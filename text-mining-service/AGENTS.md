# AGENTS.md — text-mining-service

This file is a **README for coding agents**. Human-oriented docs live in [`README.md`](README.md). Follow the closest `AGENTS.md` to the files you edit; nested files override this one for that subtree. Explicit user prompts override everything.

This service is part of the CGIAR [`ai-services`](../README.md) monorepo. Work from `text-mining-service/` unless the task clearly spans other services.

---

## Project overview

LLM-powered microservice that extracts structured information from documents (PDF, DOCX, Excel, PPTX, TXT) using AWS Bedrock (Claude Sonnet), semantic chunking, and LanceDB embeddings.

**Supported products / workflows:**

| Product | Entry (HTTP) | MCP tool | LLM / prompts |
|---|---|---|---|
| STAR | `POST /star/text-mining` | `process_document` | `app/llm/mining.py` + `prompt_star.py` |
| PRMS | `POST /prms/text-mining` | `process_document_prms` | `app/llm/mining.py` + `prompt_prms.py` |
| AICCRA | `POST /aiccra/text-mining` | `process_document_aiccra` | `app/llm/aiccra_mining/` + `prompt_aiccra.py` |
| STAR Bulk CapDev | `POST /star/mining-bulk-upload/capdev` | `process_document_capdev` | `app/llm/bulk_upload/upload_capdev.py` + `bulk_upload_capdev_prompt.py` |

Related surfaces:

- **FastAPI + MCP**: `app/mcp/client.py` (HTTP) spawns `app/mcp/server.py` (stdio MCP tools).
- **Legacy static UIs** (served by FastAPI): `interface/aiccra_mining/`, `interface/bulk_upload/` → `/ui`, `/bulk-upload`, `/static/*`.
- **Next.js Bulk Upload UI**: `frontend/` (SST / OpenNext). See [`frontend/AGENTS.md`](frontend/AGENTS.md).
- **DynamoDB** status tracking for bulk upload: table `bulk_upload_records` (prod) / `bulk_upload_records_test` (non-prod). Docs under `app/utils/dynamo/docs/`.
- **Feedback / interactions**: `/feedback`, `/feedback/{interaction_id}`; interaction client in `app/utils/interactions/`.

**Request rule (STAR/PRMS/AICCRA mining):** provide either `key` (+ `bucketName`) **or** `file`, not both.

---

## Repository layout

```
text-mining-service/
├── main.py                 # Lambda entry (Mangum → FastAPI app)
├── app/
│   ├── mcp/                # FastAPI client + MCP server tools
│   ├── llm/                # Mining pipelines (STAR/PRMS, AICCRA, bulk CapDev)
│   ├── middleware/         # STAR / PRMS auth middleware
│   ├── schemas/            # Pydantic response schemas
│   ├── db/miningdb/        # LanceDB temp tables (do not commit churn)
│   └── utils/              # config, S3, CLARISA, Dynamo, prompts, Slack, cron
├── frontend/               # Next.js 15 Bulk Upload app (nested AGENTS.md)
├── interface/              # Static HTML/JS UIs mounted by FastAPI
├── tests/                  # Sample JSON fixtures (not a full pytest suite yet)
├── pyproject.toml          # Python deps (uv)
├── requirements.txt        # Used by Dockerfile / Lambda image
└── Dockerfile              # AWS Lambda Python 3.13 image
```

---

## Architecture (agent mental model)

```
Client → FastAPI (app/mcp/client.py)
       → MCP stdio client → MCP server (app/mcp/server.py)
       → Auth (STAR/PRMS middleware / CLARISA API key where required)
       → LLM pipeline (S3 → chunk → embed LanceDB → Bedrock → JSON)
       → Slack notification + optional interaction tracking
```

- Local HTTP API: `uv run python -m app.mcp.client` → `http://localhost:8000` (`/docs`, `/redoc`).
- Lambda: `main.handler` wraps the same FastAPI app via Mangum.
- Do **not** treat `uv run python main.py` as the local API server; use the client module above.

---

## Setup commands

Requires **Python 3.13+** and [`uv`](https://github.com/astral-sh/uv).

```bash
cd text-mining-service
uv venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
uv pip install -r pyproject.toml   # or: uv sync if using lockfile workflow
cp .env.example .env               # if present; otherwise create .env from README
```

Frontend (separate Node app):

```bash
cd frontend
npm install
```

Never commit `.env`, credentials, or real AWS/CLARISA secrets.

---

## Useful commands

| Command | Purpose |
|---|---|
| `uv run python -m app.mcp.client` | Start FastAPI locally on port 8000 |
| `uv run python app/mcp/server.py` | Run MCP server alone (usually spawned by the client) |
| `python app/utils/cronjob/setup_db_cleaner_cron.py install` | Install LanceDB temp cleanup cron |
| `cd frontend && npm run dev` | Next.js Bulk Upload UI (HMR) |
| `cd frontend && npm run lint` | ESLint for frontend |
| `cd frontend && npm run build` | Production Next build — **avoid during agent sessions** |

---

## Code style & conventions

### Backend (Python)

- Prefer changes in existing modules; match naming and logging style (`app/utils/logger/logger_util.py`).
- Keep product-specific logic separated: STAR/PRMS in `mining.py`, AICCRA under `llm/aiccra_mining/`, bulk CapDev under `llm/bulk_upload/`, prompts under `app/utils/prompt/`.
- Config comes from env via `app/utils/config/config_util.py` — do not hardcode secrets, bucket names for credentials, or webhook URLs.
- Auth: STAR/PRMS use middleware; some routes validate `X-API-Key` via CLARISA (`validate_with_clarisa`). Preserve auth behavior when adding endpoints.
- Excel rows are treated as chunks; do not break that path when editing vectorization or splitting.
- Prefer small, focused diffs. Update prompts carefully — they drive production extraction quality.

### Frontend / interface

- Next.js Bulk Upload: TypeScript in `frontend/components/BulkUpload/`. Follow [`frontend/AGENTS.md`](frontend/AGENTS.md).
- Legacy `interface/` assets are plain HTML/JS served as static files; keep paths compatible with `app.mount("/static", ...)`.

### Commit message style (this service)

Recent history uses Conventional Commits with scopes, e.g.:

- `✨ feat(bulk-upload): …`
- `✨ feat(text-mining): …`
- `🔧 chore(requirements): …`

Match that style when the user asks for a commit.

---

## Testing instructions

- Interactive API checks: start `uv run python -m app.mcp.client`, then use `/docs` or curl against `/star/text-mining`, `/prms/text-mining`, `/aiccra/text-mining`, `/star/mining-bulk-upload/capdev`.
- Sample payloads / fixtures live under `tests/` (`test.json`, `test1.json`, `test2.json`).
- There is no comprehensive automated pytest suite in-tree yet. When adding logic, prefer adding/running targeted tests if present; otherwise verify via `/docs` and log output in `data/logs/`.
- After import moves or API changes, ensure the MCP client still starts and OpenAPI at `/docs` reflects new routes.
- Frontend: `cd frontend && npm run lint`. Prefer `npm run dev` over `npm run build` while iterating.

---

## Security considerations

- Never commit `.env`, AWS keys, CLARISA passwords, Slack webhooks, or API keys.
- Do not log full tokens, `client_secret`, or API keys.
- Bulk CapDev and several Dynamo routes expect `X-API-Key` validation — do not remove that dependency without an explicit request.
- CORS is intentionally open in the FastAPI app; do not widen secret exposure in responses.
- LanceDB tables under `app/db/miningdb/` are temporary processing state; avoid shipping large generated DB artifacts.
- Dockerfile copies `.env` into the image in this repo — treat that as a deployment smell; never add new secrets into the image or source.

---

## Deployment & CI

- **Container / Lambda**: `Dockerfile` → `CMD ["main.handler"]`.
- **GitHub Actions** (monorepo `.github/workflows/`): pushes trigger Jenkins jobs, e.g.:
  - `jenkins-trigger-ai-text-mining-dev.yml` → branch `dev-text-mining`
  - `jenkins-trigger-ai-text-mining.yml` → branch `dev-lambda`
  - Bulk upload frontend: `jenkins-trigger-ai-bulk-upload-dev.yml` / `…-dev-prod.yml`
- Frontend deploy tooling: SST (`sst.config.ts`) + OpenNext; see nested AGENTS.md.

---

## PR / change guidelines

- Scope PRs to one concern when possible (e.g. bulk-upload vs core STAR mining).
- Touch prompts only when the task requires extraction-behavior changes; call that out in the PR summary.
- If you change REST contracts used by STAR/PRMS/AICCRA clients or the Next.js BFF routes (`frontend/app/api/*`), update callers and document the contract change.
- Do not rewrite unrelated legacy `interface/` code when working in `frontend/`, and vice versa.
- Before finishing a task that claims a fix: run the relevant local server or lint command and fix failures you introduced.

---

## Environment variables (high level)

Backend `.env` (see README for examples): AWS credentials/region, CLARISA (`CLARISA_*`, `CLARISA_VALIDATE_URL`), `CLIENT_ID` / `CLIENT_SECRET`, bucket key prefixes (`STAR_BUCKET_KEY_NAME`, `PRMS_BUCKET_KEY_NAME`, `AICCRA_BUCKET_KEY_NAME`), `MAPPING_URL`, `SLACK_WEBHOOK_URL`, `IS_PROD`, `MS_NAME`. Optional Supabase vars for `vectorize_supabase.py` / `mining_supabase.py` paths.

Frontend: `NEXT_PUBLIC_MINING_API_BASE_URL`, `NEXT_PUBLIC_STAR_API_BASE_URL`, `NEXT_PUBLIC_MANAGEMENT_API_BASE_URL`, `NEXT_PUBLIC_CLARISA_API_BASE_URL`, plus server-side `BULK_UPLOAD_API_KEY` / `MINING_API_BASE_URL` for BFF routes.

---

## Where to look first

| Task | Start here |
|---|---|
| New HTTP endpoint | `app/mcp/client.py` |
| New MCP tool / mining flow | `app/mcp/server.py` + matching module under `app/llm/` |
| Prompt / extraction shape | `app/utils/prompt/` + `app/schemas/mining_schemas.py` |
| Auth | `app/middleware/`, CLARISA helpers in `app/utils/clarisa/` |
| Bulk upload status | `app/utils/dynamo/`, Dynamo routes in `client.py` |
| Next.js Bulk Upload UX | `frontend/components/BulkUpload/` |
| Legacy UIs | `interface/` |
