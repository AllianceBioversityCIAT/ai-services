# AICCRA Annual Report Generator Service

AI-powered service for generating AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa) mid-year and annual reports. In production, the service runs on **AWS Lambda**, reads structured data from **SQL Server (AICCRA Lakehouse)**, retrieves context with **Amazon S3 Vectors**, and generates narratives with **AWS Bedrock** (Titan embeddings + Claude Sonnet 4.5).

For deeper design notes, see [`docs/TECHNICAL_DOCUMENTATION.md`](docs/TECHNICAL_DOCUMENTATION.md), [`docs/HIGH_LEVEL_DESIGN.md`](docs/HIGH_LEVEL_DESIGN.md), and [`docs/PRODUCT_OVERVIEW.md`](docs/PRODUCT_OVERVIEW.md).

---

## Features

- **Automated report generation** for IPI and PDO indicators (mid-year and annual)
- **Web UI** at `/web` for interactive report generation and exports
- **Semantic retrieval** with Amazon S3 Vectors (production vector backend)
- **Hybrid retrieval**: vector search for semantic context + SQL Server for filter-only queries (DOI, questions, challenges)
- **Multi-report types**: mid-year progress, annual reports, summary tables, challenges & lessons learned
- **Data refresh** via `insert_data=true` (full S3 Vectors index rebuild)
- **Scheduled jobs** via EventBridge (`update_ar_data`, `update_chatbot_data`, `sync_knowledge_base`)
- **S3 exports** of processed datasets for reports and chatbot knowledge base
- **Slack notifications** for scheduled job outcomes (optional)

---

## Quick Start (local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in credentials
python dev_server.py --reload
```

| Resource | URL |
|---|---|
| Web UI | http://localhost:8000/web |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health check | http://localhost:8000/health |

---

## Supported indicators

**Intermediate Performance Indicators (IPI)**

- IPI 1.1 – IPI 1.4: Climate information and early warning systems
- IPI 2.1 – IPI 2.3: Agricultural technologies and practices
- IPI 3.1 – IPI 3.4: Institutional capacity and partnerships

**Project Development Objective (PDO)**

- PDO Indicator 1 – PDO Indicator 5: Project outcome and impact metrics

Supported years: **2021–2026**

---

## Production overview

| Layer | Technology |
|---|---|
| Runtime | AWS Lambda (Python 3.13, container image) |
| API | FastAPI + Mangum (`api_server.handler`) |
| Structured data | SQL Server via ODBC + Azure AD Service Principal |
| Vector search | Amazon S3 Vectors (`boto3` client `s3vectors`) |
| LLM | AWS Bedrock — Titan Text Embeddings v2 (1024d), Claude Sonnet 4.5 |
| File exports | Amazon S3 (`BUCKET_NAME`) |
| Scheduling | AWS EventBridge Scheduler → Lambda job events |
| Notifications | Slack webhook (optional) |

### Architecture

```text
SQL Server (Lakehouse)
        │
        ▼
  load_data() / load_full_data()
        │
        ├──► Bedrock Titan (embeddings)
        │           │
        │           ▼
        │    S3 Vectors (PutVectors / QueryVectors)
        │
        └──► SQL retrieval (DOI, questions, challenges)
                      │
                      ▼
              Post-filters (Python business rules)
                      │
                      ▼
              Bedrock Claude (report generation)
                      │
                      ▼
              API response / S3 exports
```

### Main components

| Component | Path | Role |
|---|---|---|
| REST API | `app/api/` | FastAPI routes, validation, web static files |
| Mid-year pipeline | `app/llm/vectorize.py` | Ingest + mid-year report generation |
| Annual pipeline | `app/llm/vectorize_annual.py` | Annual reports, tables, challenges |
| Vector store | `app/s3_vectors/` | S3 Vectors client, ingestion, schemas |
| Retrieval | `app/retrieval/` | Semantic search, SQL retrieval, post-filters |
| LLM | `app/llm/invoke_llm.py` | Bedrock embeddings and Claude invocation |
| Data layer | `db_conn/sql_connection.py` | `load_data()` / `load_full_data()` from SQL Server |
| Scheduled jobs | `app/utils/jobs/scheduled_jobs.py` | EventBridge job handlers |
| Lambda handler | `api_server.py` | HTTP (Mangum) + EventBridge job routing |

---

## Technology stack

- **API**: FastAPI, Uvicorn (local), Mangum (Lambda)
- **AI**: AWS Bedrock — Titan Text Embeddings v2 (1024d), Claude Sonnet 4.5
- **Vector database**: Amazon S3 Vectors (`boto3` client `s3vectors`)
- **Structured data**: SQL Server (pyodbc, ODBC Driver 18, Azure AD Service Principal)
- **Object storage**: AWS S3 (report/chatbot file exports)
- **Scheduling**: AWS EventBridge Scheduler
- **Frontend**: HTML/CSS/JavaScript (`web/`)
- **Dependencies**: `requirements.txt` (Lambda Docker build)

---

## Prerequisites

### Production (AWS Lambda)

- AWS account with:
  - **Bedrock** access (Titan embeddings + Claude Sonnet 4.5)
  - **S3 Vectors** vector bucket + index in target region (e.g. `us-east-1`)
  - **S3** bucket for file exports (`BUCKET_NAME`)
  - **Lambda** execution role with `s3vectors:*`, Bedrock invoke, and S3 write permissions
  - **EventBridge Scheduler** (optional, for automated data refresh)
- SQL Server access to AICCRA Lakehouse via **Azure AD Service Principal**
- Microsoft **ODBC Driver 18 for SQL Server** (included in the Lambda Docker image)
- Python **3.13** (Lambda runtime)

### Local development

- Python 3.13+
- ODBC Driver 18 for SQL Server (macOS/Windows) if connecting to Lakehouse directly
- Valid `.env` with the same variables as Lambda (see [Configuration](#configuration))
- Optional: pre-exported CSV fixtures + `USE_CSV_DATA=true` to skip SQL Server locally

---

## Installation

### Local

```bash
cd ar-generator-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Production (Lambda container)

```bash
docker build -t ar-generator-service .
# Push to ECR and deploy to Lambda with handler: api_server.handler
```

The Dockerfile installs ODBC Driver 18 and copies `app/`, `db_conn/`, `web/`, and `api_server.py`.

---

## Configuration

Copy `.env.example` to `.env` for local runs. In production, set the same variables as **Lambda environment variables**.

### AWS Bedrock (required)

Used explicitly by `invoke_llm.py` for embeddings and report generation.

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID_BR=your_aws_access_key
AWS_SECRET_ACCESS_KEY_BR=your_aws_secret_key
```

### S3 Vectors (required)

```bash
S3_VECTORS_BUCKET_NAME=your_vector_bucket_name
S3_VECTORS_INDEX_NAME=aiccra-chunks
```

S3 Vectors uses the **default AWS credential chain** (Lambda execution role in production).

### SQL Server / AICCRA Lakehouse (required in production)

```bash
SERVER=your_server_here
DATABASE=your_database_here
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
```

Authentication uses **Azure AD Service Principal** via ODBC Driver 18.

### S3 file exports (required)

```bash
BUCKET_NAME=your_bucket_name_here
```

Upload paths:

- Reports: `aiccra/reports_generation/files/`
- Chatbot: `aiccra/chatbot/files/`

S3 uploads use the **default AWS credential chain** (Lambda execution role).

### Bedrock Knowledge Base (scheduled chatbot sync)

```bash
KNOWLEDGE_BASE_ID=your_knowledge_base_id_here
DATA_SOURCE_ID=your_data_source_id_here
```

Required only for the `sync_knowledge_base` scheduled job.

### Slack notifications (optional)

```bash
SLACK_WEBHOOK_URL=your_slack_webhook_url_here
```

### Local CSV fallback (development only)

```bash
USE_CSV_DATA=true
# Optional: directory containing vw_ai_*_ar.csv (default: service root)
# CSV_DATA_DIR=/path/to/ar-generator-service
```

CSV fixtures (when `USE_CSV_DATA=true`):

- `vw_ai_project_contribution_ar.csv`
- `vw_ai_questions_ar.csv`
- `vw_ai_deliverables_ar.csv`
- `vw_ai_oicrs_ar.csv`
- `vw_ai_innovations_ar.csv`
- `vw_ai_challenges_ar.csv`

---

## Deployment (AWS Lambda)

The Lambda handler is **`api_server.handler`**. It supports:

1. **HTTP / Function URL / API Gateway** — FastAPI via Mangum
2. **EventBridge Scheduler jobs** — direct async job execution (`{"job": "update_ar_data"}`)

`main.py` provides a minimal Mangum wrapper for alternate deployments; the Docker image uses `api_server.py`.

### Credential model

| Service | Credentials |
|---|---|
| Bedrock (embeddings + Claude) | `AWS_ACCESS_KEY_ID_BR` / `AWS_SECRET_ACCESS_KEY_BR` |
| S3 Vectors | Default AWS credential chain (Lambda execution role) |
| S3 file uploads | Default AWS credential chain (Lambda execution role) |
| SQL Server | `SERVER`, `DATABASE`, `CLIENT_ID`, `CLIENT_SECRET` |

### S3 Vectors setup (one-time)

Before the first report run:

1. Create a **vector bucket** in your target region (the app does not create the bucket).
2. Set `S3_VECTORS_BUCKET_NAME` and `S3_VECTORS_INDEX_NAME` on Lambda.
3. Attach IAM permissions: `CreateIndex`, `DeleteIndex`, `PutVectors`, `QueryVectors`, `GetVectors`, etc.
4. Trigger a full ingest once with `insert_data=true` (see [Data refresh](#data-refresh-insert_datatrue)).

The application creates and recreates the **index** automatically (1024 dimensions, cosine, non-filterable metadata key `chunk_json`).

---

## Usage

### Start the server (local)

```bash
python dev_server.py --reload
# Options: --host, --port, --reload, --log-level
```

### Deploy (Lambda)

```bash
docker build -t ar-generator-service .
# Deploy to Lambda with handler api_server.handler
# Configure environment variables (see Configuration)
# Recommended: timeout 15 min, memory 2048 MB+ for report generation
```

### Data refresh (`insert_data=true`)

When `insert_data` is `true`, the service performs a **full rebuild** of the S3 Vectors index:

1. Delete index `S3_VECTORS_INDEX_NAME` (if exists)
2. Create index (1024 dims, cosine, non-filterable metadata key `chunk_json`)
3. Re-ingest all tables from SQL Server with fresh Bedrock embeddings

| Pipeline | Tables ingested |
|---|---|
| Mid-year (`vectorize.py`) | 5 tables (deliverables, contributions, questions, oicrs, innovations) |
| Annual (`vectorize_annual.py`) | 6 tables (above + challenges) |

During ingest, processed snapshots are also uploaded to S3 under `aiccra/reports_generation/files/`.

**Warning:** Full rebuilds can take 30–60 minutes. Lambda timeout is 15 minutes max — use the `update_ar_data` scheduled job or a dedicated invocation for initial loads.

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | API metadata and endpoint list |
| `GET` | `/web` | Web UI |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc |
| `GET` | `/health` | Health check |
| `POST` | `/api/generate` | Mid-year progress report |
| `POST` | `/api/generate-annual` | Annual report |
| `POST` | `/api/generate-annual-tables` | Summary tables by indicator group |
| `POST` | `/api/generate-challenges` | Challenges & lessons learned |

### Request body (report endpoints)

```json
{
  "indicator": "IPI 1.1",
  "year": 2025,
  "insert_data": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `indicator` | string | Yes (reports) | e.g. `"IPI 1.3"`, `"PDO Indicator 1"` |
| `year` | int | Yes | 2021–2026 |
| `insert_data` | bool | No (default `false`) | `true` = rebuild S3 Vectors index before generating |

- `insert_data=false` — query existing S3 Vectors index (typical production path)
- `insert_data=true` — delete/recreate index and reload all vectors (slow; use for scheduled refresh)

Annual tables and challenges endpoints only require `year`.

### Example: mid-year report

```bash
curl -X POST https://<lambda-function-url>/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "indicator": "IPI 1.3",
    "year": 2025,
    "insert_data": false
  }'
```

**Response:**

```json
{
  "indicator": "IPI 1.3",
  "year": 2025,
  "content": "## Mid-Year Progress Report - IPI 1.3\n\nBy mid-year 2025, AICCRA had achieved...",
  "status": "success"
}
```

### Example: rebuild vectors + report

```bash
curl -X POST https://<lambda-function-url>/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "indicator": "IPI 1.3",
    "year": 2025,
    "insert_data": true
  }'
```

### Example: annual report

```bash
curl -X POST https://<lambda-function-url>/api/generate-annual \
  -H "Content-Type: application/json" \
  -d '{
    "indicator": "PDO Indicator 1",
    "year": 2024,
    "insert_data": false
  }'
```

### Example: annual indicator summary tables

```bash
curl -X POST https://<lambda-function-url>/api/generate-annual-tables \
  -H "Content-Type: application/json" \
  -d '{"year": 2025}'
```

**Response:**

```json
{
  "year": 2025,
  "tables": {
    "PDO": [
      {
        "Indicator statement": "PDO Indicator 1: ...",
        "End-year target 2025": 1200,
        "Projected targets for 2025 (Mid-year report 2025)": "",
        "Achieved in 2025": 1350,
        "Brief overviews": "Kenya: Successfully trained 450 farmers..."
      }
    ],
    "IPI 1.x": [],
    "IPI 2.x": [],
    "IPI 3.x": []
  },
  "status": "success"
}
```

### Example: challenges & lessons learned

```bash
curl -X POST https://<lambda-function-url>/api/generate-challenges \
  -H "Content-Type: application/json" \
  -d '{"year": 2024}'
```

**Response:**

```json
{
  "year": 2024,
  "content": "# Challenges and Lessons Learned Report 2024\n\n## Executive Summary\n\n...",
  "status": "success"
}
```

### Performance (approximate)

| Operation | Duration |
|---|---|
| Mid-year report (`insert_data=false`) | 10–30 seconds |
| Annual report (`insert_data=false`) | 15–45 seconds |
| Report with `insert_data=true` | 30–60 minutes (full re-ingest) |
| Annual tables | 2–5 minutes |
| Challenges report | 3–7 minutes |

### Error responses

| HTTP status | Meaning |
|---|---|
| `400` | Invalid request parameters |
| `403` | Access denied (AWS / SQL credentials) |
| `422` | Validation error in request body |
| `500` | Internal server error |

```json
{
  "error": "Invalid request parameters",
  "details": "...",
  "status": "error"
}
```

---

## Scheduled jobs (EventBridge)

EventBridge Scheduler invokes Lambda with:

```json
{"job": "update_ar_data"}
```

| Job | Purpose |
|---|---|
| `update_ar_data` | Rebuilds S3 Vectors index via annual pipeline (`insert_data=true`) |
| `update_chatbot_data` | Exports chatbot source tables to S3 via `load_full_data()` |
| `sync_knowledge_base` | Starts Bedrock Knowledge Base ingestion job |

See `app/utils/jobs/scheduled_jobs.py` for implementation details.

---

## Retrieval design (S3 Vectors)

| Query type | Engine | Notes |
|---|---|---|
| Semantic k-NN + indicator/year/table filters | S3 Vectors `QueryVectors` | Primary context retrieval |
| DOI lookup (mid-year) | SQL Server via `sql_retrieval` | Filter-only, not vector search |
| Questions (annual) | SQL Server | Filter-only |
| Challenges | SQL Server | Filter-only |
| Business rules (Shared, Cancelled, AWPB, etc.) | Python `post_filters.py` | Applied after retrieval |

---

## Project structure

```text
ar-generator-service/
├── api_server.py              # Lambda handler (HTTP + EventBridge jobs)
├── dev_server.py              # Local uvicorn entry point
├── main.py                    # Alternate Mangum handler
├── Dockerfile                 # Lambda container (Python 3.13 + ODBC 18)
├── requirements.txt           # Production dependencies
├── .env.example
├── tests/
│   ├── test_retrieval.py
│   └── test_vector_store_schemas.py
├── app/
│   ├── api/                   # FastAPI routes and models
│   ├── llm/
│   │   ├── vectorize.py       # Mid-year pipeline (S3 Vectors)
│   │   ├── vectorize_annual.py# Annual pipeline (S3 Vectors)
│   │   └── invoke_llm.py      # Bedrock embeddings + Claude
│   ├── s3_vectors/          # S3 Vectors client, ingestion, schemas
│   ├── retrieval/             # Semantic search, SQL retrieval, filters
│   └── utils/                 # Config, prompts, S3, jobs, logging, notifications
├── db_conn/
│   └── sql_connection.py      # SQL Server + optional CSV fallback
├── web/                       # Web UI
└── docs/                      # Technical and product documentation
```

---

## Logging

Logs are written to `data/logs/app.log` (API calls, ingestion, retrieval, scheduled jobs, errors).

---

## Troubleshooting

| Issue | Check |
|---|---|
| `S3_VECTORS_BUCKET_NAME environment variable is required` | Set S3 Vectors env vars on Lambda |
| `AWS_ACCESS_KEY_ID_BR environment variable is required` | Set Bedrock credentials on Lambda |
| `AccessDenied` on `s3vectors:*` | Lambda execution role IAM policy |
| `Unknown service: s3vectors` | Upgrade `boto3` (≥ 1.35; 1.43+ recommended) |
| ODBC / SQL connection errors | ODBC Driver 18 in container; verify Service Principal vars |
| Empty or poor reports with `insert_data=false` | Index empty — run `insert_data=true` or `update_ar_data` job |
| Lambda timeout on rebuild | Increase timeout to 15 min max, or run ingest as dedicated job |
| Slack notifications skipped | `SLACK_WEBHOOK_URL` not configured (non-blocking) |
| `CSV file not found` (local) | Set `CSV_DATA_DIR` or place `vw_ai_*_ar.csv` in service root |

---

## Security

- Store credentials in Lambda environment variables or AWS Secrets Manager; never commit `.env`
- Use least-privilege IAM for Bedrock, S3 Vectors, S3, and SQL Server access
- Rotate Azure AD Service Principal credentials on a regular schedule
- Restrict Function URL / API Gateway access appropriately in production
- Never commit CSV exports or logs containing sensitive project data

---

## Version history

- **Current (production)**: S3 Vectors migration — active pipelines are `vectorize.py` and `vectorize_annual.py` with `app/s3_vectors/` and `app/retrieval/`
- **Previous**: OpenSearch-based retrieval (removed from active code paths)
