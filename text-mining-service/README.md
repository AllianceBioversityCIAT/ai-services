# Text Mining Microservice

LLM-powered microservice for intelligent document processing. It extracts structured information from documents using semantic chunking, vector search (LanceDB), RAG-style retrieval, and prompt engineering — powered by **AWS Bedrock (Claude Sonnet 4.6)** and CGIAR auth services.

This service lives inside the CGIAR [`ai-services`](../README.md) monorepo.

For AI coding agents, see [`AGENTS.md`](AGENTS.md) (and [`frontend/AGENTS.md`](frontend/AGENTS.md) for the Next.js app).

---

## Supported products

| Product | HTTP endpoint | MCP tool | Typical use |
|---|---|---|---|
| **STAR** | `POST /star/text-mining` | `process_document` | Single-document mining for STAR results |
| **PRMS** | `POST /prms/text-mining` | `process_document_prms` | Multisource PRMS extraction (docs / text / audio; five indicators, KP excluded) |
| **AICCRA** | `POST /aiccra/text-mining` | `process_document_aiccra` | AICCRA document mining (optional custom prompt) |
| **STAR Bulk CapDev** | `POST /star/mining-bulk-upload/capdev` | `process_document_capdev` | Excel bulk extraction for Capacity Development |

Related UIs:

| UI | Location | How to open |
|---|---|---|
| AICCRA static UI | `interface/aiccra_mining/` | `GET /ui` (assets under `/static/...`) |
| Bulk Upload (legacy) | `interface/bulk_upload/` | `GET /bulk-upload` |
| Bulk Upload (Next.js) | `frontend/` | `npm run dev` in `frontend/` (SST / OpenNext in AWS) |

---

## Features

- Document ingestion from S3 or multipart file upload
- Semantic chunking + embeddings with LanceDB
- Structured extraction via Claude Sonnet on AWS Bedrock
- Multi-product prompts (STAR, PRMS, AICCRA, Bulk CapDev)
- Auth via STAR middleware + CLARISA `X-API-Key` (STAR/bulk CapDev); PRMS mining uses CLARISA `X-API-Key` only
- Sync processing over MCP (FastAPI client → MCP server tools)
- Slack notifications on success/failure
- Excel row-level chunking
- DynamoDB tracking of bulk-upload record statuses (`complete` / `failed` / STAR links)
- Feedback & interaction tracking endpoints
- Lambda deployment via Mangum (`main.handler`)

---

## Prerequisites

- Python **3.13+**
- [`uv`](https://github.com/astral-sh/uv) — recommended for **local** install and development
- AWS credentials with Bedrock, S3, and DynamoDB access as required by your environment
- Node.js 20+ (only if working on `frontend/`)

### Dependency tooling: local vs Lambda

| Context | Tooling | Dependency source |
|---|---|---|
| **Local development / testing** | [`uv`](https://github.com/astral-sh/uv) (`uv venv`, `uv pip` / `uv run`) | `pyproject.toml` (lockfile: `uv.lock`) |
| **Lambda / Docker packaging** | Standard Python venv + `pip` | `requirements.txt` (used by the `Dockerfile`) |

Keep both files in sync when adding or upgrading Python packages.

---

## Setup (backend — local with uv)

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
wget -qO- https://astral.sh/uv/install.sh | sh
```

### 2. Create and activate a virtual environment

```bash
cd text-mining-service
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
uv pip install -r pyproject.toml
```

### 4. Configure environment

Create a `.env` file in the service root (never commit secrets):

```env
# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# CLARISA
CLARISA_HOST=https://api.clarisa.cgiar.org
CLARISA_LOGIN=...
CLARISA_PASSWORD=...
CLARISA_MIS=MINING
CLARISA_MIS_ENV=TEST
CLARISA_VALIDATE_URL=...

# App / auth helpers
MS_NAME=AI Mining Microservice
CLIENT_ID=...
CLIENT_SECRET=...
IS_PROD=false

# Bucket key prefixes (S3 paths per product)
STAR_BUCKET_KEY_NAME=...
PRMS_BUCKET_KEY_NAME=...
AICCRA_BUCKET_KEY_NAME=...

# Optional integrations
MAPPING_URL=...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
AUTH_TOKEN_STAR=...

# PRMS multisource mining (optional overrides)
PRMS_EXTRACTION_MAX_WORKERS=4
PRMS_MAX_SOURCES=6
PRMS_MAX_FILE_BYTES=25000000
PRMS_MAX_PDF_PAGES=100
PRMS_MAX_TEXT_CHARS=50000
PRMS_CONTEXT_TOKEN_BUDGET=300000
PRMS_FULL_SOURCE_MAX_CHARS=50000
PRMS_RETRIEVAL_TOP_K_PER_SOURCE=8
PRMS_FINAL_VALIDATION_ENABLED=false

# Amazon Transcribe for PRMS audio_keys (optional)
PRMS_AUDIO_TRANSCRIBER=amazon_transcribe
# PRMS_MAX_AUDIO_SECONDS=600
# Leave PRMS_TRANSCRIBE_LANGUAGE_CODE empty for auto language identification
# PRMS_TRANSCRIBE_LANGUAGE_CODE=
# PRMS_TRANSCRIBE_LANGUAGE_OPTIONS=en-US,es-ES,fr-FR,pt-BR
# PRMS_TRANSCRIBE_POLL_INTERVAL_SECONDS=2
# PRMS_TRANSCRIBE_TIMEOUT_SECONDS=300

# Optional Supabase path (legacy / alternate vectorization modules)
# SUPABASE_USER=...
# SUPABASE_PASSWORD=...
# SUPABASE_HOST=...
# SUPABASE_PORT=...
# SUPABASE_DB=...
```

---

## Run locally (backend)

Start the FastAPI app (this also spawns the MCP server over stdio):

```bash
uv run python -m app.mcp.client
```

- API: [http://localhost:8000](http://localhost:8000)
- Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

> **Note:** `main.py` is the **AWS Lambda** entrypoint (`Mangum`). Prefer `uv run python -m app.mcp.client` for local development.

---

## Lambda / packaging (standard venv + `requirements.txt`)

For AWS Lambda (and the Docker image), dependencies are installed from **`requirements.txt`** with a normal Python environment — not `uv`:

```bash
cd text-mining-service
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The `Dockerfile` does the equivalent for the Lambda image:

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"
```

Runtime entrypoint: `main.handler` (Mangum wrapping the FastAPI app).

---

## Frontend (Bulk Upload — Next.js)

The modern Bulk Upload UI lives in `frontend/` (Next.js 15, React 19, SST + OpenNext).

```bash
cd frontend
npm install
npm run dev
```

Useful scripts:

| Script | Purpose |
|---|---|
| `npm run dev` | Local Next.js with HMR |
| `npm run lint` | ESLint |
| `npm run sst:dev` / `sst:deploy` | SST lifecycle |
| `npm run build:open-next` | Production OpenNext build (CI / deploy) |

Typical frontend env vars (see `frontend/sst.config.ts`):

```env
NEXT_PUBLIC_MINING_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_STAR_API_BASE_URL=...
NEXT_PUBLIC_MANAGEMENT_API_BASE_URL=...
NEXT_PUBLIC_CLARISA_API_BASE_URL=...
MINING_API_BASE_URL=http://localhost:8000
BULK_UPLOAD_API_KEY=...
```

Same-origin BFF routes under `frontend/app/api/` proxy to the mining service (e.g. `POST /api/bulk-upload` → `/star/mining-bulk-upload/capdev` with `X-API-Key`).

---

## API overview

OpenAPI at `/docs` is the source of truth. High-level surface:

### Document mining

| Method | Path | Auth notes |
|---|---|---|
| `POST` | `/star/text-mining` | STAR token + `X-API-Key` (CLARISA) |
| `POST` | `/prms/text-mining` | CLARISA `X-API-Key` only (multisource) |
| `POST` | `/aiccra/text-mining` | Optional token; supports custom `prompt` |
| `POST` | `/star/mining-bulk-upload/capdev` | STAR token + roles + `X-API-Key` (CLARISA); optional `skip_ids` |

Common multipart fields for STAR/AICCRA mining:

| Field | Type | Description |
|---|---|---|
| `bucketName` | string | S3 bucket |
| `token` | string | Project auth token (required for STAR; optional for AICCRA) |
| `environmentUrl` | string | Target environment for auth |
| `key` | string | S3 object key (**or** use `file`) |
| `file` | file | Upload to process (**or** use `key`) |
| `user_id` | string | Optional interaction tracking |

PRMS multisource fields (`POST /prms/text-mining`):

| Field | Type | Description |
|---|---|---|
| `bucketName` | string | Required when using S3 keys or uploads |
| `keys` | string[] | Document S3 keys (repeat form field) |
| `files` | file[] | Direct document uploads |
| `text` | string | Optional free text |
| `audio_keys` | string[] | Existing S3 audio keys only (no multipart audio) |
| `user_id` | string | Optional interaction tracking |

Bulk CapDev extras: `skip_ids` (comma-separated record IDs already submitted), `user_name`.

⚠️ STAR/AICCRA: provide either `key` **or** `file`, not both. PRMS accepts any non-empty combination of `keys`/`files`, free text, and `audio_keys`.

### Bulk upload status (DynamoDB)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/dynamo/bulk-upload-records/{file_name}` | Read complete / failed / links |
| `POST` | `/dynamo/bulk-upload-records` | Update one record status |
| `POST` | `/dynamo/bulk-upload-records/batch` | Atomic batch status updates |

Tables: `bulk_upload_records` when `IS_PROD=true`, otherwise `bulk_upload_records_test`. More detail in `app/utils/dynamo/docs/`.

### Other useful routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/auth/token` | Issue encoded client credentials token for UIs |
| `GET` | `/ui` | AICCRA static interface |
| `GET` | `/bulk-upload` | Legacy bulk-upload HTML UI |
| `GET` | `/aiccra/prompt` | Default AICCRA prompt |
| `GET` / `POST` | `/s3/list`, `/list-s3-objects`, `/s3/download-template` | S3 helpers for UIs |
| `POST` | `/feedback` | Submit feedback |
| `GET` | `/feedback/{interaction_id}` | Lookup feedback / interaction record |

### Example: STAR (S3 key)

```bash
curl -X POST http://localhost:8000/star/text-mining \
  -H "X-API-Key: YOUR_CLARISA_API_KEY" \
  -F "bucketName=my-bucket" \
  -F "key=star/text-mining/files/test/report.pdf" \
  -F "token=auth-token" \
  -F "environmentUrl=https://your-star-env/" \
  -F "user_id=researcher@cgiar.org"
```

### Example: STAR (file upload)

```bash
curl -X POST http://localhost:8000/star/text-mining \
  -H "X-API-Key: YOUR_CLARISA_API_KEY" \
  -F "bucketName=my-bucket" \
  -F "token=auth-token" \
  -F "environmentUrl=https://your-star-env/" \
  -F "file=@/path/to/file.pdf"
```

### Example: PRMS (multisource)

```bash
curl -X POST http://localhost:8000/prms/text-mining \
  -H "X-API-Key: YOUR_CLARISA_API_KEY" \
  -F "bucketName=my-bucket" \
  -F "keys=prms/text-mining/files/test/policy.docx" \
  -F "keys=prms/text-mining/files/test/attendance.pdf" \
  -F "text=Focus on outcomes reported during 2026" \
  -F "user_id=researcher@cgiar.org"
```

### Example: AICCRA (custom prompt)

```bash
curl -X POST http://localhost:8000/aiccra/text-mining \
  -F "bucketName=my-bucket" \
  -F "key=path/to/document.pdf" \
  -F "prompt=Extract climate adaptation strategies by sector"
```

### Example: Bulk CapDev

```bash
curl -X POST http://localhost:8000/star/mining-bulk-upload/capdev \
  -H "X-API-Key: YOUR_CLARISA_API_KEY" \
  -F "bucketName=my-bucket" \
  -F "key=star/text-mining/files/test/bulk_upload/capdev.xlsx" \
  -F "token=auth-token" \
  -F "environmentUrl=https://your-star-env/" \
  -F "skip_ids=1,2,5" \
  -F "user_id=user@cgiar.org" \
  -F "user_name=Jane Doe"
```

### Python client sketch

```python
import json
import requests

url = "http://localhost:8000/star/text-mining"
headers = {"X-API-Key": "YOUR_CLARISA_API_KEY"}
data = {
    "bucketName": "my-bucket",
    "key": "documents/my-document.pdf",
    "token": "your-auth-token",
    "environmentUrl": "https://your-star-env/",
}

response = requests.post(url, data=data, headers=headers)
print(json.dumps(response.json(), indent=2))
```

### Response shape

Successful responses return **product-specific structured JSON** produced by the LLM prompts/schemas (e.g. innovation, policy change, capacity development fields for STAR/PRMS; CapDev row arrays for bulk upload). Many flows also return or associate an `interaction_id` for analytics/feedback.

On failure, expect HTTP 4xx/5xx with a `detail` message, for example:

```json
{
  "detail": "Authentication failed: Invalid credentials"
}
```

---

## Architecture

### MCP flow

```
Client
  → FastAPI (app/mcp/client.py)
  → MCP stdio client
  → MCP server (app/mcp/server.py)
  → Auth (STAR middleware + CLARISA; PRMS CLARISA X-API-Key only)
  → LLM pipeline (S3/free text/audio → context selection → Bedrock → JSON)
  → Slack notification + optional interaction tracking
```

Per product:

```
STAR        → /star/text-mining                 → process_document
PRMS        → /prms/text-mining                 → process_document_prms (app/llm/prms_mining)
AICCRA      → /aiccra/text-mining               → process_document_aiccra
Bulk CapDev → /star/mining-bulk-upload/capdev   → process_document_capdev
```

### Excel processing

For Excel (`.xlsx`, `.xls`):

1. Empty rows/columns are cleaned
2. Each row becomes a structured chunk (`column: value, …`)
3. Rows are embedded/retrieved individually where applicable
4. Other formats (PDF, DOCX, TXT, PPTX) use recursive text splitting

---

## Project structure

```
text-mining-service/
├── main.py                      # Lambda handler (Mangum → FastAPI)
├── app/
│   ├── mcp/
│   │   ├── client.py            # FastAPI routes, S3/Dynamo helpers, UIs
│   │   └── server.py            # MCP tools
│   ├── llm/
│   │   ├── providers/           # Shared Bedrock client (all products)
│   │   ├── shared/              # vectorize, map_fields, json_parser, etc.
│   │   ├── star_mining/         # STAR pipeline
│   │   ├── prms_mining/         # PRMS multisource pipeline
│   │   ├── aiccra_mining/       # AICCRA pipeline
│   │   └── bulk_upload/         # CapDev bulk pipeline
│   ├── middleware/              # STAR auth
│   ├── schemas/                 # Pydantic mining schemas
│   ├── db/miningdb/             # Temporary LanceDB data
│   └── utils/
│       ├── clarisa/
│       ├── config/
│       ├── dynamo/              # Bulk status table + docs
│       ├── interactions/
│       ├── logger/
│       ├── notification/        # Slack
│       ├── prompt/              # STAR, PRMS (modular), AICCRA, CapDev
│       └── s3/
├── frontend/                    # Next.js Bulk Upload (SST / OpenNext)
├── interface/                   # Legacy static UIs (AICCRA + bulk upload)
├── tests/                       # Fixtures + PRMS unit/API tests
├── data/logs/                   # Runtime logs
├── Dockerfile
├── pyproject.toml               # Local deps (uv)
├── requirements.txt             # Lambda / Docker deps (pip)
├── uv.lock
├── AGENTS.md
└── README.md
```

---

## Deployment & CI

- **Docker / Lambda:** `Dockerfile` installs from `requirements.txt` with `pip` into a Python 3.13 Lambda image and runs `main.handler`. Local packaging/testing for that path should use `python -m venv` + `pip install -r requirements.txt` (see [Lambda / packaging](#lambda--packaging-standard-venv--requirementstxt)).
- **Local API work** continues to use `uv` + `pyproject.toml`.
- **GitHub Actions** (monorepo `.github/workflows/`) trigger Jenkins jobs on branch pushes, for example:
  - `dev-text-mining` → text-mining service (dev)
  - `dev-lambda` → text-mining service (Lambda job)
  - Bulk Upload frontend workflows for dev / prod
- **Frontend:** SST (`frontend/sst.config.ts`) + OpenNext; CloudFormation templates under `frontend/infrastructure/`.

---

## Testing

1. Start the API: `uv run python -m app.mcp.client`
2. Exercise endpoints via `/docs` or curl
3. Use sample fixtures under `tests/` when useful
4. Frontend: `cd frontend && npm run lint` (and manual wizard checks against a running mining API)

There is no full automated pytest suite in-tree yet; treat `/docs` and logs in `data/logs/` as the primary verification path unless you add tests for your change.

---

## Security

- Keep `.env` and API keys out of git
- Prefer `X-API-Key` for CLARISA-protected STAR routes; do not expose keys in `NEXT_PUBLIC_*` frontend variables
- Avoid logging raw tokens, client secrets, or API keys
- Treat LanceDB under `app/db/miningdb/` as ephemeral processing state
