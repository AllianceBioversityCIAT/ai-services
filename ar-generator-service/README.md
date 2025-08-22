# AICCRA Annual Report Generator Service

An AI-powered service for generating comprehensive annual reports for AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa). This service combines an interface with automated report generation capabilities, leveraging vector databases and Large Language Models to produce high-quality, data-driven narratives.

---

## 🌟 Features

- **📊 AI-Powered Report Generation**: Automated reports using AWS Bedrock Claude 3.7 Sonnet
- **🔍 Vector Search Integration**: Advanced context retrieval using OpenSearch with hybrid search capabilities
- **📈 Multi-Indicator Support**: Comprehensive support for IPI and PDO indicators (2020-2030)
- **💾 Database Integration**: SQL Server connectivity for retrieving structured AICCRA data
- **🚀 REST API**: FastAPI-based service with comprehensive OpenAPI documentation
- **⚡ High Performance**: Optimized processing with configurable data refresh options
- **📋 Structured Responses**: Pydantic models for request/response validation
- **🔒 Enterprise Security**: AWS IAM authentication and secure credential management

---

## 🏗️ Architecture

The service is built as a REST API service with the following components:

### Core Components

1. **REST API Service** (`app/api/`)
   - FastAPI-based REST API with comprehensive OpenAPI documentation
   - HTTP endpoints for programmatic report generation
   - Request/response validation with Pydantic models
   - Comprehensive error handling and structured logging
   - CORS support for web applications

2. **AI Processing Engine** (`app/llm/`)
   - **Vector Processing**: `vectorize_os.py` - OpenSearch integration with hybrid search
   - **LLM Integration**: `invoke_llm.py` - AWS Bedrock Claude 3.7 Sonnet integration
   - **Agents**: `agents.py` - Advanced conversational AI with memory (future use)

3. **Utilities & Configuration** (`app/utils/`)
   - **Prompt Engineering**: Custom templates for report generation
   - **Configuration Management**: Environment-based configuration
   - **Logging**: Structured logging with file and console output
   - **S3 Integration**: File storage and management utilities

4. **Database Connectivity** (`db_conn/`)
   - SQL Server integration for structured AICCRA data retrieval
   - Data loading and preprocessing utilities

---

## 🛠️ Technology Stack

- **REST API**: FastAPI, Pydantic
- **AI/ML**: AWS Bedrock (Claude 3.7 Sonnet)
- **Vector Database**: Amazon OpenSearch Service
- **Traditional Database**: SQL Server (via `pyodbc`)
- **Cloud Services**: AWS S3, AWS Bedrock Knowledge Base, AWS IAM
- **Data Processing**: Pandas, NumPy
- **Authentication**: AWS4Auth, boto3
- **Development**: Python 3.13+

---

## 📋 Prerequisites

- **Python 3.13+** (recommended)
- **AWS Account** with Bedrock access and appropriate IAM permissions
- **SQL Server** database or connection to AICCRA Lakehouse
- **Amazon OpenSearch Service** instance
- **Environment Configuration**: `.env` file with required credentials

---

## 🚀 Installation

### 1. Set up virtual environment
```bash
cd ar-generator-service
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Create a `.env` file in the service root directory with the following variables:

```bash
# AWS Bedrock Configuration
AWS_ACCESS_KEY_ID_BR=your_aws_access_key
AWS_SECRET_ACCESS_KEY_BR=your_aws_secret_key
AWS_REGION=us-east-1

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
BUCKET_NAME=bucket_name

# OpenSearch Configuration
OPENSEARCH_HOST=your_opensearch_host
OPENSEARCH_INDEX_NAME=index_name
AWS_ACCESS_KEY_ID_OS=your_opensearch_access_key
AWS_SECRET_ACCESS_KEY_OS=your_opensearch_secret_key

# SqlServer Configuration
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret_key
SERVER=your_server_url
DATABASE=lakehouse_name
```

---

## 🎯 Usage

### 1. Start the API Server

```bash
python3 api_server.py
```

The server will start on `http://localhost:8000` by default.

### 2. Access API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

### 3. Test the API

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"indicator": "IPI 1.1", "year": 2025, "insert_data": "False"}'
```

---

## API Endpoints

### Generate Report

**POST** `/api/generate`

Generate an AI-powered AICCRA report for a specific indicator and year.

**Request Body:**
```json
{
  "indicator": "IPI 1.1",
  "year": 2025,
  "insert_data": "False"
}
```

**Parameters:**
- `indicator` (string, required): Indicator name (e.g., "IPI 1.1", "PDO Indicator 1")
- `year` (integer, required): Year for report generation
- `insert_data` (bool, optional): Whether to insert fresh data into OpenSearch

**Response (200 OK):**
```json
{
  "indicator": "IPI 1.1",
  "year": 2025,
  "content": "By mid-year 2025, AICCRA had already achieved...",
  "status": "success"
}
```

**Error Response (400/500):**
```json
{
  "error": "Error message",
  "status": "error",
  "details": "Additional error details"
}
```

### Health Check

**GET** `/health`

Check the health status of the API service.

**Response:**
```json
{
  "status": "healthy",
  "service": "AICCRA Report Generator API",
  "version": "1.0.0"
}
```

### API information

**GET** `/`

Root endpoint providing API information.

---

## Server Configuration

The API server can be configured with command-line arguments:

```bash
python3 api_server.py --help
```

Options:
- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to bind to (default: 8000)
- `--reload`: Enable auto-reload for development
- `--log-level`: Set log level (debug, info, warning, error, critical)

---

## Examples

### Python Example

```python
import requests

# Make API request
response = requests.post(
    "http://localhost:8000/api/generate",
    json={"indicator": "IPI 1.1", "year": 2025, "insert_data": "False"}
)

if response.status_code == 200:
    data = response.json()
    print(f"Report for {data['indicator']} ({data['year']}):")
    print(data['content'])
else:
    print(f"Error: {response.json()}")
```

### JavaScript Example

```javascript
fetch('http://localhost:8000/api/generate', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        indicator: 'IPI 1.1',
        year: 2025,
        insert_data: 'False'
    })
})
.then(response => response.json())
.then(data => {
    if (data.status === 'success') {
        console.log(`Report: ${data.content}`);
    } else {
        console.error(`Error: ${data.error}`);
    }
});
```

---

## 📊 Supported Indicators

### Intermediate Performance Indicators (IPI)
- **IPI 1.1**: Climate information services
- **IPI 1.2**: Weather/climate data access
- **IPI 1.3**: Early warning systems
- **IPI 1.4**: Climate risk assessments
- **IPI 2.1**: Agricultural technologies
- **IPI 2.2**: Farming practices adoption
- **IPI 2.3**: Productivity improvements
- **IPI 3.1**: Institutional capacity
- **IPI 3.2**: Policy development
- **IPI 3.3**: Knowledge sharing
- **IPI 3.4**: Partnership building

### Project Development Objective (PDO) Indicators
- **PDO Indicator 1-5**: Various project outcome metrics

---

## 🗂️ Project Structure

```
ar-generator-service/
├── main.py                        # CLI entry point
├── api_server.py                  # REST API server entry point
├── requirements.txt               # Project dependencies
├── .env.example                   # Environment variables template
├── .gitignore                     
├── *.jsonl                        # Training/reference data files
├── app/
│   ├── api/                       # REST API modules
│   │   ├── __init__.py            # API package initialization
│   │   ├── main.py                # FastAPI application
│   │   ├── models.py              # Pydantic request/response models
│   │   └── routes.py              # API endpoint routes
│   ├── llm/                       # LLM processing modules
│   │   ├── vectorize_os.py        # OpenSearch vector operations
│   │   └── invoke_llm.py          # AWS Bedrock integration
│   └── utils/                     # Utility modules
│       ├── config/                # Configuration management
│       ├── logger/                # Logging utilities
│       ├── prompts/               # Prompt templates
│       └── s3/                    # S3 integration
├── data/logs/                     # Application logs
└── db_conn/                       
    └── sql_connection.py        # Lakehouse connection

```

---

## Error Handling

The API provides comprehensive error handling with structured responses:

### HTTP Status Codes
- **200**: Success - Report generated successfully
- **400**: Bad Request - Invalid parameters (e.g., unsupported indicator)
- **403**: Forbidden - Authentication/authorization issues
- **422**: Unprocessable Entity - Request validation errors
- **500**: Internal Server Error - Service or infrastructure issues

### Error Response Format
```json
{
  "error": "Brief error description",
  "status": "error",
  "details": "Detailed error information",
  "error_code": "MACHINE_READABLE_CODE",
  "support": "aiccra-support@cgiar.org"
}
```

---

## 🔧 Development

### Key Development Components

1. **Report Generation Pipeline** (`app/llm/vectorize_os.py`):
   - Processes AICCRA data from SQL Server
   - Creates vector embeddings using AWS Bedrock
   - Performs hybrid search in OpenSearch
   - Generates reports using Claude 3.7 Sonnet

2. **API Layer** (`app/api/`):
   - FastAPI implementation with automatic OpenAPI documentation
   - Pydantic models for type safety and validation
   - Comprehensive error handling and logging

3. **Configuration Management** (`app/utils/config/`):
   - Environment-based configuration
   - Separate configs for different services (AWS, databases, etc.)

### Customizing Prompts

Edit the prompt template in `app/utils/prompts/`:
- `report_prompt.py`: Report generation template

---

## 📝 Logging

The service provides comprehensive logging:

- **Log Location**: `data/logs/app.log`
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Format**: Timestamp, level, module, message
- **Rotation**: Automatic log rotation to prevent large files

**Log Categories:**
- Application startup and configuration
- Database connections and queries  
- AWS service interactions (Bedrock, OpenSearch, S3)
- API request/response cycles
- Error handling and debugging information

---

## 🔒 Security

- AWS credentials are managed through environment variables
- Database connections use secure authentication
- API keys are never logged or exposed
- Follow AWS IAM best practices for service permissions

---

## 🐛 Troubleshooting

### Common Issues

1. **AWS Bedrock Access Denied**
   - Verify AWS credentials and region
   - Ensure Bedrock service is enabled in your AWS account
   - Check IAM permissions for Bedrock and Knowledge Base access

2. **Database Connection Errors**
   - Verify Lakehouse credentials and host accessibility
   - Check network connectivity and firewall settings
   - Ensure database exists and user has appropriate permissions

3. **Vector Database Issues**
   - Confirm OpenSearch endpoints and credentials
   - Verify index exists and is properly configured
   - Check vector dimensions and embedding model compatibility

---

## 📈 Performance Optimization

- **Caching**: Implement caching for frequent queries
- **Batch Processing**: Process multiple indicators in batches
- **Connection Pooling**: Use database connection pooling
- **Vector Index Optimization**: Tune vector search parameters

---

## 🤝 Contributing

We welcome contributions to improve the AICCRA Report Generator Service!

### Development Setup
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/enhancement-name`)
3. Set up development environment
4. Make your changes following the existing code style
5. Test your changes thoroughly
6. Update documentation as needed
7. Commit changes (`git commit -m 'Add enhancement description'`)
8. Push to your branch (`git push origin feature/enhancement-name`)
9. Create a Pull Request

### Contribution Guidelines
- Follow Python PEP 8 style guidelines
- Add appropriate error handling and logging
- Update documentation for new features
- Include examples for new API endpoints
- Test with multiple indicators and years

---

## 🔄 Version History

- **v1.0.0**: Production-ready REST API service
  - FastAPI-based REST API with OpenAPI documentation
  - AWS Bedrock Claude 3.7 Sonnet integration
  - OpenSearch vector database support
  - Comprehensive error handling and logging
  - Support for all IPI and PDO indicators (2021-2025)

---