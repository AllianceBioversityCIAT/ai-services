# Text Mining Microservice

This project is a microservice for intelligent document processing using LLMs (Large Language Models). It extracts structured information from documents using techniques like vector search, RAG, and prompt engineering — all powered by AWS Bedrock and other AI services.

The service supports multiple projects:
- **STAR**: Uses the `/star/text-mining` endpoint
- **PRMS**: Uses the `/prms/text-mining` endpoint

---

## 🚀 Features

- ✅ Document ingestion from S3
- 🔍 Semantic chunking + vector embedding with LanceDB
- 🤖 Answer generation using LLM (Claude 4.5 Sonnet via Bedrock)
- 🔒 Auth via CLARISA credentials
- 📦 Sync processing via MCP
- 📤 Slack notifications on success/failure
- 🏢 Multi-project support (STAR and PRMS)
- 📊 Excel processing with row-level chunking

---

## 🛠️ Setup Instructions

### 1. Install [uv](https://github.com/astral-sh/uv)
You can install `uv` using `curl` or `wget`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
wget -qO- https://astral.sh/uv/install.sh | sh
```

To install a specific version (e.g., v0.6.14):

```bash
curl -LsSf https://astral.sh/uv/0.6.14/install.sh | sh
```

### 2. Initialize a virtual environment

```bash
uv venv
```

### 3. Activate the virtual environment

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
uv pip install -r pyproject.toml
```

---

## ▶️ Run the Microservice

You can start the microservice using:

```bash
uv run python main.py
```

This will launch the MCP server and expose the LLM-powered tools (e.g., `process_document`) via a local MCP endpoint.

---

## 🧹 Setting Up Database Cleanup Cronjob

The service includes a database cleaning utility that removes temporary LanceDB tables to prevent excessive storage usage. You can set up a cronjob to run this cleaner automatically.

### Installing the Cronjob

```bash
python app/utils/cronjob/setup_db_cleaner_cron.py install
```

This will install a cronjob that runs daily at 7:00 PM to clean up temporary database files.


---

## 🧪 Example Usage via MCP Tool

You can now test the service using **multipart/form-data** requests for both projects.

### For STAR Project
Below is an example of the expected fields when calling the `/star/text-mining` endpoint:

| Field       | Type   | Description                     |
|-------------|--------|---------------------------------|
| `key`       | string | The name of the document        |
| `bucketName`| string | The S3 bucket where it resides  |
| `token`     | string | JWT or token for authentication |
| `file`      | file   | File to upload                  |

### For PRMS Project
Below is an example of the expected fields when calling the `/prms/text-mining` endpoint:

| Field       | Type   | Description                     |
|-------------|--------|---------------------------------|
| `key`       | string | The name of the document        |
| `bucketName`| string | The S3 bucket where it resides  |
| `token`     | string | JWT or token for authentication |
| `file`      | file   | File to upload                  |

⚠️ Important:
You must provide either *key* or *file*, but **not both**.
* If using a file upload, the document will be processed directly.
* If using a key, the document will be retrieved from S3 using the bucketName.

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory with the following:

```env
# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_ACCESS_KEY_ID_BR=...
AWS_SECRET_ACCESS_KEY_BR=...

# CLARISA Auth
CLARISA_HOST=https://api.clarisa.cgiar.org
CLARISA_LOGIN=...
CLARISA_PASSWORD=...
CLARISA_MIS=MINING
CLARISA_MIS_ENV=TEST

# API Configuration
API_USERNAME=...
API_PASSWORD=...

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Microservices Configuration
MS_NAME=AI Mining Microservice

# STAR Endpoint Configuration
STAR_ENDPOINT=...
```

---

## 🧪 Running Tests

First, start the text mining service locally:

```bash
uv run python -m app.mcp.client
```

This will launch the FastAPI server at `http://localhost:8000` with interactive documentation available at `/docs`. Then, you can test the `/star/text-mining` endpoint directly uploading files or specifying S3 keys. You will find more information in the following section.

You can also add unit tests using `pytest`.

---

## 🔌 Consuming the Text Mining Endpoints

### REST API Endpoints

The service exposes two REST API endpoints:

#### For STAR Project
```bash
curl -X POST http://localhost:8000/star/text-mining \
  -F "key=my-document.pdf" \
  -F "bucketName=my-bucket" \
  -F "token=auth-token" \
  -F "file=@/path/to/file.pdf" \
  -F "environmentUrl=test"
```

#### For PRMS Project
```bash
curl -X POST http://localhost:8000/prms/text-mining \
  -F "key=my-document.pdf" \
  -F "bucketName=my-bucket" \
  -F "token=auth-token" \
  -F "file=@/path/to/file.pdf" \
  -F "environmentUrl=test"
```

### Python Client Example

```python
import requests

# For STAR Project
star_url = "http://localhost:8000/star/text-mining"

# For PRMS Project  
prms_url = "http://localhost:8000/prms/text-mining"

# Option 1: Using an S3 key instead of uploading a file
data = {
    "bucketName": "my-bucket",
    "key": "documents/my-document.pdf",
    "token": "your-auth-token",
    "environmentUrl": "test"
}

# Process with STAR
star_response = requests.post(star_url, data=data)

# Process with PRMS
prms_response = requests.post(prms_url, data=data)

# Option 2: Using a file upload
with open("path/to/your/file.pdf", "rb") as f:
    files = {"file": f}
    data = {
        "bucketName": "my-bucket",
        "token": "your-auth-token",
        "environmentUrl": "test"
    }

    # Process with STAR
    star_response = requests.post(star_url, data=data, files=files)
    
    # Process with PRMS  
    prms_response = requests.post(prms_url, data=data, files=files)

if star_response.ok:
    result = star_response.json()
    print("STAR Result:", json.dumps(result, indent=2))

if prms_response.ok:
    result = prms_response.json()
    print("PRMS Result:", json.dumps(result, indent=2))
```

### Response Format

Both endpoints return the same structured information extracted from the document, with an additional `project` field indicating which system processed it:

```json
{
  "title": "Extracted document title",
  "summary": "Brief summary of the document content", 
  "key_points": [
    "Important point 1",
    "Important point 2"
  ],
  "entities": {
    "people": ["Person 1", "Person 2"],
    "organizations": ["Organization 1", "Organization 2"],
    "locations": ["Location 1", "Location 2"]
  },
  "metadata": {
    "processing_time": "3.5s",
    "document_type": "PDF",
    "page_count": 10,
    "project": "STAR" // or "PRMS"
  }
}
```

### Error Handling

If an error occurs during processing, both endpoints return an HTTP error status code with details:

```json
{
  "detail": "Authentication failed: Invalid credentials"
}
```

Or:

```json
{
  "detail": "Error processing document: File not found in bucket",
  "project": "PRMS"
}
```

---

## 📂 Project Structure

```
└── 📁text-mining-service
    └── 📁app
        └── 📁db
            └── 📁miningdb
        └── 📁llm
            └── mining.py
            └── vectorize.py
        └── 📁mcp
            └── client.py
            └── server.py
        └── 📁middleware
            └── auth_middleware.py
        └── 📁utils
            └── 📁clarisa
                └── clarisa_connection.py
                └── clarisa_service.py
                └── 📁dto
                    └── clarisa_connection_dto.py
            └── 📁config
                └── config_util.py
            └── 📁cronjob
                └── db_cleaner.py
                └── setup_db_cleaner_cron.py
            └── 📁logger
                └── logger_util.py
            └── 📁notification
                └── notification_service.py
            └── 📁prompt
                └── default_prompt.py
            └── 📁s3
                └── s3_util.py
    └── 📁data
        └── 📁logs
            └── app.log
    └── .env
    └── .venv
    └── .gitignore
    └── .python-version
    └── main.py
    └── pyproject.toml
    └── requirements.txt
    └── Dockerfile
    └── README.md
    └── uv.lock
```

---

## 🔄 How MCP Works in This Project

### Model Context Protocol (MCP)

MCP is a protocol that enables seamless integration between the service and LLM models. In this project, we use MCP to:

1. **Handle document processing requests**: The MCP server exposes both `process_document` (for STAR) and `process_document_prms` (for PRMS) tools that receive parameters like bucket name, document key, and authentication credentials.
2. **Authenticate users**: All requests are authenticated through the CLARISA service before processing.
3. **Process documents with LLMs**: Once authenticated, documents are retrieved from S3, processed using LLMs (Claude 4.5 Sonnet via Bedrock), and the results are returned.
4. **Notify stakeholders**: The service sends notifications via Slack upon successful processing or failures, with project-specific messaging.

### MCP Architecture

```
STAR Client Request → FastAPI /star/text-mining → MCP Client → MCP Server → process_document → LLM Processing → Response
PRMS Client Request → FastAPI /prms/text-mining → MCP Client → MCP Server → process_document_prms → LLM Processing → Response
```

The MCP server runs as a separate process and communicates with the main application through a standardized protocol, supporting both STAR and PRMS workflows.

### Excel File Processing

For Excel files (.xlsx, .xls), the service:
1. Cleans the data by removing empty rows and columns
2. Converts each row into a structured format: `column_name: value, column_name2: value2`
3. Treats each row as an individual chunk for processing
4. Maintains compatibility with other document formats (PDF, DOCX, TXT, PPTX)

---