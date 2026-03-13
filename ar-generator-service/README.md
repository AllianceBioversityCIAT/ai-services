# AICCRA Annual Report Generator Service

An AI-powered serverless service for generating comprehensive annual reports for AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa). Deployed on AWS Lambda, this service combines web and API interfaces with automated report generation capabilities, leveraging vector databases and Large Language Models to produce high-quality, data-driven narratives.

---

## 🌟 Features

- **📊 AI-Powered Report Generation**: Automated reports using AWS Bedrock Claude 3.7 Sonnet
- **🔍 Vector Search Integration**: Advanced context retrieval using OpenSearch with hybrid search capabilities
- **📈 Multi-Report Type Support**: Mid-year progress, annual reports, challenges analysis, and summary tables
- **📅 Scheduled Data Refresh**: Automated weekly updates via AWS EventBridge Scheduler
- **💾 Database Integration**: SQL Server connectivity for retrieving structured AICCRA data
- **🚀 REST API**: FastAPI-based service with comprehensive OpenAPI documentation
- **☁️ Serverless Architecture**: Deployed on AWS Lambda for automatic scaling and high availability
- **⚡ High Performance**: Optimized processing with configurable data refresh options
- **📋 Structured Responses**: Pydantic models for request/response validation
- **🔒 Enterprise Security**: AWS IAM authentication and secure credential management
- **🔔 Slack Notifications**: Real-time alerts for scheduled job status

---

## 🏗️ Architecture

The service is built as a **serverless application** deployed on AWS Lambda with the following components:

### Core Components

1. **Lambda Handler** (`api_server.py`)
   - **Hybrid Lambda Handler**: Routes both HTTP requests (via Mangum) and EventBridge Scheduler events
   - **Function URL Support**: Direct HTTP access without API Gateway
   - **Event Detection**: Automatically distinguishes between HTTP and scheduled job events
   - **Mangum Integration**: ASGI adapter for serving FastAPI in Lambda environment

2. **REST API Service** (`app/api/`)
   - FastAPI-based REST API with comprehensive OpenAPI documentation
   - HTTP endpoints for programmatic report generation
   - Request/response validation with Pydantic models
   - Comprehensive error handling and structured logging
   - CORS support for web applications
   - Static file serving for web UI

3. **AI Processing Engine** (`app/llm/`)
   - **Mid-Year Reports**: `vectorize_os.py` - OpenSearch integration for interim reports
   - **Annual Reports**: `vectorize_os_annual.py` - Comprehensive year-end report generation
   - **LLM Integration**: `invoke_llm.py` - AWS Bedrock Claude 3.7 Sonnet streaming API
   - **Vector Embeddings**: Amazon Titan Text Embeddings v2 for semantic search

4. **Scheduled Jobs** (`app/utils/jobs/`)
   - **AR Data Update**: Refreshes annual report generator data
   - **Chatbot Data Update**: Updates chatbot knowledge base sources
   - **Knowledge Base Sync**: Triggers AWS Bedrock KB ingestion
   - **EventBridge Integration**: Triggered by AWS EventBridge Scheduler rules

5. **Utilities & Configuration** (`app/utils/`)
   - **Prompt Engineering** (`prompts/`): Custom templates for different report types
   - **Configuration Management** (`config/`): Environment-based configuration
   - **Logging** (`logger/`): Structured logging to CloudWatch Logs
   - **S3 Integration** (`s3/`): File storage and management utilities
   - **Notifications** (`notification/`): Slack webhook integration

6. **Database Connectivity** (`db_conn/`)
   - SQL Server integration with Active Directory Service Principal authentication
   - Dynamic view creation for data transformation
   - Data loading and preprocessing utilities
   - JSONL export for Knowledge Base ingestion

---

## 🛠️ Technology Stack

### Core Technologies
- **Runtime**: Python 3.13
- **REST API**: FastAPI, Pydantic
- **Lambda Adapter**: Mangum (ASGI to AWS Lambda handler)
- **Development Server**: Uvicorn (local development only)

### AI & Machine Learning
- **LLM**: AWS Bedrock Claude 3.7 Sonnet (streaming API)
- **Embeddings**: Amazon Titan Text Embeddings v2 (1024 dimensions)
- **Vector Database**: Amazon OpenSearch Service (k-NN with HNSW)

### Data & Storage
- **Relational Database**: SQL Server (via `pyodbc` + ODBC Driver 18)
- **Database Authentication**: Active Directory Service Principal
- **Object Storage**: AWS S3
- **Knowledge Base**: AWS Bedrock Knowledge Base

### Serverless Infrastructure
- **Compute**: AWS Lambda (Function URL enabled)
- **Scheduling**: AWS EventBridge Scheduler
- **Authentication**: AWS IAM, AWS4Auth (OpenSearch)
- **Containerization**: Docker (Lambda deployment)

### Data Processing & Utilities
- **Data Processing**: Pandas, NumPy
- **AWS SDK**: boto3
- **HTTP Client**: aiohttp (async), requests
- **ODBC**: pyodbc, Microsoft ODBC Driver 18
- **Notifications**: Slack webhooks
- **Configuration**: python-dotenv

---

## 📋 Prerequisites

### For Development
- **Python 3.13+** (recommended)
- **Virtual Environment**: Python venv or similar
- **Environment Configuration**: `.env` file with required credentials

### For Deployment
- **Docker**: For building Lambda container images
- **AWS CLI**: Configured with appropriate credentials
- **AWS Account** with access to:
  - AWS Lambda (with Function URL capability)
  - AWS Bedrock (Claude 3.7 Sonnet model access)
  - Amazon OpenSearch Service
  - AWS S3
  - AWS EventBridge Scheduler
  - AWS Bedrock Knowledge Base
  - AWS IAM (for service permissions)

### External Services
- **SQL Server**: Connection to AICCRA Lakehouse
- **Slack Workspace**: For notification webhooks (optional)

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

Create a `.env` file in the service root directory (or configure Lambda environment variables):

```bash
# AWS Bedrock Configuration
AWS_ACCESS_KEY_ID_BR=your_aws_access_key
AWS_SECRET_ACCESS_KEY_BR=your_aws_secret_key
AWS_REGION=us-east-1

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
BUCKET_NAME=your_s3_bucket_name

# OpenSearch Configuration
OPENSEARCH_HOST=your_opensearch_endpoint.region.es.amazonaws.com
OPENSEARCH_INDEX_NAME=aiccra_reports_index
AWS_ACCESS_KEY_ID_OS=your_opensearch_access_key
AWS_SECRET_ACCESS_KEY_OS=your_opensearch_secret_key

# SQL Server Configuration (Active Directory Service Principal)
CLIENT_ID=your_service_principal_client_id
CLIENT_SECRET=your_service_principal_secret
SERVER=your_sql_server.database.windows.net
DATABASE=aiccra_lakehouse

# AWS Bedrock Knowledge Base (optional)
KNOWLEDGE_BASE_ID=your_kb_id
DATA_SOURCE_ID=your_data_source_id

# Slack Notifications (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Environment Variables for Lambda

When deploying to Lambda, configure these as **Lambda environment variables** instead of using a `.env` file.

---

## 🎯 Usage

### Local Development

#### 1. Start the Development Server

```bash
python dev_server.py
```

**With custom options:**
```bash
python dev_server.py --port 8080 --reload
```

**Available options:**
- `--host`: Host to bind to (default: `0.0.0.0`)
- `--port`: Port number (default: `8000`)
- `--reload`: Enable auto-reload for development
- `--log-level`: Set log level (debug, info, warning, error, critical, trace)

The server will start on `http://localhost:8000` by default.

#### 2. Access API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Web UI**: `http://localhost:8000/web/`

#### 3. Test the API

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"indicator": "IPI 1.1", "year": 2025, "insert_data": false}'
```

### Lambda Deployment

#### 1. Build Docker Image

```bash
docker build --platform linux/amd64 -t ar-generator-service .
```

#### 2. Tag and Push to Amazon ECR

```bash
# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag ar-generator-service:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ar-generator-service:latest

# Push image
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ar-generator-service:latest
```

#### 3. Create/Update Lambda Function

```bash
aws lambda create-function \
  --function-name ar-generator-service \
  --package-type Image \
  --code ImageUri=YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ar-generator-service:latest \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --timeout 900 \
  --memory-size 3008 \
  --environment Variables="{AWS_ACCESS_KEY_ID_BR=...,AWS_SECRET_ACCESS_KEY_BR=...}"
```

#### 4. Enable Function URL

```bash
aws lambda create-function-url-config \
  --function-name ar-generator-service \
  --auth-type NONE \
  --cors AllowOrigins="*"
```

#### 5. Configure EventBridge Scheduler (Optional)

Create EventBridge Scheduler rules for scheduled jobs:

**Weekly data refresh (every Sunday at 2 AM):**
```bash
aws scheduler create-schedule \
  --name ar-data-weekly-update \
  --schedule-expression "cron(0 2 ? * SUN *)" \
  --target '{"Arn":"arn:aws:lambda:REGION:ACCOUNT:function:ar-generator-service","RoleArn":"arn:aws:iam::ACCOUNT:role/EventBridge-Lambda-Role","Input":"{\"job\":\"update_ar_data\"}"}' \
  --flexible-time-window '{"Mode":"OFF"}'
```

**Knowledge base sync (after data updates):**
```bash
aws scheduler create-schedule \
  --name kb-sync-weekly \
  --schedule-expression "cron(30 2 ? * SUN *)" \
  --target '{"Arn":"arn:aws:lambda:REGION:ACCOUNT:function:ar-generator-service","RoleArn":"arn:aws:iam::ACCOUNT:role/EventBridge-Lambda-Role","Input":"{\"job\":\"sync_knowledge_base\"}"}' \
  --flexible-time-window '{"Mode":"OFF"}'
```

---

## API Endpoints & Web UI

### Web User Interface
- **`GET /web/`** - Main web interface for generating reports (user-friendly, no coding required)
- **`GET /`** - API information and available endpoints
- **`GET /docs`** - Interactive Swagger API documentation
- **`GET /redoc`** - Alternative ReDoc API documentation
- **`GET /health`** - Service health check

### Generate Mid-Year Report

**POST** `/api/generate`

Generate a mid-year progress report focusing on interim achievements.

**Request Body:**
```json
{
  "indicator": "IPI 1.1",
  "year": 2025,
  "insert_data": false
}
```

**Parameters:**
- `indicator` (string, required): Indicator acronym (e.g., "IPI 1.1", "PDO Indicator 1")
- `year` (integer, required): Year for report (2021-2025)
- `insert_data` (boolean, optional): Refresh OpenSearch vector database (default: `false`)

**Response (200 OK):**
```json
{
  "indicator": "IPI 1.1",
  "year": 2025,
  "content": "# Mid-Year Progress Report\n\n...",
  "status": "success"
}
```

### Generate Annual Report

**POST** `/api/generate-annual`

Generate a comprehensive annual report with full year assessment.

**Request Body:**
```json
{
  "indicator": "PDO Indicator 1",
  "year": 2024,
  "insert_data": false
}
```

**Response (200 OK):**
```json
{
  "indicator": "PDO Indicator 1",
  "year": 2024,
  "content": "# Annual Report 2024\n\n...",
  "status": "success"
}
```

### Generate Summary Tables

**POST** `/api/generate-annual-tables`

Generate consolidated summary tables for all indicators.

**Request Body:**
```json
{
  "indicator": "PDO Indicator 1",
  "year": 2025,
  "insert_data": false
}
```

**Response (200 OK):**
```json
{
  "indicator": "PDO Indicator 1",
  "year": 2025,
  "content": "# Indicator Summary Tables\n\n...",
  "status": "success"
}
```

### Generate Challenges and Lessons Learned Report

**POST** `/api/generate-challenges`

Generate a cross-cluster challenges and lessons learned analysis.

**Request Body:**
```json
{
  "indicator": "PDO Indicator 1",
  "year": 2024,
  "insert_data": false
}
```

**Response (200 OK):**
```json
{
  "indicator": "PDO Indicator 1",
  "year": 2024,
  "content": "# Challenges and Lessons Learned\n\n...",
  "status": "success"
}
```

**Error Response (400/422/500):**
```json
{
  "detail": {
    "error": "Error message",
    "details": "Additional error details",
    "status": "error"
  }
}
```

### Health Check

**GET** `/health`

Check service health status.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "AICCRA Report Generator API",
  "timestamp": "2025-03-13T10:30:00Z"
}
```

### API Information

**GET** `/`

Root endpoint with API overview and available endpoints.

---

## 🔄 Scheduled Jobs

The service includes automated background jobs triggered by AWS EventBridge Scheduler:

### Available Jobs

1. **`update_ar_data`**
   - **Purpose**: Refresh annual report generator data
   - **Schedule**: Weekly (Sundays at 2:00 AM)
   - **Duration**: ~30-40 minutes
   - **Actions**: 
     - Connects to SQL Server and creates/updates views
     - Loads data into DataFrames
     - Generates vector embeddings
     - Updates OpenSearch index
     - Uploads JSONL to S3

2. **`update_chatbot_data`**
   - **Purpose**: Update chatbot knowledge base data sources
   - **Schedule**: On-demand or custom schedule
   - **Actions**:
     - Processes multiple data tables (deliverables, contributions, questions, OICRs, innovations)
     - Exports to JSONL and CSV
     - Uploads to S3

3. **`sync_knowledge_base`**
   - **Purpose**: Synchronize AWS Bedrock Knowledge Base
   - **Schedule**: Weekly (Sundays at 2:30 AM, after data update)
   - **Duration**: ~5-10 minutes (plus background AWS processing)
   - **Actions**:
     - Triggers AWS Bedrock Agent ingestion job
     - Syncs S3 data sources with Knowledge Base
     - Sends Slack notification on completion

### Job Monitoring

- **CloudWatch Logs**: All job executions logged to CloudWatch
- **Slack Notifications**: Success/failure alerts sent to configured webhook
- **Job Status**: Check Lambda execution logs for detailed status

### Manual Job Invocation

To manually trigger a job:

```bash
aws lambda invoke \
  --function-name ar-generator-service \
  --payload '{"job": "update_ar_data"}' \
  response.json
```

---

## 📁 Project Structure

```
ar-generator-service/
├── api_server.py                  # Lambda handler (Mangum + EventBridge)
├── dev_server.py                  # Local development server (Uvicorn)
├── main.py                        # Deprecated (legacy CLI entry)
├── Dockerfile                     # Lambda container image definition
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── .gitignore
├── README.md
├── app/
│   ├── api/                       # REST API layer
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI application
│   │   ├── models.py              # Pydantic request/response models
│   │   └── routes.py              # API endpoint handlers
│   ├── llm/                       # AI processing engine
│   │   ├── invoke_llm.py          # AWS Bedrock Claude integration
│   │   ├── vectorize_os.py        # Mid-year report pipeline
│   │   └── vectorize_os_annual.py # Annual report pipeline
│   └── utils/                     # Utility modules
│       ├── config/
│       │   └── config_util.py     # Environment configuration
│       ├── jobs/
│       │   └── scheduled_jobs.py  # EventBridge job handlers
│       ├── logger/
│       │   └── logger_util.py     # CloudWatch logging
│       ├── notification/
│       │   └── notification_service.py  # Slack integration
│       ├── prompts/               # LLM prompt templates
│       │   ├── annual_report_prompt.py
│       │   ├── challenges_prompt.py
│       │   ├── diss_targets_prompt.py
│       │   └── report_prompt.py
│       └── s3/                    # S3 file operations
│           ├── divide_jsonl_files.py
│           └── upload_file_to_s3.py
├── db_conn/
│   └── sql_connection.py          # SQL Server integration
├── data/
│   └── logs/                      # Application logs (local only)
├── docs/
│   ├── HIGH_LEVEL_DESIGN.md       # Architecture documentation
│   ├── PRODUCT_OVERVIEW.md
│   └── TECHNICAL_DOCUMENTATION.md
└── web/                          # Static web UI
    ├── index.html
    ├── app.js
    └── README.md
```

---

## Examples

### Python Example

```python
import requests

# Generate annual report
response = requests.post(
    "http://localhost:8000/api/generate-annual",
    json={
        "indicator": "IPI 1.1", 
        "year": 2025, 
        "insert_data": False
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Report for {data['indicator']} ({data['year']}):")
    print(data['content'])
else:
    error = response.json()
    print(f"Error: {error.get('detail', {}).get('error')}")
```

### JavaScript Example

```javascript
fetch('http://localhost:8000/api/generate-annual', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        indicator: 'IPI 1.1',
        year: 2025,
        insert_data: false
    })
})
.then(response => response.json())
.then(data => {
    if (data.status === 'success') {
        console.log('Report:', data.content);
    } else {
        console.error('Error:', data.error);
    }
})
.catch(error => console.error('Request failed:', error));
```

### cURL Example

```bash
# Generate mid-year report with data refresh
curl -X POST "http://localhost:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "indicator": "PDO Indicator 1",
    "year": 2024,
    "insert_data": true
  }'

# Generate challenges report
curl -X POST "http://localhost:8000/api/generate-challenges" \
  -H "Content-Type: application/json" \
  -d '{"indicator": "IPI 2.1", "year": 2024, "insert_data": false}'
```

---

## ⚠️ Error Handling

The API provides comprehensive error handling with structured responses:

### HTTP Status Codes
- **200 OK**: Report generated successfully
- **400 Bad Request**: Invalid parameters or unsupported indicator
- **422 Unprocessable Entity**: Request validation errors (Pydantic)
- **500 Internal Server Error**: AWS service errors, database failures, or configuration issues

### Error Response Format
```json
{
  "detail": {
    "error": "Service configuration error",
    "details": "OpenSearch service is not properly configured",
    "status": "error"
  }
}
```

### Common Error Scenarios

**Configuration Errors:**
```json
{
  "detail": {
    "error": "Service configuration error",
    "details": "AWS_ACCESS_KEY_ID_BR environment variable is required",
    "status": "error"
  }
}
```

**Validation Errors:**
```json
{
  "detail": [
    {
      "loc": ["body", "year"],
      "msg": "ensure this value is greater than or equal to 2021",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

---

## 🔧 Development

### Local Development Workflow

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd ar-generator-service
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run Development Server**
   ```bash
   python dev_server.py --reload
   ```

4. **Test Locally**
   - Visit `http://localhost:8000/docs` for API testing
   - Visit `http://localhost:8000/web/` for web UI

### Key Development Components

1. **Report Generation Pipelines** (`app/llm/`)
   - **`vectorize_os.py`**: Mid-year reports with OpenSearch vector search
   - **`vectorize_os_annual.py`**: Annual reports, challenges, and summary tables
   - **`invoke_llm.py`**: Claude 3.7 Sonnet streaming integration

2. **Scheduled Jobs** (`app/utils/jobs/scheduled_jobs.py`)
   - `execute_update_ar_data()`: AR generator data refresh
   - `execute_update_chatbot_data()`: Chatbot KB data update
   - `execute_sync_knowledge_base()`: Bedrock KB synchronization

3. **API Layer** (`app/api/`)
   - **`main.py`**: FastAPI application with CORS and static files
   - **`routes.py`**: Endpoint handlers with lazy imports
   - **`models.py`**: Pydantic validation models

4. **Database Integration** (`db_conn/sql_connection.py`)
   - Dynamic SQL view creation
   - Data extraction and transformation
   - JSONL export for Knowledge Base

### Testing

**Test API Endpoints:**
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test report generation
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"indicator": "IPI 1.1", "year": 2025, "insert_data": false}'
```

**Test Scheduled Jobs Locally:**
```python
import asyncio
from app.utils.jobs.scheduled_jobs import execute_scheduled_job

# Test a job
result = asyncio.run(execute_scheduled_job("update_ar_data"))
print(result)
```

### Customizing Prompts

Edit prompt templates in `app/utils/prompts/`:
- **`annual_report_prompt.py`**: Annual report structure
- **`report_prompt.py`**: Mid-year report structure
- **`challenges_prompt.py`**: Challenges and lessons learned
- **`diss_targets_prompt.py`**: Indicator summary tables

Each prompt function receives:
- `indicator`: Indicator acronym
- `year`: Report year
- `context`: Retrieved data from vector search
- Additional metadata (targets, achievements, etc.)

---

## 📝 Logging

### Local Development
- **Log Location**: `data/logs/app.log`
- **Console Output**: Real-time logs to stdout
- **Log Rotation**: 5MB max size, 5 backup files

### Lambda/Production
- **CloudWatch Logs**: Automatic logging to AWS CloudWatch Logs
- **Log Group**: `/aws/lambda/ar-generator-service`
- **Log Streams**: One per Lambda execution

### Log Levels
- **DEBUG**: Detailed diagnostic (column names, data shapes, query details)
- **INFO**: Operational milestones (pipeline stages, data counts, job status)
- **WARNING**: Recoverable issues (missing optional config, data quality warnings)
- **ERROR**: Failures requiring attention (AWS service errors, DB failures)
- **CRITICAL**: Severe errors (missing required config, authentication failures)

### Log Format
```
2025-03-13 10:30:45,123 - app.llm.vectorize_os - INFO - ✅ Successfully processed 1234 records
2025-03-13 10:31:12,456 - app.api.routes - ERROR - ❌ Error invoking model: timeout
```

### Log Categories

**🚀 API Requests:**
```
📥 Received request: POST /api/generate-annual
♦ Validating request parameters...
✅ Request validation successful
```

**📊 Data Processing:**
```
📂 Loading data from vw_ai_deliverables
📈 Number of records: 1,234
🧠 Generating embeddings for 1,234 texts
✅ All embeddings generated successfully
```

**🤖 AI Processing:**
```
✍️  Generating report with LLM...
🚀 Invoking the model...
✅ Report generated successfully (1,234 tokens)
```

**📦 Scheduled Jobs:**
```
📅 Received scheduled job request: update_ar_data
🚀 Starting AR data update job
✅ AR data update completed successfully
```

---

## 🔒 Security

### Credential Management
- **Environment Variables**: All credentials stored as environment variables (never in code)
- **Lambda Environment**: Encrypted environment variables in AWS Lambda
- **IAM Roles**: Use IAM roles for Lambda execution when possible
- **Secrets Manager**: Consider migrating to AWS Secrets Manager for production

### Authentication & Authorization
- **SQL Server**: Active Directory Service Principal authentication
- **AWS Services**: IAM-based authentication with access keys
- **OpenSearch**: AWS4Auth signature-based authentication
- **API Access**: Currently no authentication (consider adding API Gateway with auth)

### Best Practices
1. **Never commit credentials** to version control
2. **Rotate credentials** regularly (90 days recommended)
3. **Principle of least privilege**: Grant minimum required permissions
4. **Audit logs**: Review CloudWatch Logs for suspicious activity
5. **Network security**: Use VPC for Lambda if accessing private resources
6. **Encrypt data**: Use TLS for all network communications

### Security Hardening Checklist
- [ ] Enable AWS GuardDuty for threat detection
- [ ] Implement API Gateway with authentication
- [ ] Use AWS WAF for web application firewall
- [ ] Enable CloudTrail for API activity logging
- [ ] Use AWS Secrets Manager instead of environment variables
- [ ] Implement rate limiting on API endpoints
- [ ] Add input validation and sanitization
- [ ] Enable VPC for Lambda function

---

## 🐛 Troubleshooting

### Common Issues

#### 1. AWS Bedrock Access Denied
```
ERROR - ❌ Error invoking the model: An error occurred (AccessDeniedException)
```
**Solutions:**
- Verify `AWS_ACCESS_KEY_ID_BR` and `AWS_SECRET_ACCESS_KEY_BR` are set
- Check AWS region is `us-east-1` or region where Claude 3.7 Sonnet is available
- Ensure IAM user/role has `bedrock:InvokeModel` permission
- Verify Claude 3.7 Sonnet model access is enabled in AWS console

#### 2. SQL Server Connection Errors
```
ERROR - ❌ ODBC connection failed
```
**Solutions:**
- Verify `CLIENT_ID` and `CLIENT_SECRET` are correct
- Check `SERVER` and `DATABASE` values
- Ensure Service Principal has read access to database
- Test network connectivity: `telnet server.database.windows.net 1433`
- Verify ODBC Driver 18 is installed: `odbcinst -q -d`

#### 3. OpenSearch Connection Issues
```
ERROR - Failed to connect to OpenSearch
```
**Solutions:**
- Verify `OPENSEARCH_HOST` includes `.es.amazonaws.com`
- Check `AWS_ACCESS_KEY_ID_OS` and `AWS_SECRET_ACCESS_KEY_OS`
- Ensure IAM user has `es:ESHttpGet` and `es:ESHttpPost` permissions
- Verify index exists: Check OpenSearch dashboard
- Check security group allows inbound HTTPS (443)

#### 4. Lambda Timeout Errors
```
Task timed out after 900.00 seconds
```
**Solutions:**
- Increase Lambda timeout (max 900 seconds = 15 minutes)
- For data refresh jobs, consider asynchronous invocation
- Optimize query performance in SQL Server
- Reduce batch size for embeddings generation

#### 5. Memory Errors in Lambda
```
Runtime exited with error: signal: killed
```
**Solutions:**
- Increase Lambda memory allocation (currently 3008 MB)
- Process data in smaller chunks
- Optimize DataFrame operations
- Use generators instead of loading all data at once

#### 6. EventBridge Scheduler Not Triggering
```
Job did not execute at scheduled time
```
**Solutions:**
- Verify EventBridge rule is enabled
- Check IAM role has `lambda:InvokeFunction` permission
- Review CloudWatch Logs for rule execution
- Verify schedule expression syntax: `cron(0 2 ? * SUN *)`
- Check Lambda concurrency limits not exceeded

### Debug Mode

Enable debug logging locally:
```bash
python dev_server.py --log-level debug
```

Check CloudWatch Logs for Lambda:
```bash
aws logs tail /aws/lambda/ar-generator-service --follow
```

---

## 📈 Performance Optimization

### Current Performance
- **Mid-Year Report**: 10-30 seconds (without data refresh)
- **Annual Report**: 10-30 seconds (without data refresh)
- **Data Refresh**: 30-40 minutes (vectorization + indexing)
- **Lambda Cold Start**: 3-5 seconds (container initialization)
- **Lambda Warm**: <1 second (cached execution)

### Optimization Strategies

**1. Lambda Configuration**
- Increase memory for faster CPU allocation (current: 3008 MB)
- Use provisioned concurrency to eliminate cold starts
- Enable Lambda SnapStart for faster initialization

**2. Data Processing**
- Implement incremental vectorization (only changed records)
- Use connection pooling for SQL Server
- Batch embedding requests (current: individual requests)
- Cache frequently accessed data in ElastiCache

**3. Vector Search**
- Optimize OpenSearch index settings (shard count, replica count)
- Tune k-NN parameters (ef_construction, ef_search)
- Partition indexes by year for faster queries
- Use filtered k-NN instead of post-filtering

**4. LLM Processing**
- Cache prompts for similar requests
- Optimize prompt length (fewer tokens = faster)
- Use batch inference for multiple reports
- Consider Claude Haiku for faster, cheaper queries

**5. Monitoring**
- Set up CloudWatch Alarms for:
  - Lambda duration > 300 seconds
  - Error rate > 5%
  - Concurrent executions > 80% of limit
- Use X-Ray for distributed tracing

---

## 📊 Supported Indicators

### Intermediate Performance Indicators (IPI)

**IPI 1.x - Climate Information Services**
- **IPI 1.1**: Climate information services access
- **IPI 1.2**: Weather/climate data utilization
- **IPI 1.3**: Early warning systems implementation
- **IPI 1.4**: Climate risk assessments conducted

**IPI 2.x - Agricultural Technologies**
- **IPI 2.1**: Climate-smart agricultural technologies developed
- **IPI 2.2**: Farming practices adoption rates
- **IPI 2.3**: Productivity improvements measured

**IPI 3.x - Institutional Capacity**
- **IPI 3.1**: Institutional capacity strengthening
- **IPI 3.2**: Policy development and influence
- **IPI 3.3**: Knowledge sharing mechanisms
- **IPI 3.4**: Partnership building and collaboration

### Project Development Objective (PDO) Indicators
- **PDO Indicator 1**: Direct project beneficiaries
- **PDO Indicator 2**: Climate-smart technologies adopted
- **PDO Indicator 3**: Institutional capacity enhanced
- **PDO Indicator 4**: Policy engagement outcomes
- **PDO Indicator 5**: Knowledge products disseminated

### Supported Years
- **2021-2025**: Full data coverage for all indicators
- **Historical Data**: Available for comparative analysis

---

## 🤝 Contributing

We welcome contributions to improve the AICCRA Report Generator Service!

### Development Setup
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/enhancement-name`)
3. Set up development environment with `dev_server.py`
4. Make your changes following PEP 8 style guidelines
5. Test locally and with Lambda deployment
6. Update documentation (README, HIGH_LEVEL_DESIGN.md)
7. Commit changes with descriptive messages
8. Push to your branch and create a Pull Request

### Contribution Guidelines
- **Code Style**: Follow Python PEP 8
- **Type Hints**: Use type annotations for all functions
- **Error Handling**: Add comprehensive try-except blocks
- **Logging**: Use structured logging with emojis for readability
- **Documentation**: Update README and docstrings
- **Testing**: Test with multiple indicators and years
- **Security**: Never commit credentials or sensitive data

---

## 🔄 Version History

### v2.0.0 (Current) - Serverless Architecture
- **☁️ Lambda Deployment**: Migrated from EC2 to AWS Lambda
- **📦 EventBridge Scheduler**: Replaced cron jobs with EventBridge
- **🔔 Slack Notifications**: Real-time job status alerts
- **🔄 Scheduled Jobs**: Automated data refresh and KB sync
- **🐳 Docker Support**: Container-based Lambda deployment
- **📊 Enhanced Logging**: CloudWatch Logs integration
- **⚡ Performance**: Optimized cold start and execution time

### v1.0.0 - Initial Production Release
- **🚀 FastAPI**: RESTful API with OpenAPI documentation
- **🤖 AWS Bedrock**: Claude 3.7 Sonnet integration
- **🔍 OpenSearch**: Vector search with hybrid k-NN
- **📊 Four Report Types**: Mid-year, annual, challenges, summaries
- **📋 Pydantic Models**: Request/response validation
- **🌐 Web UI**: Browser-based interface
- **📈 IPI & PDO Support**: All indicators (2021-2025)

---

## 📞 Support

For issues, questions, or contributions:
- **Issues**: [GitHub Issues](https://github.com/your-org/ar-generator-service/issues)
- **Documentation**: See `docs/` folder for detailed architecture
- **Email**: aiccra-support@cgiar.org

---

## 📝 License

This project is proprietary software developed for CGIAR AICCRA.

---

**Built with ❤️ by the AICCRA Digital Team**
