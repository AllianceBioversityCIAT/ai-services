# AICCRA Annual Report Generator Service

AI-powered service for generating AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa) mid-year and annual reports. Combines structured data from MySQL (or local CSV), semantic retrieval via **Amazon S3 Vectors**, and **AWS Bedrock** (Titan embeddings + Claude) to produce data-driven narratives.

---

## Features

- **Automated report generation** for IPI and PDO indicators
- **Web UI** at `/web/` for interactive report generation and exports
- **Semantic retrieval** with Amazon S3 Vectors (replaces OpenSearch in production pipelines)
- **Hybrid retrieval**: vector search for semantic context + SQL/CSV for filter-only queries (DOI, questions, challenges)
- **Multi-report types**: mid-year, annual, summary tables, challenges & lessons learned
- **Data refresh** via `insert_data=true` (full index rebuild, same behavior as the former OpenSearch flow)
- **Local development** on Mac using CSV fixtures (`USE_CSV_DATA=true`) without MySQL or SQL Server

---

## Quick Start

### Web UI

```bash
python dev_server.py --reload
# Open http://localhost:8000/web/
```

### API docs

```bash
# Interactive docs
open http://localhost:8000/docs
```

---

## Architecture

```text
MySQL / CSV  ──►  load_data()  ──►  Bedrock Titan (embeddings)
                        │                    │
                        │                    ▼
                        │            S3 Vectors (PutVectors / QueryVectors)
                        │
                        └──►  SQL retrieval (DOI, questions, challenges)
                                      │
                                      ▼
                              Post-filters (Python business rules)
                                      │
                                      ▼
                              Bedrock Claude (report generation)
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
| Data layer | `db_conn/mysql_connection.py` | MySQL or CSV loading |
| Knowledge Base (optional) | `app/llm/knowledge_base.py` | Bedrock KB integration (separate path) |

### Legacy / alternate backends (not used by default)

| Path | Description |
|---|---|
| `app/llm/opensearch/` | Original OpenSearch pipelines (`vectorize_os.py`, `vectorize_os_annual.py`) kept for reference or rollback |
| `app/llm/supabase/` | Supabase vector pipeline (`vectorize_db.py`) kept for reference |

Production pipelines import **`vectorize.py`** and **`vectorize_annual.py`**, not the legacy modules.

---

## Technology Stack

- **API**: FastAPI, Uvicorn, Mangum (Lambda)
- **AI**: AWS Bedrock — Titan Text Embeddings v2 (1024d), Claude Sonnet
- **Vector database**: Amazon S3 Vectors (`boto3` client `s3vectors`)
- **Structured data**: MySQL (SQLAlchemy) or local CSV for development
- **Object storage**: AWS S3 (report/chatbot file exports)
- **Frontend**: HTML/CSS/JavaScript (`web/`)
- **Package management**: `uv` + `pyproject.toml`; Lambda Docker build uses `requirements.txt`

---

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended for local dev)
- AWS account with:
  - Bedrock access (embeddings + Claude)
  - S3 Vectors vector bucket + index in `us-east-1` (or your target region)
  - IAM permissions for `s3vectors:*` on the Lambda role / your user
- MySQL database with AICCRA views (production), **or** local CSV files (development)

---

## Installation

```bash
cd ar-generator-service
uv venv
source .venv/bin/activate
uv pip install -r pyproject.toml
```

For Lambda-compatible installs (Docker):

```bash
pip install -r requirements.txt
```

---

## Configuration

Copy `.env.example` to `.env` and fill in values.

### Required for S3 Vectors pipelines

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID_BR=...
AWS_SECRET_ACCESS_KEY_BR=...

S3_VECTORS_BUCKET_NAME=ar-generator-vectors
S3_VECTORS_INDEX_NAME=aiccra-chunks
```

S3 Vectors uses the **default AWS credential chain** for the `s3vectors` client (typically `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` from the environment or Lambda execution role).

### Structured data (production)

```bash
MYSQL_DATABASE_URL=mysql+mysqlconnector://user:pass@host:3306/dbname
```

Optional SQL Server / Fabric vars remain in config for other integrations:

```bash
SERVER=...
DATABASE=...
CLIENT_ID=...
CLIENT_SECRET=...
```

### S3 file exports

```bash
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
BUCKET_NAME=...
```

### Local development with CSV (Mac / no MySQL)

```bash
USE_CSV_DATA=true
# Optional: directory containing vw_ai_*_ar.csv (default: app/)
# CSV_DATA_DIR=/path/to/ar-generator-service/app
```

Place CSV fixtures in `app/` (default lookup path):

- `vw_ai_project_contribution_ar.csv`
- `vw_ai_questions_ar.csv`
- `vw_ai_deliverables_ar.csv`
- `vw_ai_oicrs_ar.csv`
- `vw_ai_innovations_ar.csv`
- `vw_ai_challenges_ar.csv`

These files are pre-processed exports (include `table_type`). When `USE_CSV_DATA=true`, no MySQL connection is attempted.

### Legacy OpenSearch (reference only)

Only needed if running code under `app/llm/opensearch/`:

```bash
OPENSEARCH_HOST=...
OPENSEARCH_INDEX_NAME=...
AWS_ACCESS_KEY_ID_OS=...
AWS_SECRET_ACCESS_KEY_OS=...
```

### Legacy Supabase (reference only)

Only needed if running `app/llm/supabase/vectorize_db.py`:

```bash
SUPABASE_URL=...
COLLECTION_NAME=...
```

---

## Usage

### Start the server (local)

```bash
python dev_server.py --reload
# Options: --host, --port, --reload, --log-level
```

### Deploy (Lambda)

Production uses `main.py` as the Mangum handler (`handler = Mangum(app)`), not a separate `api_server.py`.

### Data refresh (`insert_data=true`)

When `insert_data` is `true`, the service performs a **full rebuild** of the S3 Vectors index (same pattern as the old OpenSearch flow):

1. Delete index `S3_VECTORS_INDEX_NAME` (if exists)
2. Create index (1024 dims, cosine, non-filterable metadata key `chunk_json`)
3. Re-ingest all tables from MySQL/CSV with fresh embeddings

Mid-year ingests 5 tables; annual ingests 6 (includes `vw_ai_challenges`).

**Warning:** Lambda timeout is 15 minutes max. Full rebuilds may require a dedicated job if they exceed that window.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/web/` | Web UI |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/health` | Health check |
| `POST` | `/api/generate` | Mid-year report |
| `POST` | `/api/generate-annual` | Annual report |
| `POST` | `/api/generate-annual-tables` | Summary tables by indicator group |
| `POST` | `/api/generate-challenges` | Challenges & lessons learned |

### Example: mid-year report

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"indicator": "IPI 1.3", "year": 2025, "insert_data": false}'
```

### Example: rebuild vectors + report

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"indicator": "IPI 1.3", "year": 2025, "insert_data": true}'
```

### Request body

```json
{
  "indicator": "IPI 1.1",
  "year": 2025,
  "insert_data": false
}
```

- `insert_data=false` — query existing S3 Vectors index (fast)
- `insert_data=true` — delete/recreate index and reload all vectors (slow)

---

## Project Structure

```text
ar-generator-service/
├── main.py                    # Lambda handler (Mangum)
├── dev_server.py              # Local development server (uvicorn)
├── main.py                    # CLI entry point
├── pyproject.toml             # Local dependencies (uv)
├── requirements.txt           # Lambda Docker dependencies
├── .env.example
├── tests/
│   ├── test_retrieval.py
│   └── test_vector_store_schemas.py
├── app/
│   ├── api/                   # FastAPI routes and models
│   ├── llm/
│   │   ├── vectorize.py       # Mid-year pipeline (S3 Vectors) ← active
│   │   ├── vectorize_annual.py# Annual pipeline (S3 Vectors) ← active
│   │   ├── invoke_llm.py      # Bedrock embeddings + Claude
│   │   ├── knowledge_base.py  # Bedrock KB (optional)
│   │   ├── opensearch/        # Legacy OpenSearch pipelines (backup)
│   │   └── supabase/          # Legacy Supabase pipeline (backup)
│   ├── s3_vectors/          # S3 Vectors client, ingestion, schemas
│   ├── retrieval/             # Semantic search, SQL retrieval, filters
│   ├── utils/                 # Config, prompts, S3, jobs, logging
│   └── vw_ai_*_ar.csv         # Local CSV fixtures (dev)
├── db_conn/
│   └── mysql_connection.py    # load_data() — MySQL or CSV
├── web/                       # Web UI
├── lakehouse_integration/     # Fabric / lakehouse utilities
└── test/streamlit/            # Streamlit test UI
```

---

## Retrieval design (S3 Vectors migration)

| Query type | Engine | Notes |
|---|---|---|
| Semantic k-NN + indicator/year/table filters | S3 Vectors `QueryVectors` | Replaces OpenSearch k-NN |
| DOI lookup (mid-year) | MySQL / CSV via `sql_retrieval` | Filter-only, not vector search |
| Questions (annual) | MySQL / CSV | Filter-only |
| Challenges | MySQL / CSV | Filter-only |
| Business rules (Shared, Cancelled, AWPB, etc.) | Python `post_filters.py` | Unchanged from OpenSearch era |

---

## AWS setup (S3 Vectors)

Before first run in AWS:

1. Create a **vector bucket** in your region
2. Configure Lambda env vars: `S3_VECTORS_BUCKET_NAME`, `S3_VECTORS_INDEX_NAME`
3. Attach IAM policy with `s3vectors:CreateIndex`, `DeleteIndex`, `PutVectors`, `QueryVectors`, `GetVectors`, etc.
4. Run once with `insert_data=true` to populate the index

The application creates the **index** automatically on rebuild; it does **not** create the vector bucket.

---

## Logging

Logs are written to `data/logs/app.log` (API calls, ingestion, retrieval, errors).

---

## Troubleshooting

| Issue | Check |
|---|---|
| `S3_VECTORS_BUCKET_NAME environment variable is required` | Set S3 Vectors env vars in `.env` or Lambda |
| `AccessDenied` on `s3vectors:*` | IAM policy on user/role |
| `Unknown service: s3vectors` | Upgrade `boto3` (≥ 1.43 recommended) and AWS CLI |
| Empty or poor reports with `insert_data=false` | Index empty — run `insert_data=true` first |
| MySQL errors on Mac | Use `USE_CSV_DATA=true` and CSV files in `app/` |
| `CSV file not found` | Set `CSV_DATA_DIR` or copy `vw_ai_*_ar.csv` into default `app/` |
| Lambda timeout on rebuild | Increase timeout to 15 min or run ingest as a separate job |

---

## Security

- Store credentials in `.env` locally; use Lambda environment variables and IAM roles in AWS
- Never commit `.env` or CSV exports with sensitive data
- Apply least-privilege IAM for `s3vectors`, Bedrock, and S3

---

## Version History

- **Current**: S3 Vectors migration — `vectorize.py` / `vectorize_annual.py`, `app/s3_vectors/`, `app/retrieval/`
- **Legacy**: OpenSearch pipelines preserved under `app/llm/opensearch/`
- **Legacy**: Supabase pipeline preserved under `app/llm/supabase/`
