# Text Mining Microservice

This project is a microservice for intelligent document processing using LLMs (Large Language Models). It extracts structured information from documents using techniques like vector search, RAG, and prompt engineering — all powered by AWS Bedrock and other AI services.

---

## 🚀 Features

- ✅ Document ingestion from S3
- 🔍 Semantic chunking + vector embedding with LanceDB
- 🤖 Answer generation using LLM (Claude 3 Sonnet via Bedrock)
- 🔒 Auth via CLARISA credentials
- 📦 Async processing via RabbitMQ or sync via MCP
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
# RabbitMQ
RABBITMQ_HOST=...
RABBITMQ_PORT=5671
RABBITMQ_USERNAME=...
RABBITMQ_PASSWORD=...
RABBITMQ_QUEUE=...

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
python app/test/test_endpoint.py
```

You can also add unit tests using `pytest`.

---

## 📂 Project Structure

```
└── 📁text-mining-service
    └── 📁app
        └── .DS_Store
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
    └── .DS_Store
    └── .env
    └── .gitignore
    └── .python-version
    └── main.py
    └── pyproject.toml
    └── README.md
    └── uv.lock
```
