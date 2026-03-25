class AICCRATextMiningUI {
    constructor() {
        this.apiBaseUrl = 'https://oxnrkcntlheycdgcnilexrwp4i0tucqz.lambda-url.us-east-1.on.aws';
        // this.apiBaseUrl = 'http://localhost:8000';
        this.bucket = 'ai-services-ibd';
        this.projectType = 'AICCRA';
        this.folderPath = 'aiccra/text-mining/files/test/';
        this.lastResult = null;
        this.searchTimeout = null;
        
        this.defaultPlaceholderPrompt = null;
        
        // Prompt configuration state
        this.currentPromptMode = 'default';
        this.currentCustomPrompt = '';
        
        // Get URL parameters
        this.urlParams = this.getURLParameters();
        
        this.init();
    }

    init() {
        this.createHTML();
        this.bindEvents();
        
        // Use setTimeout to ensure DOM is fully ready
        setTimeout(() => {
            this.setInitialValues();
        }, 100);
    }

    getURLParameters() {
        const params = new URLSearchParams(window.location.search);
        const urlParams = {
            user_email: params.get('user_email') || '',
            user_name: params.get('user') || ''
        };
        
        // Debug logs
        console.log('Current URL:', window.location.href);
        console.log('Search params:', window.location.search);
        console.log('Parsed parameters:', urlParams);
        
        return urlParams;
    }

    setInitialValues() {
        // Set email from URL parameter if available
        const userEmailInput = document.getElementById('userEmail');
        if (!userEmailInput) {
            console.error('userEmail input not found');
            return;
        }

        console.log('URL Parameters:', this.urlParams); // Debug log
        
        if (this.urlParams.user_email) {
            console.log('Setting email from URL:', this.urlParams.user_email); // Debug log
            userEmailInput.value = this.urlParams.user_email;
            userEmailInput.style.borderColor = 'var(--green)';
            userEmailInput.style.backgroundColor = '#f0fff4';
            
            // Show user info banner
            this.showUserInfoBanner();
            
            // Trigger the change event
            userEmailInput.dispatchEvent(new Event('input'));
        } else {
            console.log('No email parameter found in URL'); // Debug log
        }
    }

    showUserInfoBanner() {
        if (!this.urlParams.user_email) return;
        
        const banner = document.getElementById('user-info-banner');
        if (banner) {
            let infoText = '<i class="fas fa-user" style="color: var(--primary-blue); margin-right: 0.5rem;"></i>';
            
            if (this.urlParams.user_name) {
                infoText += `<strong>Welcome, ${this.urlParams.user_name}!</strong>`;
            } else {
                // Extract username from email (part before @)
                const emailUsername = this.urlParams.user_email.split('@')[0];
                infoText += `<strong>Welcome, ${emailUsername}!</strong>`;
            }
            
            banner.innerHTML = infoText;
            banner.style.display = 'block';
        }
        
        // Also show the temporary notification
        this.showURLParameterInfo();
    }

    showURLParameterInfo() {
        if (!this.urlParams.user_email) return;
        
        // Show temporary notification banner using modern design
        const notification = document.createElement('div');
        notification.className = 'notification success';
        notification.innerHTML = `
            <i class="fas fa-check-circle"></i>
            <span>User information loaded from URL</span>
        `;
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--green);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            animation: slideInRight 0.3s ease-out;
        `;
        
        document.body.appendChild(notification);
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-out forwards';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    createHTML() {
        document.body.innerHTML = `
            <div class="container">
                <div class="header">
                    <h1><i class="fas fa-brain"></i> AICCRA Text Mining</h1>
                    <p class="subtitle">Extract insights from your documents using AI</p>
                </div>

                <!-- User Info Banner (will be populated if email comes from URL) -->
                <div id="user-info-banner" class="user-info-banner" style="display: none;"></div>

                <!-- AI Warning Banner -->
                <div class="disclaimer">
                    <div class="disclaimer-title">
                        <i class="fas fa-exclamation-triangle" style="color: var(--purple);"></i> AI-Powered Service
                    </div>
                    <div class="disclaimer-text">
                        This service uses AI to analyze documents. Results should be validated before use in decision-making.
                    </div>
                </div>

                <!-- Feature Overview -->
                <div class="feature-grid">
                    <div class="feature-card">
                        <h3><i class="fas fa-upload"></i> Document Upload</h3>
                        <p>Upload files directly or select from cloud storage (S3) with support for multiple formats.</p>
                    </div>
                    <div class="feature-card">
                        <h3><i class="fas fa-cogs"></i> Custom Analysis</h3>
                        <p>Use default AICCRA prompts or create custom analysis instructions for specialized extraction.</p>
                    </div>
                    <div class="feature-card">
                        <h3><i class="fas fa-chart-bar"></i> Structured Results</h3>
                        <p>Get organized, structured data extraction with JSON output and visual result presentation.</p>
                    </div>
                </div>

                <!-- Main Content Card -->
                <div class="main-card">
                    <!-- Configuration Section -->
                    <div class="section">
                        <div class="section-header">
                            <h2><i class="fas fa-user"></i> User Information</h2>
                            <button id="customPromptConfigBtn" class="config-btn" title="Custom Prompt Configuration">
                                <i class="fas fa-cog"></i>
                            </button>
                        </div>
                        
                        <div class="form-group">
                            <label for="userEmail">Email Address</label>
                            <input type="email" id="userEmail" class="form-control" placeholder="your@email.com" />
                            <div class="input-hint" id="emailHint" style="display: none;">
                                <i class="fas fa-info-circle"></i> Your email will be used for tracking and notifications
                            </div>
                        </div>

                        <div class="form-group">
                            <label>Analysis Mode</label>
                            <div class="input-hint">
                                <i class="fas fa-magic"></i> Using the standard AICCRA prompt optimized for extracting climate adaptation and agriculture-related information. 
                                <span id="customPromptIndicator" style="display: none; color: var(--purple); font-weight: 600;">
                                    <i class="fas fa-edit"></i> Custom prompt active
                                </span>
                            </div>
                        </div>
                    </div>

                    <!-- Document Source Section -->
                    <div class="section">
                        <div class="section-header">
                            <h2><i class="fas fa-file-alt"></i> Document Source</h2>
                        </div>

                        <div class="tabs source-tabs">
                            <input type="radio" name="mode" value="upload" id="upload-tab" checked>
                            <label for="upload-tab" class="tab">
                                <i class="fas fa-upload"></i> Upload File
                            </label>
                            
                            <input type="radio" name="mode" value="s3" id="s3-tab">
                            <label for="s3-tab" class="tab">
                                <i class="fas fa-cloud"></i> From Cloud Storage
                            </label>
                        </div>

                        <!-- Upload Section -->
                        <div id="uploadSection" class="tab-content">
                            <div class="file-upload-area" id="fileUploadArea">
                                <div class="upload-icon"><i class="fas fa-cloud-upload-alt"></i></div>
                                <div class="upload-text">
                                    <p><strong>Drag & drop your file here</strong></p>
                                    <p class="upload-subtext">or click to browse</p>
                                </div>
                                <input type="file" id="fileInput" accept=".pdf,.docx,.txt,.xlsx,.xls,.pptx" />
                            </div>
                            <div class="file-types">
                                <i class="fas fa-file"></i> Supported: PDF, DOCX, TXT, XLSX, XLS, PPTX
                            </div>
                            <div id="uploadInfo" class="upload-info" style="display:none;"></div>
                        </div>

                        <!-- S3 Section -->
                        <div id="s3Section" class="tab-content" style="display:none;">
                            <div class="form-group">
                                <label for="additionalPrefix">Additional Path (optional)</label>
                                <input type="text" id="additionalPrefix" class="form-control" placeholder="subfolder/" />
                                <div class="input-hint" id="searchInfo">
                                    <i class="fas fa-folder"></i> Searching in default folder
                                </div>
                            </div>
                            
                            <div class="form-group">
                                <button id="refreshBtn" class="btn btn-secondary">
                                    <i class="fas fa-sync-alt"></i> Refresh Files
                                </button>
                            </div>

                            <div class="form-group">
                                <label for="s3Select">Select File</label>
                                <select id="s3Select" class="form-control" disabled>
                                    <option>Loading...</option>
                                </select>
                            </div>
                        </div>

                        <!-- Process Button -->
                        <div class="process-section">
                            <button id="processBtn" class="btn btn-primary">
                                <i class="fas fa-cogs"></i> Process Document
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Loading -->
                <div id="loading" class="loading" style="display:none;">
                    <div class="spinner"></div>
                    <p><strong>Processing Document</strong></p>
                    <p>Analyzing your document with AI...</p>
                </div>

                <!-- Results -->
                <div id="results" class="result" style="display:none;">
                    <div class="result-success">
                        <div id="successMessage" class="success-message"></div>
                    </div>

                    <div class="result-section">
                        <div class="result-header expandable-header" data-target="rawJson">
                            <div class="result-title">
                                <i class="fas fa-code"></i>
                                <h3>Raw JSON Output</h3>
                            </div>
                            <i class="fas fa-chevron-down expand-icon"></i>
                        </div>
                        <div id="rawJson" class="result-content expandable-content" style="display:none;">
                            <pre id="jsonContent" class="json-output"></pre>
                        </div>
                    </div>

                    <div id="processedResults"></div>
                </div>

                <!-- Error -->
                <div id="error" class="alert alert-error" style="display:none;">
                    <i class="fas fa-exclamation-triangle"></i>
                    <div class="error-message"></div>
                </div>

                <!-- Custom Prompt Configuration Modal -->
                <div id="customPromptModal" class="modal" style="display: none;">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h3><i class="fas fa-edit"></i> Custom Prompt Configuration</h3>
                            <button class="modal-close" id="closeModalBtn">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        
                        <div class="modal-body">
                            <div class="form-group">
                                <label>Analysis Prompt Mode</label>
                                
                                <div class="tabs prompt-tabs">
                                    <input type="radio" name="promptMode" value="default" id="default-prompt-tab" checked>
                                    <label for="default-prompt-tab" class="tab">
                                        <i class="fas fa-magic"></i> Default Prompt
                                    </label>
                                    
                                    <input type="radio" name="promptMode" value="custom" id="custom-prompt-tab">
                                    <label for="custom-prompt-tab" class="tab">
                                        <i class="fas fa-edit"></i> Custom Prompt
                                    </label>
                                </div>

                                <!-- Default Prompt Info -->
                                <div id="defaultPromptSection" class="prompt-section">
                                    <div class="input-hint">
                                        <i class="fas fa-magic"></i> Using the standard AICCRA prompt optimized for extracting climate adaptation and agriculture-related information.
                                    </div>
                                </div>

                                <!-- Custom Prompt Section -->
                                <div id="customPromptSection" class="prompt-section" style="display: none;">
                                    <div class="custom-prompt-controls">
                                        <button type="button" id="loadPlaceholderBtn" class="btn btn-secondary">
                                            <i class="fas fa-download"></i> Load Template
                                        </button>
                                        <button type="button" id="downloadPromptBtn" class="btn btn-secondary">
                                            <i class="fas fa-save"></i> Download Prompt
                                        </button>
                                    </div>
                                    
                                    <textarea id="customPrompt" class="form-control" rows="8" 
                                        placeholder="Enter your custom prompt here or click 'Load Template' to start with the default AICCRA prompt..."></textarea>
                                    
                                    <div class="input-hint">
                                        <i class="fas fa-lightbulb"></i> <strong>Tips:</strong><br/>
                                        • Click "Load Template" to start with the default AICCRA prompt<br/>
                                        • Edit the prompt to customize how the AI analyzes your document<br/>
                                        • Click "Download Prompt" to save your customized prompt
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="modal-footer">
                            <button class="btn btn-secondary" id="cancelModalBtn">
                                <i class="fas fa-times"></i> Cancel
                            </button>
                            <button class="btn btn-primary" id="saveModalBtn">
                                <i class="fas fa-save"></i> Apply Configuration
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        const style = document.createElement('style');
        style.textContent = `
            :root {
                --primary-blue: #0478A3;
                --secondary-blue: #3A84A7;
                --light-blue: #81B8C1;
                --very-light-blue: #E7F4FF;
                --yellow: #FFCD2A;
                --purple: #8B5CF6;
                --green: #8CBF3F;
                --orange: #F39820;
                --white: #ffffff;
                --gray-50: #f8fafc;
                --gray-100: #f1f5f9;
                --gray-200: #e2e8f0;
                --gray-300: #cbd5e1;
                --gray-400: #94a3b8;
                --gray-500: #64748b;
                --gray-600: #475569;
                --gray-700: #334155;
                --gray-800: #1e293b;
                --gray-900: #0f172a;
            }

            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, var(--very-light-blue) 0%, var(--white) 100%);
                min-height: 100vh;
                color: var(--gray-800);
                line-height: 1.6;
            }

            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }

            /* Header */
            .header {
                text-align: center;
                margin-bottom: 3rem;
                padding: 2rem 0;
            }

            .header h1 {
                font-size: 3rem;
                font-weight: 700;
                background: linear-gradient(135deg, var(--primary-blue), var(--secondary-blue));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 0.5rem;
            }

            .header .subtitle {
                font-size: 1.25rem;
                color: var(--gray-600);
                font-weight: 400;
            }

            /* User Info Banner */
            .user-info-banner {
                background: linear-gradient(135deg, var(--very-light-blue), var(--white));
                padding: 1rem 2rem;
                border-radius: 8px;
                margin-bottom: 2rem;
                border-left: 4px solid var(--primary-blue);
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                font-size: 0.95rem;
                color: var(--gray-700);
            }

            /* Feature Grid */
            .feature-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }

            .feature-card {
                background: var(--white);
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border-top: 4px solid var(--secondary-blue);
            }

            .feature-card h3 {
                color: var(--primary-blue);
                margin-bottom: 0.5rem;
                font-size: 1.1rem;
            }

            .feature-card p {
                color: var(--gray-600);
                font-size: 0.9rem;
            }

            /* Main Card */
            .main-card {
                background: var(--white);
                border-radius: 16px;
                padding: 2rem;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
                margin-bottom: 2rem;
            }

            /* Sections */
            .section {
                margin-bottom: 2rem;
            }

            .section:last-child {
                margin-bottom: 0;
            }

            .section-header {
                margin-bottom: 1.5rem;
                padding-bottom: 0.5rem;
                border-bottom: 2px solid var(--very-light-blue);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .section-header h2 {
                color: var(--primary-blue);
                font-size: 1.5rem;
                font-weight: 600;
            }

            .config-btn {
                background: var(--purple);
                color: var(--white);
                border: none;
                padding: 0.5rem;
                border-radius: 50%;
                width: 2.5rem;
                height: 2.5rem;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 1rem;
            }

            .config-btn:hover {
                background: #7c3aed;
                transform: scale(1.05);
            }

            /* Form Controls */
            .form-group {
                margin-bottom: 1.5rem;
            }

            .form-group label {
                display: block;
                margin-bottom: 0.5rem;
                font-weight: 500;
                color: var(--gray-700);
            }

            .form-control {
                width: 100%;
                padding: 0.75rem 1rem;
                border: 2px solid var(--gray-200);
                border-radius: 8px;
                font-size: 1rem;
                transition: all 0.3s ease;
                background: var(--white);
                font-family: inherit;
            }

            .form-control:focus {
                outline: none;
                border-color: var(--primary-blue);
                box-shadow: 0 0 0 3px rgba(4, 120, 163, 0.1);
            }

            textarea.form-control {
                resize: vertical;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                font-size: 0.9rem;
                line-height: 1.4;
                min-height: 150px;
            }

            .form-control::placeholder {
                color: var(--gray-400);
                font-style: italic;
            }

            /* Input Hints */
            .input-hint {
                margin-top: 0.5rem;
                font-size: 0.875rem;
                color: var(--gray-600);
                background: var(--gray-50);
                padding: 0.5rem;
                border-radius: 6px;
                border-left: 3px solid var(--light-blue);
            }

            /* Tabs */
            .tabs {
                display: flex;
                background: var(--white);
                border-radius: 12px;
                padding: 4px;
                margin-bottom: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }

            .tabs input[type="radio"] {
                display: none;
            }

            .tab {
                flex: 1;
                padding: 0.75rem 1.5rem;
                text-align: center;
                border: none;
                background: transparent;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
                transition: all 0.3s ease;
                color: var(--gray-600);
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
            }

            .tabs input[type="radio"]:checked + .tab {
                background: var(--primary-blue);
                color: var(--white);
                box-shadow: 0 2px 4px rgba(4, 120, 163, 0.3);
            }

            .tab:hover:not(:has(input:checked)) {
                background: var(--very-light-blue);
                color: var(--primary-blue);
            }

            /* Tab Content */
            .tab-content {
                display: none;
            }

            /* Prompt Sections */
            .prompt-section {
                transition: all 0.3s ease;
            }

            .custom-prompt-controls {
                display: flex;
                gap: 0.5rem;
                margin-bottom: 1rem;
                flex-wrap: wrap;
            }

            /* File Upload Area */
            .file-upload-area {
                border: 2px dashed var(--light-blue);
                border-radius: 12px;
                padding: 3rem 2rem;
                text-align: center;
                transition: all 0.3s ease;
                cursor: pointer;
                position: relative;
                background: var(--gray-50);
            }

            .file-upload-area:hover {
                border-color: var(--primary-blue);
                background: var(--very-light-blue);
                transform: translateY(-2px);
            }

            .file-upload-area.dragover {
                border-color: var(--green);
                background: #f0fff4;
                transform: scale(1.02);
            }

            .upload-icon {
                font-size: 3rem;
                margin-bottom: 1rem;
                color: var(--light-blue);
            }

            .upload-text p {
                font-size: 1.1rem;
                color: var(--gray-600);
                margin-bottom: 0.5rem;
            }

            .upload-subtext {
                color: var(--gray-500) !important;
                font-size: 0.9rem !important;
            }

            .file-upload-area input[type="file"] {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                opacity: 0;
                cursor: pointer;
            }

            .file-types {
                margin-top: 1rem;
                text-align: center;
                font-size: 0.875rem;
                color: var(--gray-500);
            }

            .upload-info {
                margin-top: 1rem;
                padding: 1rem;
                background: var(--very-light-blue);
                border: 1px solid var(--light-blue);
                border-radius: 8px;
                color: var(--primary-blue);
            }

            /* Buttons */
            .btn {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.875rem 2rem;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                justify-content: center;
                font-family: inherit;
            }

            .btn-primary {
                background: linear-gradient(135deg, var(--primary-blue), var(--secondary-blue));
                color: var(--white);
            }

            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(4, 120, 163, 0.3);
            }

            .btn-secondary {
                background: var(--green);
                color: var(--white);
            }

            .btn-secondary:hover {
                background: #7aa836;
                transform: translateY(-2px);
            }

            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none !important;
            }

            /* Process Section */
            .process-section {
                margin-top: 2rem;
                padding-top: 1.5rem;
                border-top: 1px solid var(--gray-200);
            }

            .process-section .btn {
                width: 100%;
                font-size: 1.1rem;
                padding: 1rem 2rem;
            }

            /* Loading */
            .loading {
                display: none;
                text-align: center;
                padding: 3rem;
                background: var(--white);
                border-radius: 16px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
                margin-bottom: 2rem;
            }

            .loading.show {
                display: block;
            }

            .spinner {
                width: 50px;
                height: 50px;
                border: 4px solid var(--light-blue);
                border-top: 4px solid var(--primary-blue);
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 1rem;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            /* Results */
            .result {
                display: none;
                margin-top: 2rem;
            }

            .result.show {
                display: block;
            }

            .result-success {
                background: linear-gradient(135deg, var(--green) 0%, #a8d158 100%);
                padding: 1rem 2rem;
                border-radius: 12px;
                margin-bottom: 2rem;
                color: var(--white);
                box-shadow: 0 4px 12px rgba(140, 191, 63, 0.3);
            }

            .success-message {
                font-weight: 600;
                font-size: 1.1rem;
                text-align: center;
            }

            .result-section {
                background: var(--white);
                border-radius: 12px;
                margin-bottom: 1.5rem;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }

            .result-header {
                padding: 1rem 1.5rem;
                background: var(--gray-50);
                border-bottom: 1px solid var(--gray-200);
                display: flex;
                align-items: center;
                justify-content: space-between;
                cursor: pointer;
                transition: all 0.3s ease;
            }

            .result-header:hover {
                background: var(--very-light-blue);
            }

            .result-title {
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }

            .result-title h3 {
                font-size: 1.25rem;
                font-weight: 600;
                color: var(--gray-800);
                margin: 0;
            }

            .expand-icon {
                color: var(--primary-blue);
                transition: transform 0.3s ease;
            }

            .result-content {
                padding: 1.5rem;
                transition: all 0.3s ease;
            }

            .json-output {
                background: var(--gray-50);
                padding: 1.5rem;
                border-radius: 8px;
                overflow-x: auto;
                font-size: 0.9rem;
                border: 1px solid var(--gray-200);
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            }

            /* Alerts */
            .alert {
                padding: 1rem 1.5rem;
                border-radius: 8px;
                margin: 1rem 0;
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }

            .alert-error {
                background: #fef2f2;
                color: #b91c1c;
                border-left: 4px solid #ef4444;
            }

            /* Disclaimer */
            .disclaimer {
                margin-bottom: 2rem;
                padding: 1.5rem;
                background: #f3f0ff;
                border-left: 4px solid var(--purple);
                border-radius: 8px;
            }

            .disclaimer-title {
                font-weight: 600;
                color: var(--gray-800);
                margin-bottom: 0.5rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .disclaimer-text {
                color: var(--gray-700);
                font-size: 0.9rem;
            }

            /* Result Item Styles */
            .result-item {
                margin-bottom: 1.5rem;
                border-radius: 8px;
                overflow: hidden;
            }

            .result-field {
                margin-bottom: 1rem;
                padding-bottom: 0.75rem;
                border-bottom: 1px solid var(--gray-200);
            }

            .result-field:last-child {
                border-bottom: none;
                margin-bottom: 0;
            }

            .result-field strong {
                color: var(--primary-blue);
                font-weight: 600;
                display: block;
                margin-bottom: 0.25rem;
            }

            .result-table {
                overflow-x: auto;
                background: var(--white);
                border-radius: 6px;
                border: 1px solid var(--gray-200);
            }

            .result-table table {
                width: 100%;
                border-collapse: collapse;
                margin: 0;
            }

            .result-table th {
                background: var(--gray-50);
                color: var(--gray-700);
                font-weight: 600;
                padding: 0.75rem;
                text-align: left;
                border-bottom: 2px solid var(--gray-200);
                font-size: 0.875rem;
            }

            .result-table td {
                padding: 0.75rem;
                border-bottom: 1px solid var(--gray-100);
                color: var(--gray-700);
                font-size: 0.875rem;
            }

            .result-table tr:last-child td {
                border-bottom: none;
            }

            .result-table tr:hover {
                background: var(--gray-50);
            }

            /* Modal Styles */
            .modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                animation: fadeIn 0.3s ease-out;
            }

            .modal-content {
                background: var(--white);
                border-radius: 16px;
                width: 90%;
                max-width: 800px;
                max-height: 90vh;
                overflow-y: auto;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                animation: slideUp 0.3s ease-out;
            }

            .modal-header {
                padding: 1.5rem 2rem;
                border-bottom: 1px solid var(--gray-200);
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: linear-gradient(135deg, var(--very-light-blue), var(--white));
            }

            .modal-header h3 {
                margin: 0;
                color: var(--primary-blue);
                font-size: 1.5rem;
                font-weight: 600;
            }

            .modal-close {
                background: none;
                border: none;
                font-size: 1.25rem;
                color: var(--gray-500);
                cursor: pointer;
                padding: 0.5rem;
                border-radius: 50%;
                width: 2.5rem;
                height: 2.5rem;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
            }

            .modal-close:hover {
                background: var(--gray-100);
                color: var(--gray-700);
            }

            .modal-body {
                padding: 2rem;
            }

            .modal-footer {
                padding: 1.5rem 2rem;
                border-top: 1px solid var(--gray-200);
                display: flex;
                gap: 1rem;
                justify-content: flex-end;
                background: var(--gray-50);
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            /* Responsive Design */
            @media (max-width: 768px) {
                .container {
                    padding: 1rem;
                }

                .header h1 {
                    font-size: 2rem;
                }

                .main-card {
                    padding: 1.5rem;
                }

                .feature-grid {
                    grid-template-columns: 1fr;
                }

                .tabs {
                    flex-direction: column;
                    gap: 4px;
                }

                .file-upload-area {
                    padding: 2rem 1rem;
                }

                .custom-prompt-controls {
                    flex-direction: column;
                }

                .btn {
                    padding: 0.75rem 1.5rem;
                    font-size: 0.9rem;
                }
            }

            /* Animations */
            .main-card, .result-section, .feature-card {
                animation: slideUp 0.3s ease-out;
            }

            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes slideInRight {
                from {
                    opacity: 0;
                    transform: translateX(30px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }

            @keyframes slideOutRight {
                from {
                    opacity: 1;
                    transform: translateX(0);
                }
                to {
                    opacity: 0;
                    transform: translateX(30px);
                }
            }

            /* Hide/Show Classes */
            .hidden { display: none !important; }
            .show { display: block !important; }
        `;
        document.head.appendChild(style);
    }

    bindEvents() {
        // Mode switching
        document.querySelectorAll('input[name="mode"]').forEach(radio => {
            radio.addEventListener('change', () => this.handleModeChange());
        });

        // File input and drag & drop
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('fileUploadArea');

        fileInput.addEventListener('change', () => this.handleFileChange());

        // Drag and drop events
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                this.handleFileChange();
            }
        });

        // Process button
        document.getElementById('processBtn').addEventListener('click', () => this.processDocument());

        // Expandable sections
        document.addEventListener('click', (e) => {
            if (e.target.closest('.expandable-header')) {
                this.toggleExpandable(e.target.closest('.expandable-header'));
            }
        });

        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => this.loadS3Objects());

        // Additional prefix input
        document.getElementById('additionalPrefix').addEventListener('input', () => this.updateSearchInfo());

        // Load placeholder prompt
        document.getElementById('loadPlaceholderBtn').addEventListener('click', () => this.loadPlaceholderPrompt());

        // Download custom prompt
        document.getElementById('downloadPromptBtn').addEventListener('click', () => this.downloadPrompt());

        // Custom prompt changes
        document.getElementById('customPrompt').addEventListener('input', () => this.handleCustomPromptChange());

        // Email input changes
        document.getElementById('userEmail').addEventListener('input', () => this.handleEmailChange());

        // Custom Prompt Modal
        document.getElementById('customPromptConfigBtn').addEventListener('click', () => this.openCustomPromptModal());
        document.getElementById('closeModalBtn').addEventListener('click', () => this.closeCustomPromptModal());
        document.getElementById('cancelModalBtn').addEventListener('click', () => this.closeCustomPromptModal());
        document.getElementById('saveModalBtn').addEventListener('click', () => this.saveCustomPromptConfig());

        // Modal background click to close
        document.getElementById('customPromptModal').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                this.closeCustomPromptModal();
            }
        });

        // Modal prompt mode switching
        document.querySelectorAll('input[name="promptMode"]').forEach(radio => {
            radio.addEventListener('change', () => this.handleModalPromptModeChange());
        });

        // Initial setup
        this.handleModeChange();
        this.updateSearchInfo();
        
        // Additional check for URL parameters after a delay (for production issues)
        setTimeout(() => {
            this.checkAndRetryURLParams();
        }, 1000);
    }

    checkAndRetryURLParams() {
        const userEmailInput = document.getElementById('userEmail');
        
        // If email field is empty but we have URL params, try again
        if (userEmailInput && !userEmailInput.value && window.location.search.includes('user_email')) {
            console.log('Retrying URL parameter extraction...');
            this.urlParams = this.getURLParameters();
            this.setInitialValues();
        }
    }

    handleModeChange() {
        const mode = document.querySelector('input[name="mode"]:checked').value;
        const uploadSection = document.getElementById('uploadSection');
        const s3Section = document.getElementById('s3Section');

        if (mode === 'upload') {
            uploadSection.style.display = 'block';
            s3Section.style.display = 'none';
        } else {
            uploadSection.style.display = 'none';
            s3Section.style.display = 'block';
            this.loadS3Objects();
        }
    }

    handleFileChange() {
        const fileInput = document.getElementById('fileInput');
        const uploadInfo = document.getElementById('uploadInfo');
        const uploadArea = document.getElementById('fileUploadArea');
        
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            uploadInfo.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1.2rem;">📁</span>
                    <strong>Selected:</strong> ${file.name}
                </div>
                <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #666;">
                    Will be uploaded to: <code>${this.bucket}/${this.folderPath}${file.name}</code>
                </div>
            `;
            uploadInfo.style.display = 'block';
            
            uploadArea.style.borderColor = '#8CBF3F';
            uploadArea.style.backgroundColor = '#f0fff4';
        } else {
            uploadInfo.style.display = 'none';
            uploadArea.style.borderColor = '#cbd5e0';
            uploadArea.style.backgroundColor = '#fafafa';
        }
    }

    updateSearchInfo() {
        const additionalPrefix = document.getElementById('additionalPrefix').value;
        const searchInfo = document.getElementById('searchInfo');
        if (additionalPrefix.trim()) {
            searchInfo.innerHTML = `📁 Searching with prefix: <code>${additionalPrefix}</code>`;
        } else {
            searchInfo.innerHTML = `📁 Searching in default folder`;
        }
        
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        this.searchTimeout = setTimeout(() => {
            this.loadS3Objects();
        }, 500);
    }

    async loadPlaceholderPrompt() {
        const promptTextarea = document.getElementById('customPrompt');
        const loadBtn = document.getElementById('loadPlaceholderBtn');
        
        // Show loading state
        loadBtn.disabled = true;
        loadBtn.innerHTML = '<span class="btn-icon">⏳</span> Loading...';
        
        try {
            // Load prompt from backend if not already loaded
            if (!this.defaultPlaceholderPrompt) {
                const response = await fetch(`${this.apiBaseUrl}/aiccra/prompt`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error(`Failed to load prompt: ${response.status} ${response.statusText}`);
                }

                const data = await response.json();
                
                if (data.status === 'success') {
                    this.defaultPlaceholderPrompt = data.content;
                } else {
                    throw new Error(data.message || 'Failed to load prompt');
                }
            }
            
            // Set the prompt in the textarea
            promptTextarea.value = this.defaultPlaceholderPrompt;
            this.showInfo('✅ Template prompt loaded successfully! You can now edit it as needed.');
            
        } catch (error) {
            console.error('Error loading prompt:', error);
            this.showError('❌ Could not load prompt from backend. Please check your connection and try again.');
        } finally {
            // Reset button state
            loadBtn.disabled = false;
            loadBtn.innerHTML = '<span class="btn-icon">📋</span> Load Template';
        }
    }

    downloadPrompt() {
        const promptContent = document.getElementById('customPrompt').value.trim();
        
        if (!promptContent) {
            this.showError('❌ No prompt content to download. Please enter some text first.');
            return;
        }

        try {
            // Create a timestamp for the filename
            const now = new Date();
            const timestamp = now.toISOString().slice(0, 19).replace(/[T:]/g, '-');
            const filename = `aiccra-custom-prompt-${timestamp}.txt`;

            // Create blob and download
            const blob = new Blob([promptContent], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            
            // Create download link
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            link.style.display = 'none';
            
            // Trigger download
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Clean up
            window.URL.revokeObjectURL(url);
            
            this.showInfo(`💾 Prompt downloaded as "${filename}"`);
            
        } catch (error) {
            console.error('Error downloading prompt:', error);
            this.showError('❌ Error downloading prompt. Please try again.');
        }
    }

    handleCustomPromptChange() {
        const promptContent = document.getElementById('customPrompt').value.trim();
        const downloadBtn = document.getElementById('downloadPromptBtn');
        
        // Enable/disable download button based on content
        downloadBtn.disabled = !promptContent;
        downloadBtn.style.opacity = promptContent ? '1' : '0.6';
    }

    handleEmailChange() {
        const emailInput = document.getElementById('userEmail');
        const emailHint = document.getElementById('emailHint');
        const email = emailInput.value.trim();
        
        if (email) {
            emailHint.style.display = 'block';
            emailInput.style.borderColor = '#1079A4';
        } else {
            emailHint.style.display = 'none';
            emailInput.style.borderColor = '#e2e8f0';
        }
    }

    openCustomPromptModal() {
        const modal = document.getElementById('customPromptModal');
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
        
        // Initialize modal with current settings
        this.handleModalPromptModeChange();
        
        // Focus on the modal for accessibility
        modal.focus();
    }

    handleModalPromptModeChange() {
        const mode = document.querySelector('input[name="promptMode"]:checked').value;
        const defaultSection = document.getElementById('defaultPromptSection');
        const customSection = document.getElementById('customPromptSection');

        if (mode === 'default') {
            defaultSection.style.display = 'block';
            customSection.style.display = 'none';
        } else {
            defaultSection.style.display = 'none';
            customSection.style.display = 'block';
            // Initialize download button state
            this.handleCustomPromptChange();
        }
    }

    closeCustomPromptModal() {
        const modal = document.getElementById('customPromptModal');
        modal.style.display = 'none';
        document.body.style.overflow = 'auto'; // Restore scrolling
    }

    saveCustomPromptConfig() {
        const promptMode = document.querySelector('input[name="promptMode"]:checked').value;
        const customPromptContent = document.getElementById('customPrompt').value.trim();
        const indicator = document.getElementById('customPromptIndicator');
        
        if (promptMode === 'custom') {
            if (!customPromptContent) {
                this.showError('Please enter a custom prompt or switch to default mode.');
                return;
            }
            
            // Show custom prompt indicator
            indicator.style.display = 'inline';
            this.showInfo('✅ Custom prompt configuration saved!');
        } else {
            // Hide custom prompt indicator
            indicator.style.display = 'none';
            this.showInfo('✅ Using default AICCRA prompt.');
        }
        
        // Store the current prompt mode for processing
        this.currentPromptMode = promptMode;
        this.currentCustomPrompt = customPromptContent;
        
        this.closeCustomPromptModal();
    }

    showInfo(message) {
        // Create a temporary info message
        const infoDiv = document.createElement('div');
        infoDiv.className = 'info-message';
        infoDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #8CBF3F;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            font-weight: 500;
            max-width: 400px;
        `;
        infoDiv.textContent = message;
        document.body.appendChild(infoDiv);

        // Remove after 5 seconds
        setTimeout(() => {
            if (infoDiv.parentNode) {
                infoDiv.parentNode.removeChild(infoDiv);
            }
        }, 5000);
    }

    async loadS3Objects() {
        const select = document.getElementById('s3Select');
        const additionalPrefix = document.getElementById('additionalPrefix').value;
        const fullPrefix = this.folderPath + additionalPrefix;

        select.innerHTML = '<option>Loading...</option>';
        select.disabled = true;

        try {
            const response = await fetch(`${this.apiBaseUrl}/list-s3-objects`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    bucket: this.bucket,
                    prefix: fullPrefix,
                    max_items: 1000
                })
            });

            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.status === 'error') {
                throw new Error(data.message || 'Failed to list files');
            }

            const objects = data.objects || [];

            select.innerHTML = '';
            select.disabled = false;

            if (objects.length === 0) {
                select.innerHTML = '<option>No files found</option>';
                select.disabled = true;
            } else {
                select.innerHTML = '<option value="">Select a file...</option>';
                objects.forEach(key => {
                    const option = document.createElement('option');
                    option.value = key;
                    option.textContent = key.split('/').pop();
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading S3 objects:', error);
            select.innerHTML = '<option>Error loading files</option>';
            select.disabled = true;
            
            let errorMessage = `Failed to load S3 objects: ${error.message}`;
            
            if (error.message.includes('NetworkError') || error.message.includes('Network Failure')) {
                errorMessage = 'Network error. Please check your internet connection and try again.';
            } else if (error.message.includes('CORS')) {
                errorMessage = 'CORS error. The API may need to be configured to allow browser requests.';
            }
            
            this.showError(errorMessage);
        }
    }

    async processDocument() {
        const email = document.getElementById('userEmail').value.trim();
        if (!email) {
            this.showError('Please provide your email address.');
            return;
        }

        // Use stored prompt configuration instead of querying DOM elements
        const promptMode = this.currentPromptMode || 'default';
        let customPrompt = '';

        if (promptMode === 'custom') {
            customPrompt = this.currentCustomPrompt || '';
            
            if (!customPrompt) {
                this.showError('Please configure a custom prompt in the settings or switch to default mode.');
                return;
            }
        }

        const mode = document.querySelector('input[name="mode"]:checked').value;

        if (mode === 'upload') {
            const fileInput = document.getElementById('fileInput');
            if (!fileInput.files.length) {
                this.showError('Please select a file to upload.');
                return;
            }
            
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            formData.append('bucketName', this.bucket);
            formData.append('user_id', email);
            
            // Add custom prompt if provided
            if (customPrompt) {
                formData.append('prompt', customPrompt);
            }
            
            this.showLoading(true);
            this.hideError();
            this.hideResults();

            try {
                const startTime = Date.now();
                const response = await this.callAPI(formData);
                const elapsed = (Date.now() - startTime) / 1000;

                if (response.status === 'error' || response.isError) {
                    throw new Error(response.error || response.message || 'Unknown error occurred');
                }

                this.lastResult = response;
                this.showResults(response, elapsed);
            } catch (error) {
                this.showError(error.message);
            } finally {
                this.showLoading(false);
            }
        } else {
            const selectedKey = document.getElementById('s3Select').value;
            if (!selectedKey) {
                this.showError('Please select a file from S3.');
                return;
            }
            
            const formData = new FormData();
            formData.append('bucketName', this.bucket);
            formData.append('user_id', email);
            formData.append('key', selectedKey);
            
            // Add custom prompt if provided
            if (customPrompt) {
                formData.append('prompt', customPrompt);
            }

            this.showLoading(true);
            this.hideError();
            this.hideResults();

            try {
                const startTime = Date.now();
                const response = await this.callAPI(formData);
                const elapsed = (Date.now() - startTime) / 1000;

                if (response.status === 'error' || response.isError) {
                    throw new Error(response.error || response.message || 'Unknown error occurred');
                }

                this.lastResult = response;
                this.showResults(response, elapsed);
            } catch (error) {
                this.showError(error.message);
            } finally {
                this.showLoading(false);
            }
        }
    }

    async callAPI(formData) {
        const url = `${this.apiBaseUrl}/aiccra/text-mining`;
        
        const options = {
            method: 'POST',
            body: formData
        };

        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`API error ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    showLoading(show) {
        document.getElementById('loading').style.display = show ? 'block' : 'none';
    }

    showError(message) {
        const errorDiv = document.getElementById('error');
        const errorMessage = errorDiv.querySelector('.error-message');
        errorMessage.textContent = message;
        errorDiv.style.display = 'block';
        
        // Scroll to error
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    hideError() {
        document.getElementById('error').style.display = 'none';
    }

    hideResults() {
        document.getElementById('results').style.display = 'none';
    }

    showResults(result, elapsed) {
        const resultsDiv = document.getElementById('results');
        const successDiv = document.getElementById('successMessage');
        const jsonContent = document.getElementById('jsonContent');
        const processedResults = document.getElementById('processedResults');

        successDiv.innerHTML = `
            <span style="font-size: 1.2rem;">✅</span>
            Processing completed successfully! 
            <span style="font-weight: normal;">⏱️ ${elapsed.toFixed(2)}s</span>
        `;
        jsonContent.textContent = JSON.stringify(result, null, 2);

        // Extract and display structured results
        const extractedResults = this.extractResults(result);
        processedResults.innerHTML = this.renderStructuredResults(extractedResults);

        resultsDiv.style.display = 'block';
        
        // Scroll to results
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    extractResults(result) {
        // First, check if we already have a structured results format
        if (result.results) return result;
        
        const content = result.content;
        if (Array.isArray(content)) {
            for (const item of content) {
                if (item.text) {
                    try {
                        // Try to parse the text as JSON first
                        const parsed = JSON.parse(item.text);
                        if (parsed.results) return parsed;
                        if (parsed.json_content && parsed.json_content.results) return parsed.json_content;
                        
                        // Check if there's a nested json_content with text
                        if (parsed.json_content && parsed.json_content.text) {
                            // This is likely a free-form response, not structured JSON
                            return {
                                results: [],
                                freeFormResponse: parsed.json_content.text,
                                interactionId: parsed.interaction_id
                            };
                        }
                    } catch (e) {
                        // If JSON parsing fails, treat as free-form text
                        return {
                            results: [],
                            freeFormResponse: item.text,
                            rawContent: item
                        };
                    }
                }
            }
        }
        
        // If no content found, return empty structure
        return { results: [] };
    }

    renderStructuredResults(data) {
        const results = data.results || [];
        
        // Check if we have a free-form response (when custom prompt is used)
        if (data.freeFormResponse && results.length === 0) {
            return `
                <div class="result-section">
                    <div class="result-header expandable-header" data-target="freeFormResponse">
                        <div class="result-title">
                            <i class="fas fa-comments"></i>
                            <h3>AI Analysis Response</h3>
                        </div>
                        <i class="fas fa-chevron-down expand-icon"></i>
                    </div>
                    <div id="freeFormResponse" class="result-content expandable-content">
                        <div class="free-form-response">
                            ${this.renderFreeFormResponse(data.freeFormResponse)}
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Standard structured results display
        if (results.length === 0) {
            return `
                <div class="result-section">
                    <div class="result-content" style="text-align: center; padding: 3rem;">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">📄</div>
                        <h3 style="color: var(--gray-600); margin-bottom: 0.5rem;">No Results Found</h3>
                        <p style="color: var(--gray-500);">The document was processed but no structured data was extracted.</p>
                        <div class="input-hint" style="margin-top: 1rem;">
                            💡 <strong>Tip:</strong> Try using the "Load Template" option in Custom Prompt mode for structured data extraction.
                        </div>
                    </div>
                </div>
            `;
        }

        let html = `
            <div class="result-section">
                <div class="result-header expandable-header" data-target="extractedResults">
                    <div class="result-title">
                        <i class="fas fa-chart-bar"></i>
                        <h3>Extracted Results (${results.length} found)</h3>
                    </div>
                    <i class="fas fa-chevron-down expand-icon"></i>
                </div>
                <div id="extractedResults" class="result-content expandable-content">
        `;

        results.forEach((result, index) => {
            html += `
                <div class="result-item" style="background: var(--gray-50); margin-bottom: 1.5rem; padding: 1.5rem; border-radius: 8px; border-left: 4px solid var(--secondary-blue);">
                    <h4 style="color: var(--primary-blue); margin-bottom: 1rem; font-size: 1.1rem;">📊 Result ${index + 1}</h4>
                    ${this.renderResultFields(result)}
                </div>
            `;
        });

        html += `</div></div>`;
        return html;
    }

    renderResultFields(result) {
        const fieldMapping = {
            "indicator": "Indicator",
            "title": "Result title",
            "short_title": "Short result title",
            "description": "Description",
            "main_contact_person": "Main contact person",
            "keywords": "Keywords",
            "geoscope_level": "Geoscope level",
            "regions": "Regions codes",
            "countries": "Countries codes",
            "innovation_nature": "Innovation nature",
            "innovation_type": "Innovation type",
            "assess_readiness": "Readiness level",
            "anticipated_users": "Anticipated users",
            "innovation_actors_detailed": "Actors",
            "organizations_detailed": "Organizations"
        };

        let html = '';
        for (const [field, label] of Object.entries(fieldMapping)) {
            const value = result[field];
            if (value !== undefined && value !== null && value !== '') {
                html += this.renderField(field, label, value);
            }
        }
        return html || '<div class="result-field" style="color: #a0aec0; font-style: italic;">No data available</div>';
    }

    renderField(field, label, value) {
        if (field === 'keywords' && Array.isArray(value)) {
            const keywords = value.map(k => `<span style="background: #E7F4FF; color: #1079A4; padding: 0.25rem 0.5rem; border-radius: 15px; font-size: 0.875rem; margin-right: 0.5rem; display: inline-block; margin-bottom: 0.25rem; border: 1px solid #81B8C1;">${k}</span>`).join('');
            return `<div class="result-field"><strong>${label}:</strong><br/><div style="margin-top: 0.5rem;">${keywords}</div></div>`;
        } else if ((field === 'innovation_actors_detailed' || field === 'organizations_detailed') && Array.isArray(value)) {
            return `<div class="result-field">
                <strong>${label}:</strong>
                <div class="result-table" style="margin-top: 0.75rem;">${this.renderTable(value, field)}</div>
            </div>`;
        } else if (typeof value === 'object') {
            return `<div class="result-field"><strong>${label}:</strong><br/><pre style="margin-top: 0.5rem; background: #f7fafc; padding: 1rem; border-radius: 6px; font-size: 0.875rem; white-space: pre-wrap;">${JSON.stringify(value, null, 2)}</pre></div>`;
        } else {
            return `<div class="result-field"><strong>${label}:</strong> ${value}</div>`;
        }
    }

    renderFreeFormResponse(response) {
        // Clean up the response text
        let cleanResponse = response;
        
        // Remove code blocks but keep their content
        cleanResponse = cleanResponse.replace(/```[\s\S]*?```/g, '');
        
        // Convert markdown headers to HTML
        cleanResponse = cleanResponse.replace(/^### (.*$)/gim, '<h3 style="color: var(--primary-blue); margin: 1.5rem 0 0.75rem 0; font-size: 1.1rem;">$1</h3>');
        cleanResponse = cleanResponse.replace(/^## (.*$)/gim, '<h2 style="color: var(--primary-blue); margin: 1.5rem 0 0.75rem 0; font-size: 1.25rem;">$1</h2>');
        cleanResponse = cleanResponse.replace(/^# (.*$)/gim, '<h1 style="color: var(--primary-blue); margin: 1.5rem 0 1rem 0; font-size: 1.4rem;">$1</h1>');
        
        // Convert markdown bold and italic
        cleanResponse = cleanResponse.replace(/\*\*(.*?)\*\*/g, '<strong style="color: var(--gray-800);">$1</strong>');
        cleanResponse = cleanResponse.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Convert markdown lists
        cleanResponse = cleanResponse.replace(/^\* (.*$)/gim, '<li style="margin: 0.25rem 0;">$1</li>');
        cleanResponse = cleanResponse.replace(/^- (.*$)/gim, '<li style="margin: 0.25rem 0;">$1</li>');
        cleanResponse = cleanResponse.replace(/^\d+\. (.*$)/gim, '<li style="margin: 0.25rem 0;">$1</li>');
        
        // Wrap consecutive list items in ul tags
        cleanResponse = cleanResponse.replace(/(<li.*?<\/li>(?:\s*<li.*?<\/li>)*)/g, '<ul style="margin: 0.75rem 0; padding-left: 1.5rem;">$1</ul>');
        
        // Convert line breaks to paragraphs
        cleanResponse = cleanResponse.replace(/\n\n+/g, '</p><p>');
        cleanResponse = cleanResponse.replace(/\n/g, '<br>');
        
        // Clean up any multiple consecutive breaks
        cleanResponse = cleanResponse.replace(/<br>\s*<br>/g, '<br>');
        
        // Wrap in paragraphs if not already wrapped
        if (!cleanResponse.includes('<h1>') && !cleanResponse.includes('<h2>') && !cleanResponse.includes('<h3>') && !cleanResponse.includes('<p>')) {
            cleanResponse = `<p>${cleanResponse}</p>`;
        } else {
            // Add paragraph tags around non-header content
            cleanResponse = `<div>${cleanResponse}</div>`;
            cleanResponse = cleanResponse.replace(/<div>/, '<p>').replace(/<\/div>/, '</p>');
        }
        
        return `
            <div class="free-form-content" style="
                line-height: 1.7; 
                color: var(--gray-700); 
                font-size: 1rem;
                background: var(--gray-50);
                padding: 2rem;
                border-radius: 12px;
                border-left: 4px solid var(--green);
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            ">
                ${cleanResponse}
            </div>
            <div class="response-note" style="
                margin-top: 1rem; 
                padding: 1rem; 
                background: linear-gradient(135deg, var(--very-light-blue), var(--white)); 
                border-radius: 8px; 
                font-size: 0.9rem; 
                color: var(--primary-blue);
                border: 1px solid var(--light-blue);
                border-left: 4px solid var(--purple);
            ">
                <strong><i class="fas fa-info-circle"></i> Custom Analysis:</strong> This response was generated using your custom prompt. 
                The AI adapted its output format based on your specific instructions.
            </div>
        `;
    }

    renderTable(data, type) {
        if (!Array.isArray(data) || data.length === 0) {
            return '<p style="color: #a0aec0; font-style: italic; margin: 0.5rem 0;">No data available</p>';
        }

        const columns = type === 'innovation_actors_detailed' 
            ? { name: 'Actor name', type: 'Type', gender_age: 'Gender/Age', other_actor_type: 'Other type' }
            : { name: 'Organization name', type: 'Organization type', sub_type: 'Organization sub-type', other_type: 'Other type' };

        let html = '<table><thead><tr>';
        Object.values(columns).forEach(col => {
            html += `<th>${col}</th>`;
        });
        html += '</tr></thead><tbody>';

        data.forEach(row => {
            html += '<tr>';
            Object.keys(columns).forEach(key => {
                const cellValue = row[key] || '-';
                html += `<td>${cellValue}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        return html;
    }

    toggleExpandable(header) {
        const targetId = header.getAttribute('data-target');
        const content = document.getElementById(targetId);
        const icon = header.querySelector('.expand-icon');
        
        if (content.style.display === 'none') {
            content.style.display = 'block';
            icon.textContent = '−';
            icon.style.transform = 'rotate(180deg)';
        } else {
            content.style.display = 'none';
            icon.textContent = '+';
            icon.style.transform = 'rotate(0deg)';
        }
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AICCRATextMiningUI();
});