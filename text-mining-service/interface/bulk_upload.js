// =========================
// Configuration & Constants
// =========================
const API_BASE_URL = 'https://oxnrkcntlheycdgcnilexrwp4i0tucqz.lambda-url.us-east-1.on.aws';
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
    } else if (mode === 's3' && s3Key) {
        formData.append('key', s3Key);
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
    
    // Remove batch_number
    delete formatted.batch_number;
    
    // Ensure year is a string (@IsString in DTO)
    if (formatted.year !== undefined && formatted.year !== null) {
        formatted.year = String(formatted.year);
    }
    
    // Convert numeric fields to numbers (@IsNumber in DTO)
    const numericFields = ['total_participants', 'male_participants', 'female_participants', 'non_binary_participants', 'assess_readiness'];
    numericFields.forEach(field => {
        if (formatted[field] !== undefined && formatted[field] !== null && formatted[field] !== '') {
            formatted[field] = Number(formatted[field]);
        }
    });
    
    // Convert regions to array of numbers (@IsNumber({}, { each: true }) in DTO)
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
    
    // Convert similarity_score to number in nested objects (@IsNumber in DTO)
    // AiRawInstitution: trainee_affiliation
    if (formatted.trainee_affiliation) {
        if (formatted.trainee_affiliation.similarity_score !== undefined) {
            formatted.trainee_affiliation.similarity_score = Number(formatted.trainee_affiliation.similarity_score);
        }
        // institution_id should be string (@IsString in DTO)
        if (formatted.trainee_affiliation.institution_id !== undefined && formatted.trainee_affiliation.institution_id !== null) {
            formatted.trainee_affiliation.institution_id = String(formatted.trainee_affiliation.institution_id);
        }
    }
    
    // AiRawUser: training_supervisor and main_contact_person
    if (formatted.training_supervisor && formatted.training_supervisor.similarity_score !== undefined) {
        formatted.training_supervisor.similarity_score = Number(formatted.training_supervisor.similarity_score);
    }
    
    if (formatted.main_contact_person && formatted.main_contact_person.similarity_score !== undefined) {
        formatted.main_contact_person.similarity_score = Number(formatted.main_contact_person.similarity_score);
    }
    
    // Convert partners: institution_id to string, similarity_score to number
    if (formatted.partners && Array.isArray(formatted.partners)) {
        formatted.partners = formatted.partners.map(p => {
            if (typeof p === 'object') {
                const partner = { ...p };
                if (partner.similarity_score !== undefined) {
                    partner.similarity_score = Number(partner.similarity_score);
                }
                if (partner.institution_id !== undefined && partner.institution_id !== null) {
                    partner.institution_id = String(partner.institution_id);
                }
                return partner;
            }
            return p;
        });
    }
    
    // Parse JSON strings for array/object fields
    const jsonFields = ['keywords', 'sdg_targets', 'countries', 'evidences'];
    jsonFields.forEach(field => {
        if (formatted[field] && typeof formatted[field] === 'string') {
            try {
                formatted[field] = JSON.parse(formatted[field]);
            } catch (e) {
                formatted[field] = [];
            }
        }
    });
    
    // Parse partners if it's a string
    if (formatted.partners && typeof formatted.partners === 'string') {
        try {
            formatted.partners = JSON.parse(formatted.partners);
        } catch (e) {
            formatted.partners = [];
        }
    }
    
    return formatted;
}

async function submitToSTAR(selectedResults) {
    if (!currentAuthToken) {
        showError('Authentication token not available. Please process a document first.');
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
        displaySTARResults(starResponse, selectedResults.length);
        
    } catch (error) {
        hideLoading();
        showError(`Error submitting to STAR: ${error.message}`);
    }
}

// =========================
// UI Rendering
// =========================
function displayResults(rawResult, elapsed) {
    const payload = extractInnerResults(rawResult);
    const results = payload.results || [];
    
    currentResults = results;
    editedData = JSON.parse(JSON.stringify(results)); // Deep clone
    currentPage = 1; // Reset to first page when displaying new results
    
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
    
    // Calculate pagination
    const totalPages = Math.ceil(results.length / resultsPerPage);
    const startIndex = (currentPage - 1) * resultsPerPage;
    const endIndex = Math.min(startIndex + resultsPerPage, results.length);
    const paginatedResults = results.slice(startIndex, endIndex);
    
    // Define columns
    const columns = [
        { key: 'select', label: 'Select', type: 'checkbox' },
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
        { key: 'countries', label: 'Countries', type: 'textarea' },
        { key: 'regions', label: 'Regions', type: 'textarea' },
        { key: 'evidences', label: 'Evidences', type: 'textarea' },
        { key: 'trainee_nationality.code', label: 'Trainee Nationality Code', type: 'text' },
    ];
    
    // Build header
    thead.innerHTML = `
        <tr>
            ${columns.map(col => {
                if (col.type === 'checkbox') {
                    return `<th><input type="checkbox" id="selectAllCheckbox" title="Select/Deselect All"></th>`;
                }
                return `<th>${col.label}</th>`;
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
                    } else if (col.type === 'select') {
                        const value = getNestedValue(result, col.key) || '';
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
                        return `<td><input type="text" value="${value}" data-index="${globalIdx}" data-field="${col.key}"></td>`;
                    }
                }).join('')}
            </tr>
        `;
    }).join('');
    
    // Render pagination controls
    renderPaginationControls(results.length, totalPages);
    
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

function handleCellEdit(event) {
    const input = event.target;
    const index = parseInt(input.dataset.index);
    const field = input.dataset.field;
    let value = input.value;
    
    // Parse JSON for array/object fields
    if (input.tagName === 'TEXTAREA' && ['keywords', 'partners', 'countries', 'regions', 'evidences', 'sdg_targets'].includes(field)) {
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
