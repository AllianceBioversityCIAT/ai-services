// AICCRA Report Generator Web App
const API_BASE_URL = 'https://ia.prms.cgiar.org';

// Tracking configuration
const AI_FEEDBACK_URL = 'https://clv3b6bv9d.execute-api.us-east-1.amazonaws.com';

// URL Parameters utility
function getUrlParameter(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

function extractUserInfoFromUrl() {
    const email = getUrlParameter('user_email');
    const user = getUrlParameter('user');
    
    return {
        email: email,
        user: user
    };
}

// Initialize user info from URL
let userInfo = extractUserInfoFromUrl();

// Tab functionality
function openTab(evt, tabName) {
    const tabContents = document.getElementsByClassName('tab-content');
    const tabs = document.getElementsByClassName('tab');
    
    // Hide all tab contents
    Array.from(tabContents).forEach(content => content.classList.remove('active'));
    
    // Remove active class from all tabs
    Array.from(tabs).forEach(tab => tab.classList.remove('active'));
    
    // Show selected tab content and mark tab as active
    document.getElementById(tabName).classList.add('active');
    evt.currentTarget.classList.add('active');
}

// Utility functions
function showLoading(loadingId) {
    document.getElementById(loadingId).classList.add('show');
}

function hideLoading(loadingId) {
    document.getElementById(loadingId).classList.remove('show');
}

function showResult(resultId) {
    document.getElementById(resultId).classList.add('show');
}

function hideResult(resultId) {
    document.getElementById(resultId).classList.remove('show');
}

function showError(message, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = `
        <div class="alert alert-error">
            <i class="fas fa-exclamation-circle"></i>
            <strong>Error:</strong> ${message}
        </div>
    `;
    showResult(containerId);
}

function formatMarkdown(text) {
    if (!text) return '';
    
    // Simple markdown formatting
    return text
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/^\- (.*$)/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
        .replace(/\n/g, '<br>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
}

function downloadAsDocx(content, filename) {
    // Simple DOCX download using blob
    // Note: This is a simplified version. For full DOCX support, you'd need a library like docx.js
    const blob = new Blob([content], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

function downloadAsExcel(data, filename) {
    // Convert table data to CSV for Excel compatibility
    let csv = '';
    if (data && data.length > 0) {
        // Headers
        const headers = Object.keys(data[0]);
        csv += headers.join(',') + '\n';
        
        // Rows
        data.forEach(row => {
            const values = headers.map(header => {
                const value = row[header] || '';
                // Escape commas and quotes for CSV
                return `"${value.toString().replace(/"/g, '""')}"`;
            });
            csv += values.join(',') + '\n';
        });
    }
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// API call functions
async function makeApiCall(endpoint, data) {
    const startTime = Date.now();
    
    try {
        // Add user info to the request if available
        const requestData = {
            ...data,
            ...(userInfo.email && { user_email: userInfo.email }),
            ...(userInfo.user && { user_name: userInfo.user })
        };

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        
        // Calculate response time
        const responseTime = (Date.now() - startTime) / 1000;
        
        // Track interaction
        await trackInteraction(endpoint, data, result, responseTime, true);
        
        return result;
    } catch (error) {
        // Calculate response time even for errors
        const responseTime = (Date.now() - startTime) / 1000;
        
        // Track failed interaction
        await trackInteraction(endpoint, data, null, responseTime, false, error.message);
        
        console.error('API call failed:', error);
        throw error;
    }
}

// Track interaction function
async function trackInteraction(endpoint, requestData, responseData, responseTime, success, errorMessage = null) {
    try {
        // Determine service type based on endpoint
        let displayName = '';
        let serviceDescription = '';
        let userAction = '';
        let aiOutput = '';

        console.log('Processing endpoint:', endpoint);
        
        switch(endpoint) {
            case '/api/generate':
                displayName = `AR Generator Service - Mid-Year Report`;
                serviceDescription = `Generate mid-year progress reports for AICCRA indicators`;
                userAction = `Generate mid-year report for ${requestData.indicator} (${requestData.year})`;
                aiOutput = success && responseData?.content ? responseData.content.substring(0, 200) + '...' : (errorMessage || 'Error generating report');
                break;
            case '/api/generate-annual':
                displayName = `AR Generator Service - Annual Report`;
                serviceDescription = `Generate comprehensive annual reports for AICCRA indicators`;
                userAction = `Generate annual report for ${requestData.indicator} (${requestData.year})`;
                aiOutput = success && responseData?.content ? responseData.content.substring(0, 200) + '...' : (errorMessage || 'Error generating report');
                break;
            case '/api/generate-annual-tables':
                displayName = `AR Generator Service - Summary Tables`;
                serviceDescription = `Generate indicator summary tables for all PDO and IPI indicators`;
                userAction = `Generate summary tables for year ${requestData.year}`;
                aiOutput = success && responseData?.tables ? 'Summary tables generated successfully' : (errorMessage || 'Error generating tables');
                break;
            case '/api/generate-challenges':
                displayName = `AR Generator Service - Challenges Report`;
                serviceDescription = `Generate challenges and lessons learned reports`;
                userAction = `Generate challenges report for year ${requestData.year}`;
                aiOutput = success && responseData?.content ? responseData.content.substring(0, 200) + '...' : (errorMessage || 'Error generating challenges report');
                break;
            default:
                displayName = `AR Generator Service`;
                serviceDescription = `AICCRA Report Generator Service`;
                userAction = `API call to ${endpoint}`;
                aiOutput = success ? 'Report generated successfully' : (errorMessage || 'Error generating report');
        }

        console.log('Endpoint:', endpoint);
        console.log('Display Name assigned:', displayName);
        console.log('Service Description assigned:', serviceDescription);
        
        const interactionData = {
            user_id: userInfo.email || 'Unknown',
            user_input: userAction,
            ai_output: aiOutput,
            service_name: 'report-generator',
            display_name: displayName,
            service_description: serviceDescription,
            platform: "AICCRA",
            context: {
                request_params: {
                    indicator: requestData.indicator,
                    year: requestData.year,
                    insert_data: requestData.insert_data
                },
                user_info: {
                    user_name: userInfo.user || null
                },
                success: success,
                error_message: errorMessage
            },
            response_time_seconds: responseTime
        };
        
        console.log('Tracking interaction:', interactionData);
        
        const response = await fetch(`${AI_FEEDBACK_URL}/api/interactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(interactionData)
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('Interaction tracked successfully:', result);
        } else {
            console.warn('Failed to track interaction:', response.status, response.statusText);
        }
        
    } catch (error) {
        console.error('Error tracking interaction:', error);
        // Don't throw here to avoid affecting the main functionality
    }
}

// Tab 1: Reports (Annual and Mid-Year)
async function generateReport() {
    const button = document.getElementById('generate-report');
    const indicator = document.getElementById('indicator-select').value;
    const year = parseInt(document.getElementById('year-select').value);
    const reportType = document.getElementById('report-type-select').value;
    
    button.disabled = true;
    hideResult('report-result');
    showLoading('report-loading');
    
    // Update loading text based on report type
    const loadingText = reportType === 'annual' 
        ? 'Generating annual report... This may take a few minutes.'
        : 'Generating mid-year report... This may take a few minutes.';
    document.getElementById('report-loading-text').textContent = loadingText;
    
    // Determine endpoint based on report type
    const endpoint = reportType === 'annual' ? '/api/generate-annual' : '/api/generate';
    
    try {
        const data = await makeApiCall(endpoint, {
            indicator: indicator,
            year: year,
            insert_data: false
        });
        
        const content = formatMarkdown(data.content || 'No content received');
        document.getElementById('report-content').innerHTML = content;
        
        // Store data for download
        window.lastReport = {
            content: data.content,
            indicator: indicator,
            year: year,
            type: reportType
        };
        
        showResult('report-result');
    } catch (error) {
        showError(error.message, 'report-result');
    } finally {
        hideLoading('report-loading');
        button.disabled = false;
    }
}

// Tab 2: Summary Tables
async function generateTables() {
    const button = document.getElementById('generate-tables');
    const year = parseInt(document.getElementById('year-tables-select').value);
    
    button.disabled = true;
    hideResult('tables-result');
    showLoading('tables-loading');
    
    try {
        const data = await makeApiCall('/api/generate-annual-tables', { 
            indicator: "PDO Indicator 1", // Dummy indicator for tables endpoint
            year: year,
            insert_data: false
        });
        
        const tablesContainer = document.getElementById('tables-content');
        tablesContainer.innerHTML = '';
        
        // Store data for download
        window.lastTablesData = { tables: data.tables, year: year };
        
        Object.entries(data.tables).forEach(([groupName, tableData]) => {
            if (tableData && tableData.length > 0) {
                const sectionDiv = document.createElement('div');
                sectionDiv.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 2rem 0 1rem 0;">
                        <h3 style="color: var(--primary-blue);">${groupName}</h3>
                        <button onclick="downloadTableAsExcel('${groupName}')" class="btn btn-secondary" style="padding: 0.5rem 1rem; font-size: 0.875rem;">
                            <i class="fas fa-download"></i> Download ${groupName}
                        </button>
                    </div>
                `;
                
                const tableContainer = document.createElement('div');
                tableContainer.className = 'table-container';
                
                const table = document.createElement('table');
                table.className = 'data-table';
                
                if (tableData.length > 0) {
                    // Create header
                    const thead = document.createElement('thead');
                    const headerRow = document.createElement('tr');
                    Object.keys(tableData[0]).forEach(key => {
                        const th = document.createElement('th');
                        th.textContent = key;
                        headerRow.appendChild(th);
                    });
                    thead.appendChild(headerRow);
                    table.appendChild(thead);
                    
                    // Create body
                    const tbody = document.createElement('tbody');
                    tableData.forEach(row => {
                        const tr = document.createElement('tr');
                        Object.values(row).forEach(value => {
                            const td = document.createElement('td');
                            td.innerHTML = formatMarkdown(value?.toString() || '');
                            tr.appendChild(td);
                        });
                        tbody.appendChild(tr);
                    });
                    table.appendChild(tbody);
                }
                
                tableContainer.appendChild(table);
                sectionDiv.appendChild(tableContainer);
                tablesContainer.appendChild(sectionDiv);
            }
        });
        
        showResult('tables-result');
    } catch (error) {
        showError(error.message, 'tables-result');
    } finally {
        hideLoading('tables-loading');
        button.disabled = false;
    }
}

function downloadTableAsExcel(groupName) {
    if (window.lastTablesData && window.lastTablesData.tables[groupName]) {
        const filename = `${groupName}_summary_${window.lastTablesData.year}.csv`;
        downloadAsExcel(window.lastTablesData.tables[groupName], filename);
    }
}

// Tab 3: Challenges Report
async function generateChallengesReport() {
    const button = document.getElementById('generate-challenges');
    const year = parseInt(document.getElementById('year-challenges-select').value);
    
    button.disabled = true;
    hideResult('challenges-result');
    showLoading('challenges-loading');
    
    try {
        const data = await makeApiCall('/api/generate-challenges', {
            indicator: "PDO Indicator 1", // Dummy indicator for challenges endpoint
            year: year,
            insert_data: false
        });
        
        const content = formatMarkdown(data.content || 'No content received');
        document.getElementById('challenges-content').innerHTML = content;
        
        // Store data for download
        window.lastChallengesReport = {
            content: data.content,
            year: year
        };
        
        showResult('challenges-result');
    } catch (error) {
        showError(error.message, 'challenges-result');
    } finally {
        hideLoading('challenges-loading');
        button.disabled = false;
    }
}

// Download functions
function downloadReport() {
    if (window.lastReport) {
        const reportTypeName = window.lastReport.type === 'annual' ? 'annual_report' : 'midyear_report';
        const filename = `${reportTypeName}_${window.lastReport.indicator}_${window.lastReport.year}.txt`;
        downloadAsDocx(window.lastReport.content, filename);
    }
}

function downloadChallengesReport() {
    if (window.lastChallengesReport) {
        const filename = `challenges_lessons_learned_${window.lastChallengesReport.year}.txt`;
        downloadAsDocx(window.lastChallengesReport.content, filename);
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Display user info if available from URL
    displayUserInfo();
    
    // Reports tab (Annual and Mid-Year)
    document.getElementById('generate-report').addEventListener('click', generateReport);
    document.getElementById('download-report').addEventListener('click', downloadReport);
    
    // Tables tab
    document.getElementById('generate-tables').addEventListener('click', generateTables);
    
    // Challenges tab
    document.getElementById('generate-challenges').addEventListener('click', generateChallengesReport);
    document.getElementById('download-challenges').addEventListener('click', downloadChallengesReport);
    
    // Set default active tab
    document.querySelector('.tab.active').click();
});

function displayUserInfo() {
    if (userInfo.email || userInfo.user) {
        // Create user info display element if it doesn't exist
        let userInfoDisplay = document.getElementById('user-info-display');
        if (!userInfoDisplay) {
            userInfoDisplay = document.createElement('div');
            userInfoDisplay.id = 'user-info-display';
            userInfoDisplay.className = 'user-info-banner';
            userInfoDisplay.style.cssText = `
                background: linear-gradient(135deg, var(--very-light-blue), var(--white));
                padding: 1rem 2rem;
                border-radius: 8px;
                margin-bottom: 2rem;
                border-left: 4px solid var(--primary-blue);
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            `;
            
            // Insert after header
            const header = document.querySelector('.header');
            header.parentNode.insertBefore(userInfoDisplay, header.nextSibling);
        }
        
        let infoText = '<i class="fas fa-user" style="color: var(--primary-blue); margin-right: 0.5rem;"></i>';
        
        if (userInfo.user) {
            infoText += `<strong>Welcome, ${userInfo.user}!</strong>`;
        } else if (userInfo.email) {
            // Extract username from email (part before @)
            const emailUsername = userInfo.email.split('@')[0];
            infoText += `<strong>Welcome, ${emailUsername}!</strong>`;
        }
        
        userInfoDisplay.innerHTML = infoText;
    }
}

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
});