# Text Mining Microservice

This project is a microservice for intelligent document processing using LLMs (Large Language Models). It extracts structured information from documents using techniques like vector search, RAG, and prompt engineering — all powered by AWS Bedrock and other AI services.

---

## 🚀 Features

- ✅ Document ingestion from S3
- 🔍 Semantic chunking + vector embedding with LanceDB
- 🤖 Answer generation using LLM (Claude 3 Sonnet via Bedrock)
- 🔒 Auth via CLARISA credentials
- 📦 Sync processing via MCP
- 📤 Slack notifications on success/failure

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

You can now test the service using a **multipart/form-data** request.  
Below is an example of the expected fields when calling the `/process` endpoint:

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

Run the producer test to push messages to MCP:

```bash
python -m pytest app/test/test_endpoint.py -v
```

You can also add unit tests using `pytest`.

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
    └── README.md
    └── uv.lock
```

---

## 🔄 How MCP Works in This Project

### Model Context Protocol (MCP)

MCP is a protocol that enables seamless integration between the service and LLM models. In this project, we use MCP to:

1. **Handle document processing requests**: The MCP server exposes the `process_document` tool that receives parameters like bucket name, document key, and authentication credentials.
2. **Authenticate users**: All requests are authenticated through the CLARISA service before processing.
3. **Process documents with LLMs**: Once authenticated, documents are retrieved from S3, processed using LLMs (Claude 3 Sonnet via Bedrock), and the results are returned.
4. **Notify stakeholders**: The service sends notifications via Slack upon successful processing or failures.

### MCP Architecture

```
Client Request → FastAPI Endpoint → MCP Client → MCP Server → LLM Processing → Response
```

The MCP server runs as a separate process and communicates with the main application through a standardized protocol.

---

## 🔌 Consuming the Text Mining Endpoint

### REST API Endpoint

The service exposes a REST API endpoint at `/process` that you can call to process documents:

```bash
curl -X POST http://localhost:8000/process \
  -F "key=my-document.pdf" \
  -F "bucketName=my-bucket" \
  -F "token=auth-token" \
  -F "file=@/path/to/file.pdf"
```

### Python Client Example

```python
import requests

url = "http://localhost:8000/process"

# Option 1: Using an S3 key instead of uploading a file
data = {
    "bucketName": "my-bucket",
    "key": "documents/my-document.pdf",
    "token": "eyJhbGciOi..."     # Replace with a valid token
}
response = requests.post(url, data=data)

# Option 2: Using a file upload
# with open("path/to/your/file.pdf", "rb") as f:
#     files = {
#         "file": f
#     }
#     data = {
#         "bucketName": "my-bucket",
#         "token": "eyJhbGciOi..."
#     }

#     response = requests.post(url, data=data, files=files)

# Handle response
if response.ok:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

### Response Format

The endpoint returns structured information extracted from the document:

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
    "page_count": 10
  }
}
```

### Error Handling

If an error occurs during processing, the endpoint returns an HTTP error status code with details:

```json
{
  "detail": "Authentication failed: Invalid credentials"
}
```

Or:

```json
{
  "detail": "Error processing document: File not found in bucket"
}
```

---
