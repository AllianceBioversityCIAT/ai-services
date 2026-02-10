// =========================
// Configuration & Constants
// =========================
const API_BASE_URL = 'https://oxnrkcntlheycdgcnilexrwp4i0tucqz.lambda-url.us-east-1.on.aws';
// const API_BASE_URL = 'http://localhost:8000';
const S3_BUCKET = 'ai-services-ibd';
const FOLDER_PATH = 'star/text-mining/files/test/';
const ENVIRONMENT_URL = 'https://management-allianceindicatorstest.ciat.cgiar.org/api/';
const STAR_API_URL = 'https://main-allianceindicatorstest.ciat.cgiar.org/api/results/ai/formalize/bulk';

// =========================
// State Management
// =========================
let currentResults = null;
let currentAuthToken = null;
let selectedFile = null;
let s3Objects = [];
let editedData = [];
let currentPage = 1;
let resultsPerPage = 10;
let currentFileName = null;
let recordStatuses = {}; // { recordId: { status: 'pending'|'complete'|'failed', link: '...' } }
let activeFilters = {}; // { columnKey: [selectedValues] }
let openFilterColumn = null; // Track which filter is currently open

// =========================
// Helper Functions
// =========================
async function getAuthToken() {
    try {
        // Call backend endpoint to get auth token securely
        const response = await fetch(`${API_BASE_URL}/api/auth/token`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to obtain auth token: ${response.status}`);
        }
        
        const data = await response.json();
        return data.token;
    } catch (error) {
        console.error('Error obtaining auth token:', error);
        throw new Error('Unable to authenticate. Please try again later.');
    }
}

function showLoading(message = 'Processing...') {
    const overlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    loadingText.textContent = message;
    overlay.style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = `❌ ${message}`;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 8000);
}

function hideResults() {
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('starSubmissionResults').style.display = 'none';
}

function extractInnerResults(rawResult) {
    if (rawResult && typeof rawResult === 'object' && rawResult.results) {
        return rawResult;
    }
    
    if (rawResult && rawResult.content && Array.isArray(rawResult.content)) {
        for (const item of rawResult.content) {
            if (item.text) {
                try {
                    const parsed = JSON.parse(item.text);
                    if (parsed && parsed.results) {
                        return parsed;
                    }
                } catch (e) {
                    continue;
                }
            }
        }
    }
    
    return { results: [] };
}

function extractUnmappedInstitutions(results) {
    const unmapped = [];
    const seen = new Set();
    
    results.forEach((result, idx) => {
        const recordId = `Record_${idx + 1}`;
        const title = result.title || 'Unknown Title';
        
        // Check partners
        if (result.partners && Array.isArray(result.partners)) {
            result.partners.forEach(partner => {
                const institutionId = partner.institution_id;
                const similarityScore = partner.similarity_score || 0;
                const institutionName = partner.institution_name || 'Unknown Institution';
                
                if ((institutionId === null && similarityScore === 0) || similarityScore < 70) {
                    const key = institutionName.toLowerCase().trim();
                    if (!seen.has(key)) {
                        seen.add(key);
                        unmapped.push({
                            record_id: recordId,
                            record_title: title,
                            source_field: 'partners',
                            institution_name: institutionName,
                            institution_id: institutionId,
                            similarity_score: similarityScore
                        });
                    }
                }
            });
        }
        
        // Check trainee_affiliation
        if (result.trainee_affiliation && typeof result.trainee_affiliation === 'object') {
            const aff = result.trainee_affiliation;
            const institutionId = aff.institution_id;
            const similarityScore = aff.similarity_score || 0;
            const affiliationName = aff.institution_name || 'Unknown Affiliation';
            
            if ((institutionId === null && similarityScore === 0) || similarityScore < 70) {
                const key = affiliationName.toLowerCase().trim();
                if (!seen.has(key)) {
                    seen.add(key);
                    unmapped.push({
                        record_id: recordId,
                        record_title: title,
                        source_field: 'trainee_affiliation',
                        institution_name: affiliationName,
                        institution_id: institutionId,
                        similarity_score: similarityScore
                    });
                }
            }
        }
        
        // Check trainees_description
        if (result.trainees_description && Array.isArray(result.trainees_description)) {
            result.trainees_description.forEach(trainee => {
                const institutionId = trainee.institution_id;
                const similarityScore = trainee.similarity_score || 0;
                const institutionName = trainee.institution_name || 'Unknown Institution';
                
                if ((institutionId === null && similarityScore === 0) || similarityScore < 70) {
                    const key = institutionName.toLowerCase().trim();
                    if (!seen.has(key)) {
                        seen.add(key);
                        unmapped.push({
                            record_id: recordId,
                            record_title: title,
                            source_field: 'trainees_description',
                            institution_name: institutionName,
                            institution_id: institutionId,
                            similarity_score: similarityScore
                        });
                    }
                }
            });
        }
    });
    
    return unmapped;
}

function createUnmappedReportCSV(unmapped) {
    if (unmapped.length === 0) return 'No unmapped institutions found.';
    
    const headers = ['record_id', 'record_title', 'source_field', 'institution_name', 'institution_id', 'similarity_score'];
    const rows = unmapped.map(item => 
        headers.map(key => {
            const val = item[key];
            if (val === null || val === undefined) return '';
            const str = String(val);
            // Escape quotes and wrap in quotes if contains comma or quote
            if (str.includes(',') || str.includes('"') || str.includes('\n')) {
                return '"' + str.replace(/"/g, '""') + '"';
            }
            return str;
        }).join(',')
    );
    
    return [headers.join(','), ...rows].join('\n');
}

function downloadCSV(content, filename) {
    const blob = new Blob([content], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// =========================
// DynamoDB Functions
// =========================
async function loadRecordStatusesFromDynamo(fileName) {
    try {
        const response = await fetch(`${API_BASE_URL}/dynamo/bulk-upload-records/${encodeURIComponent(fileName)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            if (response.status === 404) {
                // No existe registro previo, retornar objeto vacío
                return { complete: [], failed: [], links: {} };
            }
            throw new Error(`Failed to load record statuses: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error loading record statuses:', error);
        return { complete: [], failed: [], links: {} };
    }
}

async function saveRecordStatusToDynamo(fileName, recordId, status, link = null) {
    try {
        const payload = {
            fileName: fileName,
            recordId: String(recordId), // Ensure recordId is always a string
            status: status,
            link: link
        };
        
        const response = await fetch(`${API_BASE_URL}/dynamo/bulk-upload-records`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('DynamoDB save error:', errorText);
            throw new Error(`Failed to save record status: ${response.status} - ${errorText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error saving record status:', error);
        throw error;
    }
}

// =========================
// API Calls
// =========================
async function processDocument(mode, file = null, s3Key = null) {
    try {
        // Obtain auth token securely from backend
        if (!currentAuthToken) {
            showLoading('Authenticating...');
            currentAuthToken = await getAuthToken();
            hideLoading();
        }
    } catch (error) {
        showError(error.message);
        return;
    }
    
    const formData = new FormData();
    formData.append('bucketName', S3_BUCKET);
    formData.append('token', currentAuthToken);
    formData.append('environmentUrl', ENVIRONMENT_URL);
    
    if (mode === 'upload' && file) {
        const fullKey = FOLDER_PATH + file.name;
        formData.append('file', file);
        formData.append('key', fullKey);
        currentFileName = file.name;
    } else if (mode === 's3' && s3Key) {
        formData.append('key', s3Key);
        // Extraer nombre del archivo de la key de S3
        currentFileName = s3Key.split('/').pop();
    } else {
        showError('Invalid document source');
        return;
    }
    
    try {
        showLoading('Sending document to the service...');
        
        const startTime = Date.now();
        const response = await fetch(`${API_BASE_URL}/star/mining-bulk-upload/capdev`, {
            method: 'POST',
            body: formData
        });
        
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API error ${response.status}: ${errorText}`);
        }
        
        const result = await response.json();
        
        hideLoading();
        
        if (result.status === 'error' || result.isError === true) {
            showError(`Service returned an error: ${result.error || result.message || 'Unknown error'}`);
            return;
        }
        
        displayResults(result, elapsed);
        
    } catch (error) {
        hideLoading();
        showError(`Could not reach the API: ${error.message}`);
    }
}

function formatResultForSTAR(result) {
    const formatted = { ...result };
    
    // Remove batch_number and id (id is for internal tracking only)
    delete formatted.batch_number;
    delete formatted.id;
    
    // ========================================
    // STEP 1: Remove fields NOT used in CapDev bulk upload
    // ========================================
    const nonCapDevFields = [
        'evidence_for_stage', 'policy_type', 'stage_in_policy_process',
        'short_title', 'innovation_nature', 'innovation_type', 
        'anticipated_users', 'assess_readiness', 'innovation_actors_detailed',
        'organizations', 'organization_type', 'organization_sub_type', 
        'other_organization_type'
    ];
    nonCapDevFields.forEach(field => delete formatted[field]);
    
    // ========================================
    // STEP 2: Convert year to string (@IsString in DTO)
    // ========================================
    if (formatted.year !== undefined && formatted.year !== null) {
        formatted.year = String(formatted.year);
    }
    
    // ========================================
    // STEP 3: Convert numeric fields to numbers (@IsNumber in DTO)
    // ========================================
    const numericFields = ['total_participants', 'male_participants', 'female_participants', 'non_binary_participants'];
    numericFields.forEach(field => {
        if (formatted[field] !== undefined && formatted[field] !== null && formatted[field] !== '') {
            formatted[field] = Number(formatted[field]);
        }
    });
    
    // ========================================
    // STEP 4: Convert regions to array of numbers (@IsNumber({}, { each: true }) in DTO)
    // ========================================
    if (formatted.regions) {
        if (typeof formatted.regions === 'string') {
            try {
                formatted.regions = JSON.parse(formatted.regions);
            } catch (e) {
                formatted.regions = [];
            }
        }
        if (Array.isArray(formatted.regions)) {
            formatted.regions = formatted.regions.map(r => {
                if (typeof r === 'object' && r.id) return Number(r.id);
                return Number(r);
            }).filter(r => !isNaN(r));
        }
    }
    
    // ========================================
    // STEP 5: Process and validate trainee_affiliation (AiRawInstitution)
    // ========================================
    if (formatted.trainee_affiliation && typeof formatted.trainee_affiliation === 'object') {
        // Convert similarity_score to number (@IsNumber)
        if (formatted.trainee_affiliation.similarity_score !== undefined && formatted.trainee_affiliation.similarity_score !== null) {
            formatted.trainee_affiliation.similarity_score = Number(formatted.trainee_affiliation.similarity_score);
        }
        // Convert institution_id to string (@IsString @IsOptional)
        if (formatted.trainee_affiliation.institution_id !== undefined && formatted.trainee_affiliation.institution_id !== null) {
            formatted.trainee_affiliation.institution_id = String(formatted.trainee_affiliation.institution_id);
        }
        // Validate required field institution_name exists (@IsNotEmpty)
        if (!formatted.trainee_affiliation.institution_name || !formatted.trainee_affiliation.similarity_score) {
            delete formatted.trainee_affiliation;
        }
    }
    
    // ========================================
    // STEP 6: Process and validate training_supervisor (AiRawUser)
    // ========================================
    if (formatted.training_supervisor && typeof formatted.training_supervisor === 'object') {
        // Convert similarity_score to number (@IsNumber)
        if (formatted.training_supervisor.similarity_score !== undefined && formatted.training_supervisor.similarity_score !== null) {
            formatted.training_supervisor.similarity_score = Number(formatted.training_supervisor.similarity_score);
        }
        // Convert code to string (@IsString @IsOptional)
        if (formatted.training_supervisor.code !== undefined && formatted.training_supervisor.code !== null) {
            formatted.training_supervisor.code = String(formatted.training_supervisor.code);
        }
        // Validate required field name exists (@IsNotEmpty)
        if (!formatted.training_supervisor.name || !formatted.training_supervisor.similarity_score) {
            delete formatted.training_supervisor;
        }
    }
    
    // ========================================
    // STEP 7: Process and validate main_contact_person (AiRawUser)
    // ========================================
    if (formatted.main_contact_person && typeof formatted.main_contact_person === 'object') {
        // Convert similarity_score to number (@IsNumber)
        if (formatted.main_contact_person.similarity_score !== undefined && formatted.main_contact_person.similarity_score !== null) {
            formatted.main_contact_person.similarity_score = Number(formatted.main_contact_person.similarity_score);
        }
        // Convert code to string (@IsString @IsOptional)
        if (formatted.main_contact_person.code !== undefined && formatted.main_contact_person.code !== null) {
            formatted.main_contact_person.code = String(formatted.main_contact_person.code);
        }
        // Validate required field name exists (@IsNotEmpty)
        if (!formatted.main_contact_person.name || !formatted.main_contact_person.similarity_score) {
            delete formatted.main_contact_person;
        }
    }
    
    // ========================================
    // STEP 8: Process and validate language (AiRawLanguage)
    // ========================================
    if (formatted.language && typeof formatted.language === 'object') {
        // Ensure name and code are strings
        if (formatted.language.name) {
            formatted.language.name = String(formatted.language.name);
        }
        if (formatted.language.code) {
            formatted.language.code = String(formatted.language.code);
        }
        // Validate required fields exist (@IsNotEmpty)
        if (!formatted.language.name || !formatted.language.code) {
            delete formatted.language;
        }
    }
    
    // ========================================
    // STEP 9: Process and validate trainee_nationality (AiRawCountry)
    // ========================================
    if (formatted.trainee_nationality && typeof formatted.trainee_nationality === 'object') {
        // Ensure code is string (@IsString @IsNotEmpty)
        if (formatted.trainee_nationality.code) {
            formatted.trainee_nationality.code = String(formatted.trainee_nationality.code);
        }
        // Validate areas is array of strings (@IsOptional @IsArray @IsString({ each: true }))
        if (formatted.trainee_nationality.areas) {
            if (Array.isArray(formatted.trainee_nationality.areas)) {
                formatted.trainee_nationality.areas = formatted.trainee_nationality.areas.map(a => String(a));
                if (formatted.trainee_nationality.areas.length === 0) {
                    delete formatted.trainee_nationality.areas;
                }
            } else {
                delete formatted.trainee_nationality.areas;
            }
        }
        // Validate required field code exists
        if (!formatted.trainee_nationality.code) {
            delete formatted.trainee_nationality;
        }
    }
    
    // ========================================
    // STEP 10: Parse JSON strings for array/object fields
    // ========================================
    const jsonFields = ['keywords', 'sdg_targets', 'countries', 'evidences', 'partners', 'trainees_description'];
    jsonFields.forEach(field => {
        if (formatted[field] && typeof formatted[field] === 'string') {
            try {
                formatted[field] = JSON.parse(formatted[field]);
            } catch (e) {
                formatted[field] = [];
            }
        }
    });
    
    // ========================================
    // STEP 11: Validate and clean partners array (AiRawInstitution[])
    // ========================================
    if (formatted.partners !== undefined) {
        if (!Array.isArray(formatted.partners) || formatted.partners.length === 0) {
            delete formatted.partners;
        } else {
            formatted.partners = formatted.partners.map(p => {
                if (typeof p === 'object' && p !== null) {
                    const partner = { ...p };
                    // Convert similarity_score to number
                    if (partner.similarity_score !== undefined && partner.similarity_score !== null) {
                        partner.similarity_score = Number(partner.similarity_score);
                    }
                    // Convert institution_id to string
                    if (partner.institution_id !== undefined && partner.institution_id !== null) {
                        partner.institution_id = String(partner.institution_id);
                    }
                    return partner;
                }
                return p;
            }).filter(p => p && typeof p === 'object' && p.institution_name && p.similarity_score !== undefined);
            
            if (formatted.partners.length === 0) {
                delete formatted.partners;
            }
        }
    }
    
    // ========================================
    // STEP 11.5: Validate and clean trainees_description array (AiRawInstitution[])
    // ========================================
    if (formatted.trainees_description !== undefined) {
        if (!Array.isArray(formatted.trainees_description) || formatted.trainees_description.length === 0) {
            delete formatted.trainees_description;
        } else {
            formatted.trainees_description = formatted.trainees_description.map(t => {
                if (typeof t === 'object' && t !== null) {
                    const trainee = { ...t };
                    // Convert similarity_score to number
                    if (trainee.similarity_score !== undefined && trainee.similarity_score !== null) {
                        trainee.similarity_score = Number(trainee.similarity_score);
                    }
                    // Convert institution_id to string
                    if (trainee.institution_id !== undefined && trainee.institution_id !== null) {
                        trainee.institution_id = String(trainee.institution_id);
                    }
                    return trainee;
                }
                return t;
            }).filter(t => t && typeof t === 'object' && t.institution_name && t.similarity_score !== undefined);
            
            if (formatted.trainees_description.length === 0) {
                delete formatted.trainees_description;
            }
        }
    }
    
    // ========================================
    // STEP 12: Validate and clean countries array (AiRawCountry[])
    // ========================================
    if (formatted.countries !== undefined) {
        if (!Array.isArray(formatted.countries) || formatted.countries.length === 0) {
            delete formatted.countries;
        } else {
            formatted.countries = formatted.countries.map(c => {
                if (typeof c === 'object' && c !== null) {
                    const country = { ...c };
                    // Ensure code is string
                    if (country.code) {
                        country.code = String(country.code);
                    }
                    // Validate areas is array of strings
                    if (country.areas) {
                        if (Array.isArray(country.areas)) {
                            country.areas = country.areas.map(a => String(a));
                            if (country.areas.length === 0) {
                                delete country.areas;
                            }
                        } else {
                            delete country.areas;
                        }
                    }
                    return country;
                }
                return c;
            }).filter(c => c && typeof c === 'object' && c.code);
            
            if (formatted.countries.length === 0) {
                delete formatted.countries;
            }
        }
    }
    
    // ========================================
    // STEP 13: Validate and clean evidences array (AiRawEvidence[])
    // ========================================
    if (formatted.evidences !== undefined) {
        if (!Array.isArray(formatted.evidences) || formatted.evidences.length === 0) {
            delete formatted.evidences;
        } else {
            formatted.evidences = formatted.evidences.map(e => {
                if (typeof e === 'object' && e !== null) {
                    const evidence = { ...e };
                    // Ensure both fields are strings
                    if (evidence.evidence_link) {
                        evidence.evidence_link = String(evidence.evidence_link);
                    }
                    if (evidence.evidence_description) {
                        evidence.evidence_description = String(evidence.evidence_description);
                    }
                    return evidence;
                }
                return e;
            }).filter(e => e && typeof e === 'object' && e.evidence_link && e.evidence_description);
            
            if (formatted.evidences.length === 0) {
                delete formatted.evidences;
            }
        }
    }
    
    // ========================================
    // STEP 14: Clean optional array fields (keywords, sdg_targets)
    // ========================================
    ['keywords', 'sdg_targets'].forEach(field => {
        if (formatted[field] !== undefined) {
            if (!Array.isArray(formatted[field]) || formatted[field].length === 0) {
                delete formatted[field];
            } else {
                // Ensure all items are strings
                formatted[field] = formatted[field].map(item => String(item));
            }
        }
    });
    
    // ========================================
    // STEP 15: Clean regions array
    // ========================================
    if (formatted.regions !== undefined) {
        if (!Array.isArray(formatted.regions) || formatted.regions.length === 0) {
            delete formatted.regions;
        }
    }
    
    // ========================================
    // STEP 16: Process IP Rights fields
    // ========================================
    // Convert asset_ip_owner_id to number if it's still a string
    if (formatted.asset_ip_owner_id !== undefined && formatted.asset_ip_owner_id !== null && formatted.asset_ip_owner_id !== '') {
        if (typeof formatted.asset_ip_owner_id === 'string') {
            const nameToIdMap = {
                'International Center for Tropical Agriculture - CIAT': 1,
                'Bioversity International': 2,
                'Bioversity International and International Center for Tropical Agriculture - CIAT': 3,
                'Others': 4
            };
            formatted.asset_ip_owner_id = nameToIdMap[formatted.asset_ip_owner_id] || Number(formatted.asset_ip_owner_id);
        } else {
            formatted.asset_ip_owner_id = Number(formatted.asset_ip_owner_id);
        }
    } else {
        delete formatted.asset_ip_owner_id;
    }
    
    // Clean IP Rights description fields
    ['asset_ip_owner_description', 'publicity_restriction_description', 
     'potential_asset_description', 'requires_further_development_description'].forEach(field => {
        if (formatted[field] === null || formatted[field] === undefined || formatted[field] === '') {
            delete formatted[field];
        } else if (formatted[field] !== undefined) {
            formatted[field] = String(formatted[field]);
        }
    });
    
    // Clean IP Rights Yes/No fields
    ['publicity_restriction', 'potential_asset', 'requires_further_development'].forEach(field => {
        if (formatted[field] === null || formatted[field] === undefined || formatted[field] === '') {
            delete formatted[field];
        } else if (formatted[field] !== undefined) {
            formatted[field] = String(formatted[field]);
        }
    });
    
    // ========================================
    // STEP 17: Remove optional string fields if null/undefined/empty
    // ========================================
    const optionalStringFields = [
        'description', 'geoscope_level', 'training_category', 'training_purpose',
        'trainee_name', 'trainee_gender', 'training_type', 'delivery_modality',
        'start_date', 'end_date', 'length_of_training', 
        'alliance_main_contact_person_first_name', 'alliance_main_contact_person_last_name',
        'degree', 'trainees'
    ];
    
    optionalStringFields.forEach(field => {
        if (formatted[field] === null || formatted[field] === undefined || formatted[field] === '') {
            delete formatted[field];
        } else if (formatted[field] !== undefined) {
            // Ensure it's a string
            formatted[field] = String(formatted[field]);
        }
    });
    
    // ========================================
    // STEP 18: Remove optional numeric fields if null/undefined
    // ========================================
    numericFields.forEach(field => {
        if (formatted[field] === null || formatted[field] === undefined) {
            delete formatted[field];
        }
    });
    
    // ========================================
    // STEP 19: Remove optional nested objects if null/empty
    // ========================================
    const optionalNestedObjects = ['trainee_affiliation', 'training_supervisor', 'main_contact_person', 'language', 'trainee_nationality'];
    optionalNestedObjects.forEach(field => {
        if (formatted[field] === null || formatted[field] === undefined || 
            (typeof formatted[field] === 'object' && Object.keys(formatted[field]).length === 0)) {
            delete formatted[field];
        }
    });
    
    return formatted;
}

async function submitToSTAR(selectedResults) {
    if (!currentAuthToken) {
        showError('Authentication token not available. Please process a document first.');
        return;
    }
    
    if (!currentFileName) {
        showError('File name not available. Please process a document first.');
        return;
    }
    
    try {
        showLoading(`Submitting ${selectedResults.length} records to STAR platform...`);
        
        // Format results according to STAR DTO requirements
        const formattedResults = selectedResults.map(result => formatResultForSTAR(result));
        
        const response = await fetch(STAR_API_URL, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentAuthToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ results: formattedResults })
        });
        
        hideLoading();
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`STAR API error ${response.status}: ${errorText}`);
        }
        
        const starResponse = await response.json();
        
        // Procesar respuesta y actualizar estados
        await processSTARResponse(starResponse, selectedResults);
        
        // Recargar la tabla para mostrar los estados actualizados
        // Usar editedData para preservar las ediciones del usuario
        renderResultsTable(editedData);
        
        displaySTARResults(starResponse, selectedResults.length);
        
    } catch (error) {
        hideLoading();
        showError(`Error submitting to STAR: ${error.message}`);
    }
}

async function processSTARResponse(starResponse, submittedResults) {
    const resultsCreated = starResponse.data?.results_created || [];
    const resultsErrors = starResponse.data?.results_errors || [];
    
    // Crear un mapa de resultados enviados por título para identificarlos
    const resultsByTitle = new Map();
    submittedResults.forEach(result => {
        resultsByTitle.set(result.title, result);
    });
    
    // Procesar registros exitosos
    for (const created of resultsCreated) {
        if (created.error === false && created.title) {
            const originalResult = resultsByTitle.get(created.title);
            if (originalResult && originalResult.id) {
                const recordId = originalResult.id;
                const starLink = `https://allianceindicatorstest.ciat.cgiar.org/result/STAR-${created.result_official_code}`;
                
                // Actualizar estado local
                recordStatuses[recordId] = {
                    status: 'complete',
                    link: starLink
                };
                
                // Guardar en DynamoDB
                try {
                    await saveRecordStatusToDynamo(currentFileName, recordId, 'complete', starLink);
                } catch (error) {
                    console.error(`Failed to save status for record ${recordId}:`, error);
                }
            }
        }
    }
    
    // Procesar registros con error
    for (const errorResult of resultsErrors) {
        if (errorResult.error === true && errorResult.title) {
            const originalResult = resultsByTitle.get(errorResult.title);
            if (originalResult && originalResult.id) {
                const recordId = originalResult.id;
                
                // Actualizar estado local
                recordStatuses[recordId] = {
                    status: 'failed',
                    link: null,
                    errorMessage: errorResult.message_error
                };
                
                // Guardar en DynamoDB
                try {
                    await saveRecordStatusToDynamo(currentFileName, recordId, 'failed', null);
                } catch (error) {
                    console.error(`Failed to save status for record ${recordId}:`, error);
                }
            }
        }
    }
}

// =========================
// UI Rendering
// =========================
async function displayResults(rawResult, elapsed) {
    const payload = extractInnerResults(rawResult);
    const results = payload.results || [];
    
    currentResults = results;
    editedData = JSON.parse(JSON.stringify(results)); // Deep clone
    currentPage = 1; // Reset to first page when displaying new results
    
    // Cargar estados desde DynamoDB si existe el archivo
    if (currentFileName) {
        showLoading('Loading previous statuses...');
        const savedStatuses = await loadRecordStatusesFromDynamo(currentFileName);
        
        // Construir el objeto recordStatuses
        recordStatuses = {};
        
        // Marcar registros completados
        savedStatuses.complete?.forEach(recordId => {
            recordStatuses[String(recordId)] = {
                status: 'complete',
                link: savedStatuses.links?.[recordId] || null
            };
        });
        
        // Marcar registros fallidos
        savedStatuses.failed?.forEach(recordId => {
            recordStatuses[String(recordId)] = {
                status: 'failed',
                link: null
            };
        });
        
        // Los que no están en ninguno de los dos, están en pending
        results.forEach(result => {
            const resultId = String(result.id); // Convert to string
            if (result.id && !recordStatuses[resultId]) {
                recordStatuses[resultId] = {
                    status: 'pending',
                    link: null
                };
            }
        });
        
        hideLoading();
    }
    
    // Reset filters when new data is loaded
    activeFilters = {};
    openFilterColumn = null;
    
    // Show results section
    document.getElementById('resultsSection').style.display = 'block';
    
    // Success message
    document.getElementById('successMessage').textContent = `✅ Processed successfully! ⏱️ ${elapsed}s`;
    
    // Raw JSON
    document.getElementById('rawJson').textContent = JSON.stringify(rawResult, null, 2);
    
    // Institution mapping report
    if (results.length > 0) {
        const unmapped = extractUnmappedInstitutions(results);
        const reportDiv = document.getElementById('institutionReport');
        const reportContent = document.getElementById('institutionReportContent');
        
        if (unmapped.length > 0) {
            reportDiv.style.display = 'block';
            reportContent.innerHTML = `
                <div class="warning-message">
                    ⚠️ Found ${unmapped.length} unmapped institutions
                </div>
                <details class="collapsible">
                    <summary>🔍 View unmapped institutions</summary>
                    <div style="overflow-x: auto; padding: 1rem;">
                        <table class="results-table">
                            <thead>
                                <tr>
                                    <th>Record ID</th>
                                    <th>Record Title</th>
                                    <th>Source Field</th>
                                    <th>Institution Name</th>
                                    <th>Institution ID</th>
                                    <th>Similarity Score</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${unmapped.map(item => `
                                    <tr>
                                        <td>${item.record_id}</td>
                                        <td>${item.record_title}</td>
                                        <td>${item.source_field}</td>
                                        <td>${item.institution_name}</td>
                                        <td>${item.institution_id || 'null'}</td>
                                        <td>${item.similarity_score}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </details>
                <button class="btn btn-secondary" style="margin-top: 1rem;" onclick="downloadUnmappedReport()">
                    📥 Download Unmapped Institutions Report
                </button>
            `;
        } else {
            reportDiv.style.display = 'block';
            reportContent.innerHTML = '<div class="info-message">✅ All institutions were successfully mapped!</div>';
        }
    }
    
    // Results table
    if (results.length > 0) {
        renderResultsTable(results);
        document.getElementById('resultsTableSection').style.display = 'block';
        document.getElementById('recordsCount').textContent = `📊 Found ${results.length} records`;
    }
    
    // Scroll to results
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderResultsTable(results) {
    const table = document.getElementById('resultsTable');
    const thead = document.getElementById('tableHead');
    const tbody = document.getElementById('tableBody');
    
    // Apply filters
    const filteredResults = applyFilters(results);
    
    // Calculate pagination
    const totalPages = Math.ceil(filteredResults.length / resultsPerPage);
    const startIndex = (currentPage - 1) * resultsPerPage;
    const endIndex = Math.min(startIndex + resultsPerPage, filteredResults.length);
    const paginatedResults = filteredResults.slice(startIndex, endIndex);
    
    // Define columns
    const columns = [
        { key: 'select', label: 'Select', type: 'checkbox' },
        { key: 'id', label: 'ID', type: 'text', readonly: true },
        { key: 'status', label: 'Status', type: 'status', readonly: true },
        { key: 'star_link', label: 'STAR Link', type: 'link', readonly: true },
        { key: 'indicator', label: 'Indicator', type: 'text' },
        { key: 'title', label: 'Title', type: 'text', required: true },
        { key: 'description', label: 'Description', type: 'textarea' },
        { key: 'year', label: 'Year', type: 'text' },
        { key: 'contract_code', label: 'Contract Code', type: 'text' },
        { key: 'sdg_targets', label: 'SDG Targets', type: 'textarea' },
        { key: 'training_category', label: 'Training Category', type: 'select', options: ['Training', 'Engagement'] },
        { key: 'training_type', label: 'Training Type', type: 'select', options: ['Individual training', 'Group training'] },
        { key: 'training_purpose', label: 'Training Purpose', type: 'text' },
        { key: 'start_date', label: 'Start Date', type: 'text' },
        { key: 'end_date', label: 'End Date', type: 'text' },
        { key: 'delivery_modality', label: 'Delivery Modality', type: 'select', options: ['in-person', 'virtual', 'hybrid'] },
        { key: 'length_of_training', label: 'Length of Training', type: 'select', options: ['Short-term', 'Long-term'] },
        { key: 'total_participants', label: 'Total Participants', type: 'number' },
        { key: 'male_participants', label: 'Male Participants', type: 'number' },
        { key: 'female_participants', label: 'Female Participants', type: 'number' },
        { key: 'non_binary_participants', label: 'Non-binary Participants', type: 'number' },
        { key: 'degree', label: 'Degree', type: 'select', options: ['PhD', 'MSc', 'BSc', 'Other'] },
        { key: 'trainee_name', label: 'Trainee Name', type: 'text' },
        { key: 'trainee_gender', label: 'Trainee Gender', type: 'select', options: ['male', 'female', 'non-binary'] },
        { key: 'geoscope_level', label: 'Geoscope Level', type: 'select', options: ['Global', 'Regional', 'National', 'Sub-national', 'This is yet to be determined'] },
        { key: 'keywords', label: 'Keywords', type: 'textarea' },
        { key: 'main_contact_person.name', label: 'Main Contact Name', type: 'text' },
        { key: 'main_contact_person.code', label: 'Main Contact Code', type: 'text' },
        { key: 'main_contact_person.similarity_score', label: 'Main Contact Similarity', type: 'number' },
        { key: 'training_supervisor.name', label: 'Training Supervisor', type: 'text' },
        { key: 'training_supervisor.code', label: 'Training Supervisor Code', type: 'text' },
        { key: 'training_supervisor.similarity_score', label: 'Supervisor Similarity', type: 'number' },
        { key: 'trainee_affiliation.institution_name', label: 'Trainee Affiliation', type: 'text' },
        { key: 'trainee_affiliation.institution_id', label: 'Trainee Affiliation ID', type: 'text' },
        { key: 'trainee_affiliation.similarity_score', label: 'Affiliation Similarity', type: 'number' },
        { key: 'language.name', label: 'Language', type: 'text' },
        { key: 'language.code', label: 'Language Code', type: 'text' },
        { key: 'partners', label: 'Partners', type: 'textarea' },
        { key: 'trainees', label: 'Trainees', type: 'select', options: ['Yes', 'No'] },
        { key: 'trainees_description', label: 'Trainees Organizations', type: 'textarea' },
        { key: 'countries', label: 'Countries', type: 'textarea' },
        { key: 'regions', label: 'Regions', type: 'textarea' },
        { key: 'evidences', label: 'Evidences', type: 'textarea' },
        { key: 'trainee_nationality.code', label: 'Trainee Nationality Code', type: 'text' },
        { key: 'asset_ip_owner_id', label: 'Asset IP Owner', type: 'select', options: [
            'International Center for Tropical Agriculture - CIAT',
            'Bioversity International',
            'Bioversity International and International Center for Tropical Agriculture - CIAT',
            'Others'
        ]},
        { key: 'asset_ip_owner_description', label: 'Asset IP Owner Description', type: 'text' },
        { key: 'publicity_restriction', label: 'Publicity Restriction', type: 'select', options: ['Yes', 'No'] },
        { key: 'publicity_restriction_description', label: 'Publicity Restriction Description', type: 'textarea' },
        { key: 'potential_asset', label: 'Potential Asset', type: 'select', options: ['Yes', 'No'] },
        { key: 'potential_asset_description', label: 'Potential Asset Description', type: 'textarea' },
        { key: 'requires_further_development', label: 'Requires Further Development', type: 'select', options: ['Yes', 'No'] },
        { key: 'requires_further_development_description', label: 'Further Development Description', type: 'textarea' },
    ];
    
    // Build header
    thead.innerHTML = `
        <tr>
            ${columns.map(col => {
                if (col.type === 'checkbox') {
                    return `<th><input type="checkbox" id="selectAllCheckbox" title="Select/Deselect All"></th>`;
                }
                // Add filter icon for filterable columns
                if (col.readonly || col.type === 'status' || col.type === 'link') {
                    return `<th>${col.label}</th>`;
                }
                const hasActiveFilter = activeFilters[col.key] && activeFilters[col.key].length > 0;
                const filterClass = hasActiveFilter ? 'filter-active' : '';
                return `<th>
                    <div class="th-content">
                        <span>${col.label}</span>
                        <span class="filter-icon ${filterClass}" data-column="${col.key}" title="Filter">▼</span>
                    </div>
                </th>`;
            }).join('')}
        </tr>
    `;
    
    // Build rows with paginated results
    tbody.innerHTML = paginatedResults.map((result, localIdx) => {
        const globalIdx = startIndex + localIdx; // Global index in the full results array
        return `
            <tr>
                ${columns.map(col => {
                    if (col.type === 'checkbox') {
                        return `<td><input type="checkbox" class="row-select" data-index="${globalIdx}"></td>`;
                    } else if (col.type === 'status') {
                        const recordId = String(result.id); // Convert to string
                        const statusInfo = recordStatuses[recordId] || { status: 'pending' };
                        const statusClass = statusInfo.status === 'complete' ? 'status-complete' : 
                                          statusInfo.status === 'failed' ? 'status-failed' : 'status-pending';
                        const statusText = statusInfo.status === 'complete' ? '✓ Complete' : 
                                         statusInfo.status === 'failed' ? '✗ Failed' : '⏳ Pending';
                        return `<td><span class="${statusClass}">${statusText}</span></td>`;
                    } else if (col.type === 'link') {
                        const recordId = String(result.id); // Convert to string
                        const statusInfo = recordStatuses[recordId] || { status: 'pending', link: null };
                        if (statusInfo.status === 'complete' && statusInfo.link) {
                            return `<td><a href="${statusInfo.link}" target="_blank" class="star-link">🔗 View in STAR</a></td>`;
                        }
                        return `<td>-</td>`;
                    } else if (col.type === 'select') {
                        let value = getNestedValue(result, col.key);
                        // Special handling for asset_ip_owner_id: convert number to name for display
                        if (col.key === 'asset_ip_owner_id' && typeof value === 'number') {
                            const idToNameMap = {
                                1: 'International Center for Tropical Agriculture - CIAT',
                                2: 'Bioversity International',
                                3: 'Bioversity International and International Center for Tropical Agriculture - CIAT',
                                4: 'Others'
                            };
                            value = idToNameMap[value] || '';
                        }
                        if (!value) {
                            value = '';
                        }
                        const options = col.options || [];
                        return `
                            <td>
                                <select data-index="${globalIdx}" data-field="${col.key}">
                                    <option value="">Select...</option>
                                    ${options.map(opt => `<option value="${opt}" ${value === opt ? 'selected' : ''}>${opt}</option>`).join('')}
                                </select>
                            </td>
                        `;
                    } else if (col.type === 'number') {
                        const value = getNestedValue(result, col.key) || 0;
                        return `<td><input type="number" value="${value}" data-index="${globalIdx}" data-field="${col.key}" min="0"></td>`;
                    } else if (col.type === 'textarea') {
                        let value = getNestedValue(result, col.key);
                        if (typeof value === 'object') {
                            value = JSON.stringify(value);
                        }
                        return `<td><textarea data-index="${globalIdx}" data-field="${col.key}" rows="3">${value || ''}</textarea></td>`;
                    } else {
                        const value = getNestedValue(result, col.key) || '';
                        if (col.readonly) {
                            return `<td><input type="text" value="${value}" readonly style="background-color: #f5f5f5; cursor: not-allowed;"></td>`;
                        }
                        return `<td><input type="text" value="${value}" data-index="${globalIdx}" data-field="${col.key}"></td>`;
                    }
                }).join('')}
            </tr>
        `;
    }).join('');
    
    // Render pagination controls with filtered count
    renderPaginationControls(filteredResults.length, totalPages);
    
    // Add event listeners for filter icons
    thead.querySelectorAll('.filter-icon').forEach(icon => {
        icon.addEventListener('click', (e) => {
            e.stopPropagation();
            const columnKey = icon.dataset.column;
            toggleFilterPanel(columnKey, icon, results);
        });
    });
    
    // Add event listeners for edits
    tbody.querySelectorAll('input, select, textarea').forEach(input => {
        if (!input.classList.contains('row-select')) {
            input.addEventListener('change', handleCellEdit);
        }
    });
    
    // Add event listeners for checkboxes
    tbody.querySelectorAll('.row-select').forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectionInfo);
    });
    
    // Add event listener for select all checkbox
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const isChecked = this.checked;
            tbody.querySelectorAll('.row-select').forEach(checkbox => {
                checkbox.checked = isChecked;
            });
            updateSelectionInfo();
        });
    }
}

function renderPaginationControls(totalResults, totalPages) {
    const paginationDiv = document.getElementById('paginationControls');
    if (!paginationDiv) return;
    
    const startIndex = (currentPage - 1) * resultsPerPage + 1;
    const endIndex = Math.min(currentPage * resultsPerPage, totalResults);
    
    let paginationHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 1.5rem; flex-wrap: wrap; gap: 1rem;">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <span style="color: var(--gray-600); font-size: 0.9rem;">
                    Showing ${startIndex}-${endIndex} of ${totalResults} records
                </span>
                <select id="resultsPerPageSelect" style="padding: 0.5rem; border: 1px solid var(--gray-300); border-radius: 6px; background: var(--white);">
                    <option value="10" ${resultsPerPage === 10 ? 'selected' : ''}>10 per page</option>
                    <option value="25" ${resultsPerPage === 25 ? 'selected' : ''}>25 per page</option>
                    <option value="50" ${resultsPerPage === 50 ? 'selected' : ''}>50 per page</option>
                    <option value="100" ${resultsPerPage === 100 ? 'selected' : ''}>100 per page</option>
                    <option value="200" ${resultsPerPage === 200 ? 'selected' : ''}>200 per page</option>
                </select>
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <button id="firstPageBtn" class="btn btn-secondary" style="padding: 0.5rem 0.75rem;" ${currentPage === 1 ? 'disabled' : ''}>
                    ⟪ First
                </button>
                <button id="prevPageBtn" class="btn btn-secondary" style="padding: 0.5rem 0.75rem;" ${currentPage === 1 ? 'disabled' : ''}>
                    ← Previous
                </button>
                <span style="color: var(--gray-700); font-weight: 500; padding: 0 1rem;">
                    Page ${currentPage} of ${totalPages}
                </span>
                <button id="nextPageBtn" class="btn btn-secondary" style="padding: 0.5rem 0.75rem;" ${currentPage === totalPages ? 'disabled' : ''}>
                    Next →
                </button>
                <button id="lastPageBtn" class="btn btn-secondary" style="padding: 0.5rem 0.75rem;" ${currentPage === totalPages ? 'disabled' : ''}>
                    Last ⟫
                </button>
            </div>
        </div>
    `;
    
    paginationDiv.innerHTML = paginationHTML;
    
    // Add event listeners for pagination buttons
    document.getElementById('firstPageBtn')?.addEventListener('click', () => {
        currentPage = 1;
        renderResultsTable(currentResults);
    });
    
    document.getElementById('prevPageBtn')?.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderResultsTable(currentResults);
        }
    });
    
    document.getElementById('nextPageBtn')?.addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            renderResultsTable(currentResults);
        }
    });
    
    document.getElementById('lastPageBtn')?.addEventListener('click', () => {
        currentPage = totalPages;
        renderResultsTable(currentResults);
    });
    
    document.getElementById('resultsPerPageSelect')?.addEventListener('change', (e) => {
        resultsPerPage = parseInt(e.target.value);
        currentPage = 1; // Reset to first page when changing page size
        renderResultsTable(currentResults);
    });
}

function getNestedValue(obj, path) {
    if (!path.includes('.')) {
        return obj[path];
    }
    const parts = path.split('.');
    let current = obj;
    for (const part of parts) {
        if (current && typeof current === 'object' && part in current) {
            current = current[part];
        } else {
            return undefined;
        }
    }
    return current;
}

function setNestedValue(obj, path, value) {
    if (!path.includes('.')) {
        obj[path] = value;
        return;
    }
    const parts = path.split('.');
    let current = obj;
    for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        if (!current[part] || typeof current[part] !== 'object') {
            current[part] = {};
        }
        current = current[part];
    }
    current[parts[parts.length - 1]] = value;
}

function applyFilters(results) {
    if (Object.keys(activeFilters).length === 0) {
        return results;
    }
    
    return results.filter(result => {
        // Check all active filters
        for (const [columnKey, selectedValues] of Object.entries(activeFilters)) {
            if (selectedValues.length === 0) continue;
            
            const cellValue = getNestedValue(result, columnKey);
            const cellValueStr = formatCellValueForFilter(cellValue);
            
            // If value is not in selected values, filter out this row
            if (!selectedValues.includes(cellValueStr)) {
                return false;
            }
        }
        return true;
    });
}

function formatCellValueForFilter(value) {
    if (value === null || value === undefined) return '(Empty)';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
}

function getUniqueValues(results, columnKey) {
    const values = new Set();
    results.forEach(result => {
        const value = getNestedValue(result, columnKey);
        values.add(formatCellValueForFilter(value));
    });
    return Array.from(values).sort();
}

function toggleFilterPanel(columnKey, iconElement, results) {
    // Close any open filter panel
    const existingPanel = document.querySelector('.filter-panel');
    if (existingPanel) {
        if (openFilterColumn === columnKey) {
            existingPanel.remove();
            openFilterColumn = null;
            return;
        }
        existingPanel.remove();
    }
    
    openFilterColumn = columnKey;
    
    // Get unique values for this column
    const uniqueValues = getUniqueValues(results, columnKey);
    const currentFilters = activeFilters[columnKey] || [];
    
    // Create filter panel
    const panel = document.createElement('div');
    panel.className = 'filter-panel';
    panel.innerHTML = `
        <div class="filter-panel-header">
            <input type="text" class="filter-search" placeholder="Search...">
        </div>
        <div class="filter-options">
            <label class="filter-option">
                <input type="checkbox" value="__select_all__" ${currentFilters.length === 0 ? 'checked' : ''}>
                <span>(Select All)</span>
            </label>
            ${uniqueValues.map(value => `
                <label class="filter-option">
                    <input type="checkbox" value="${value.replace(/"/g, '&quot;')}" 
                        ${currentFilters.length === 0 || currentFilters.includes(value) ? 'checked' : ''}>
                    <span>${value}</span>
                </label>
            `).join('')}
        </div>
        <div class="filter-panel-footer">
            <button class="filter-btn filter-btn-clear">Clear</button>
            <button class="filter-btn filter-btn-apply">Apply</button>
        </div>
    `;
    
    // Position panel below icon
    const iconRect = iconElement.getBoundingClientRect();
    panel.style.position = 'absolute';
    panel.style.top = `${iconRect.bottom + window.scrollY + 5}px`;
    panel.style.left = `${iconRect.left + window.scrollX}px`;
    
    document.body.appendChild(panel);
    
    // Handle search
    const searchInput = panel.querySelector('.filter-search');
    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        panel.querySelectorAll('.filter-option').forEach((option, index) => {
            if (index === 0) return; // Skip "Select All"
            const text = option.textContent.toLowerCase();
            option.style.display = text.includes(searchTerm) ? 'flex' : 'none';
        });
    });
    
    // Handle select all
    const selectAllCheckbox = panel.querySelector('input[value="__select_all__"]');
    const valueCheckboxes = Array.from(panel.querySelectorAll('.filter-option input')).slice(1);
    
    selectAllCheckbox.addEventListener('change', (e) => {
        valueCheckboxes.forEach(cb => {
            if (cb.closest('.filter-option').style.display !== 'none') {
                cb.checked = e.target.checked;
            }
        });
    });
    
    valueCheckboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            const allChecked = valueCheckboxes.filter(c => 
                c.closest('.filter-option').style.display !== 'none'
            ).every(c => c.checked);
            selectAllCheckbox.checked = allChecked;
        });
    });
    
    // Handle clear button
    panel.querySelector('.filter-btn-clear').addEventListener('click', () => {
        delete activeFilters[columnKey];
        panel.remove();
        openFilterColumn = null;
        currentPage = 1;
        renderResultsTable(editedData);
    });
    
    // Handle apply button
    panel.querySelector('.filter-btn-apply').addEventListener('click', () => {
        const selectedValues = valueCheckboxes
            .filter(cb => cb.checked)
            .map(cb => cb.value);
        
        if (selectedValues.length === uniqueValues.length) {
            // All selected = no filter
            delete activeFilters[columnKey];
        } else if (selectedValues.length > 0) {
            activeFilters[columnKey] = selectedValues;
        } else {
            // None selected = show nothing
            activeFilters[columnKey] = [];
        }
        
        panel.remove();
        openFilterColumn = null;
        currentPage = 1;
        renderResultsTable(editedData);
    });
    
    // Close panel when clicking outside
    setTimeout(() => {
        document.addEventListener('click', function closePanel(e) {
            if (!panel.contains(e.target) && e.target !== iconElement) {
                panel.remove();
                openFilterColumn = null;
                document.removeEventListener('click', closePanel);
            }
        });
    }, 0);
}

function handleCellEdit(event) {
    const input = event.target;
    const index = parseInt(input.dataset.index);
    const field = input.dataset.field;
    let value = input.value;
    
    // Special handling for asset_ip_owner_id: convert name to number
    if (field === 'asset_ip_owner_id' && value) {
        const nameToIdMap = {
            'International Center for Tropical Agriculture - CIAT': 1,
            'Bioversity International': 2,
            'Bioversity International and International Center for Tropical Agriculture - CIAT': 3,
            'Others': 4
        };
        value = nameToIdMap[value] || value;
    }
    
    // Parse JSON for array/object fields
    if (input.tagName === 'TEXTAREA' && ['keywords', 'partners', 'countries', 'regions', 'evidences', 'sdg_targets', 'trainees_description'].includes(field)) {
        try {
            value = JSON.parse(value);
        } catch (e) {
            // Keep as string if not valid JSON
        }
    }
    
    // Parse numbers
    if (input.type === 'number') {
        value = parseInt(value) || 0;
    }
    
    setNestedValue(editedData[index], field, value);
}

function updateSelectionInfo() {
    const checkboxes = document.querySelectorAll('.row-select');
    const selected = Array.from(checkboxes).filter(cb => cb.checked).length;
    const total = checkboxes.length;
    
    const selectionInfo = document.getElementById('selectionInfo');
    const submitBtn = document.getElementById('submitToStar');
    
    if (selected > 0) {
        selectionInfo.textContent = `📋 Selected: ${selected} of ${total} records`;
        selectionInfo.style.display = 'block';
        submitBtn.disabled = false;
    } else {
        selectionInfo.style.display = 'none';
        submitBtn.disabled = true;
    }
}

function displaySTARResults(response, count) {
    const section = document.getElementById('starSubmissionResults');
    section.style.display = 'block';
    
    document.getElementById('starResponseJson').textContent = JSON.stringify(response, null, 2);
    
    // Show success message at top
    const successMsg = document.createElement('div');
    successMsg.className = 'success-message';
    successMsg.textContent = `✅ Successfully submitted ${count} records to STAR!`;
    successMsg.style.marginBottom = '1rem';
    
    section.insertBefore(successMsg, section.firstChild);
    
    // Scroll to results
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function downloadUnmappedReport() {
    if (!currentResults) return;
    
    const unmapped = extractUnmappedInstitutions(currentResults);
    const csv = createUnmappedReportCSV(unmapped);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    downloadCSV(csv, `unmapped_institutions_${timestamp}.csv`);
}

// =========================
// Event Listeners
// =========================
document.addEventListener('DOMContentLoaded', function() {
    // Download template button
    const downloadTemplateBtn = document.getElementById('downloadTemplateBtn');
    if (downloadTemplateBtn) {
        downloadTemplateBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            try {
                showLoading('Downloading template...');
                const response = await fetch(`${API_BASE_URL}/s3/download-template`);
                
                if (!response.ok) {
                    throw new Error(`Failed to download template: ${response.status}`);
                }
                
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'capdev_template.xlsx';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                hideLoading();
            } catch (error) {
                hideLoading();
                showError(`Error downloading template: ${error.message}`);
            }
        });
    }
    
    // Document source radio buttons
    const radioButtons = document.querySelectorAll('input[name="docSource"]');
    radioButtons.forEach(radio => {
        radio.addEventListener('change', function() {
            const uploadMode = document.getElementById('uploadMode');
            const s3Mode = document.getElementById('s3Mode');
            
            if (this.value === 'upload') {
                uploadMode.style.display = 'block';
                s3Mode.style.display = 'none';
            } else {
                uploadMode.style.display = 'none';
                s3Mode.style.display = 'block';
                // Load S3 objects if not already loaded
                if (s3Objects.length === 0) {
                    loadS3Objects();
                }
            }
        });
    });
    
    // File input
    const fileInput = document.getElementById('fileInput');
    const fileName = document.getElementById('fileName');
    const uploadInfo = document.getElementById('uploadInfo');
    
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            selectedFile = e.target.files[0];
            fileName.textContent = `📄 ${selectedFile.name}`;
            fileName.classList.add('active');
            uploadInfo.style.display = 'block';
            uploadInfo.textContent = `📁 File will be uploaded to: ${S3_BUCKET}/${FOLDER_PATH}${selectedFile.name}`;
        }
    });
    
    // Drag and drop
    const uploadArea = document.querySelector('.file-upload-area');
    
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.style.borderColor = 'var(--primary-light)';
        this.style.background = 'var(--white)';
    });
    
    uploadArea.addEventListener('dragleave', function() {
        this.style.borderColor = 'var(--gray-300)';
        this.style.background = 'var(--gray-50)';
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.style.borderColor = 'var(--gray-300)';
        this.style.background = 'var(--gray-50)';
        
        if (e.dataTransfer.files.length > 0) {
            selectedFile = e.dataTransfer.files[0];
            fileName.textContent = `📄 ${selectedFile.name}`;
            fileName.classList.add('active');
            uploadInfo.style.display = 'block';
            uploadInfo.textContent = `📁 File will be uploaded to: ${S3_BUCKET}/${FOLDER_PATH}${selectedFile.name}`;
        }
    });
    
    // Refresh S3 button
    document.getElementById('refreshS3').addEventListener('click', loadS3Objects);
    
    // Process button
    document.getElementById('processBtn').addEventListener('click', function() {
        const mode = document.querySelector('input[name="docSource"]:checked').value;
        
        hideResults();
        
        if (mode === 'upload') {
            if (!selectedFile) {
                showError('You need to select a file to upload.');
                return;
            }
            processDocument('upload', selectedFile);
        } else {
            const s3Key = document.getElementById('s3Select').value;
            if (!s3Key) {
                showError('You need to select an S3 object.');
                return;
            }
            processDocument('s3', null, s3Key);
        }
    });
    
    // Submit to STAR button
    document.getElementById('submitToStar').addEventListener('click', function() {
        const checkboxes = document.querySelectorAll('.row-select');
        const selectedIndices = [];
        
        checkboxes.forEach((cb, idx) => {
            if (cb.checked) {
                selectedIndices.push(idx);
            }
        });
        
        if (selectedIndices.length === 0) {
            showError('Please select at least one record to submit to STAR.');
            return;
        }
        
        const selectedResults = selectedIndices.map(idx => editedData[idx]);
        submitToSTAR(selectedResults);
    });
    
    // Clear selections button
    document.getElementById('clearSelections').addEventListener('click', function() {
        document.querySelectorAll('.row-select').forEach(cb => cb.checked = false);
        updateSelectionInfo();
        document.getElementById('starSubmissionResults').style.display = 'none';
    });
});

async function loadS3Objects() {
    const prefix = document.getElementById('s3Prefix').value;
    const fullPrefix = FOLDER_PATH + prefix;
    const select = document.getElementById('s3Select');
    const caption = document.getElementById('s3Caption');
    
    select.innerHTML = '<option value="">Loading...</option>';
    caption.textContent = `Searching in: ${S3_BUCKET}/${fullPrefix}`;
    
    try {
        const response = await fetch(`${API_BASE_URL}/s3/list?bucket=${S3_BUCKET}&prefix=${encodeURIComponent(fullPrefix)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        s3Objects = data.objects || [];
        
        if (s3Objects.length > 0) {
            select.innerHTML = s3Objects.map(key => 
                `<option value="${key}">${key}</option>`
            ).join('');
            caption.textContent = `Found ${s3Objects.length} objects. Selected: ${s3Objects[0]}`;
        } else {
            select.innerHTML = '<option value="">No objects found</option>';
            caption.textContent = 'No objects found for this bucket/prefix.';
        }
    } catch (error) {
        showError(`S3 listing error: ${error.message}`);
        select.innerHTML = '<option value="">Error loading</option>';
        caption.textContent = 'Error loading objects from S3.';
    }
}
