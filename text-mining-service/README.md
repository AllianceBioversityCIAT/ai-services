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

## 🧪 Example Usage via MCP Tool

You can test it with a payload like:

```json
{
  "key": "my-document.pdf",
  "bucket": "my-bucket",
  "credentials": {
    "username": "your-client-id",
    "password": "your-secret"
  }
}
```

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory with the following:

```env
# AWS
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# CLARISA Auth
CLARISA_HOST=https://api.clarisa.cgiar.org
CLARISA_LOGIN=...
CLARISA_PASSWORD=...
CLARISA_MIS=MINING
CLARISA_MIS_ENV=TEST

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Microservices Configuration
MS_NAME=AI Mining Microservice
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
        └── 📁test
            └── test_producer.py
        └── 📁utils
            └── 📁clarisa
                └── clarisa_connection.py
                └── clarisa_service.py
                └── 📁dto
                    └── clarisa_connection_dto.py
            └── 📁config
                └── config_util.py
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
  -H "Content-Type: application/json" \
  -d '{
    "bucketName": "my-bucket",
    "key": "documents/my-document.pdf",
    "credentials": {
      "username": "your-client-id",
      "password": "your-secret"
    },
    "prompt": "Extract key information from this document" # Optional
  }'
```

### Python Client Example

```python
import requests
import json

url = "http://localhost:8000/process"
payload = {
    "bucketName": "my-bucket",
    "key": "documents/my-document.pdf",
    "credentials": {
        "username": "your-client-id",
        "password": "your-secret"
    },
    "prompt": "Extract key information from this document"  # Optional
}

response = requests.post(url, json=payload)
result = response.json()
print(json.dumps(result, indent=2))
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
