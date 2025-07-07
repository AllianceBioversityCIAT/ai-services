# AICCRA Annual Report Generator Service

An AI-powered service for generating comprehensive annual reports for AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa). This service combines an interface with automated report generation capabilities, leveraging vector databases and Large Language Models to produce high-quality, data-driven narratives.

---

## 🌟 Features

- **📊 Automated Report Generation**: AI-generated reports for various performance indicators
- **🔍 Vector Search**: Integration with AWS Bedrock Knowledge Base and OpenSearch
- **📈 Multi-Indicator Support**: Handles both IPI (Intermediate Performance Indicators) and PDO (Project Development Objective) indicators
- **💾 Database Integration**: MySQL or SQL Server connectivity for retrieving structured data

---

## 🏗️ Architecture

The service consists of two main components:

### 1. REST API Service (`app/api/`)
- FastAPI-based REST API with OpenAPI documentation
- HTTP endpoints for programmatic access
- Request/response validation with Pydantic models
- Comprehensive error handling and logging
- CORS support for web applications

### 2. Core Processing Engine
- **Vector Database Options** (choose one):
  - `app/llm/knowledge_base.py` - AWS Bedrock Knowledge Base integration
  - `app/llm/vectorize_os.py` - OpenSearch vector processing
  - `app/llm/vectorize_db.py` - Supabase vector processing
- **Prompt Engineering**: Custom prompts for report generation
- **Database Connectivity**: MySQL or SQL Server integration for data retrieval

---

## 🛠️ Technology Stack

- **REST API**: FastAPI, Uvicorn, Pydantic
- **AI/ML**: AWS Bedrock (Claude 3 Sonnet)
- **Vector Database**: OpenSearch, Supabase
- **Traditional Database**: MySQL, SQL Server
- **Cloud Services**: AWS S3, AWS Bedrock Knowledge Base
- **Data Processing**: Pandas, NumPy
- **Authentication**: AWS4Auth
- **Package Management**: uv

---

## 📋 Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- AWS account with Bedrock access
- MySQL database or direct connection to the Lakehouse (SQL Server)
- OpenSearch or Supabase instance

---

## 🚀 Installation

### 1. Install uv package manager
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Set up virtual environment
```bash
cd ar-generator-service
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies
```bash
uv pip install -r pyproject.toml
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

# AWS Bedrock Knowledge Base
KNOWLEDGE_BASE_ID=your_knowledge_base_id

# OpenSearch Configuration
OPENSEARCH_HOST=your_opensearch_host
OPENSEARCH_INDEX_NAME=index_name
AWS_ACCESS_KEY_ID_OS=your_opensearch_access_key
AWS_SECRET_ACCESS_KEY_OS=your_opensearch_secret_key

# MySQL Configuration
MYSQL_DATABASE_URL=your_mysql_connection_url

# SqlServer Configuration
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret_key
SERVER=your_server_url
DATABASE=lakehouse_name

# Supabase Configuration (if using)
SUPABASE_URL=your_supabase_url
COLLECTION_NAME=collection_name
```

---

## 🎯 Usage

### 1. Start the API Server

```bash
cd ar-generator-service
python3 api_server.py
```

The server will start on `http://localhost:8000` by default.

### 2. Access API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

### 3. Test the API

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"indicator": "IPI 1.1", "year": 2025}'
```

---

## API Endpoints

### `POST /api/generate`

Generate an AICCRA report for the specified indicator and year.

**Request Body:**
```json
{
  "indicator": "IPI 1.1",
  "year": 2025
}
```

**Parameters:**
- `indicator` (string, required): Indicator name (e.g., "IPI 1.1", "PDO Indicator 1")
- `year` (integer, required): Year for report generation

**Response (200 OK):**
```json
{
  "indicator": "IPI 1.1",
  "year": 2025,
  "content": "Generated report content...",
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

### `GET /`

Root endpoint providing API information.

### `GET /health`

Health check endpoint.

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
    json={"indicator": "IPI 1.1", "year": 2024}
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
        year: 2024
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
- **PDO 1-5**: Various project outcome metrics

---

## 🗂️ Project Structure

```
ar-generator-service/
├── chatbot_app.py                 # Main Streamlit application
├── main.py                        # CLI entry point
├── api_server.py                  # REST API server entry point
├── pyproject.toml                 # Project dependencies
├── uv.lock                        # Dependency lock file
├── API_README.md                  # REST API documentation
├── .env.example                   # Environment variables template
├── *.jsonl                        # Training/reference data files
├── app/
│   ├── api/                       # REST API modules
│   │   ├── __init__.py            # API package initialization
│   │   ├── main.py                # FastAPI application
│   │   ├── models.py              # Pydantic request/response models
│   │   └── routes.py              # API endpoint routes
│   ├── llm/                       # LLM processing modules
│   │   ├── knowledge_base.py      # AWS Bedrock KB integration
│   │   ├── vectorize_db.py        # Supabase vector operations
│   │   └── vectorize_os.py        # OpenSearch vector operations
│   └── utils/                     # Utility modules
│       ├── config/                # Configuration management
│       ├── logger/                # Logging utilities
│       ├── prompts/               # Prompt templates
│       └── s3/                    # S3 integration
├── data/logs/                     # Application logs
├── db_conn/                       # Database connections
└── lakehouse_integration/         # Data warehouse integration
```

---

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request (validation errors)
- `403`: Forbidden (access denied)
- `422`: Unprocessable Entity (validation errors)
- `500`: Internal Server Error

---

## 🔧 Development

### Key Components

1. **Vector Processing** (`app/llm/`):
   - Handles embedding generation and vector search
   - Integrates with multiple vector databases
   - Supports hybrid search capabilities

2. **Prompt Engineering** (`app/utils/prompts/`):
   - Custom prompts for report generation
   - Knowledge base query optimization
   - Context-aware response generation

3. **Database Integration** (`db_conn/`):
   - MySQL or SQL Server connectivity for structured data
   - Data loading and preprocessing utilities

### Customizing Prompts

Edit the prompt template in `app/utils/prompts/`:
- `report_generation_prompt.py`: Report generation template

---

## 📝 Logging

Logs are automatically generated in `data/logs/app.log` with information about:
- Application startup and shutdown
- Database connections
- API calls to AWS services
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
   - Verify MySQL credentials and host accessibility
   - Check network connectivity and firewall settings
   - Ensure database exists and user has appropriate permissions

3. **Vector Database Issues**
   - Confirm OpenSearch/Supabase endpoints and credentials
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

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-indicator`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add new indicator support'`)
6. Push to the branch (`git push origin feature/new-indicator`)
7. Create a Pull Request

---

## 🔄 Version History

- **v0.1.0**: Initial release with basic chatbot and report generation
- Features in development: Enhanced analytics, multi-language support, advanced visualization

---