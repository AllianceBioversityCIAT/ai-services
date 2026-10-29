# AGENTS.md — text-mining-service

This is the **service-main copy** of the coding-agent guide for `main-text-mining`. Human-oriented docs live in [`README.md`](README.md). Follow the closest `AGENTS.md` to the files you edit; nested files override this one for that subtree. Explicit user prompts override everything.

Read the [root agent guide](../AGENTS.md) for shared branch and change rules. This service is part of the CGIAR [`ai-services`](../README.md) monorepo. Work from `text-mining-service/` unless the task clearly spans other services.

Prepare changes from `dev-text-mining`, normally on a focused task branch. The maintainer handles `dev-text-mining` → `main-text-mining`; integration then continues through `staging` → `main`. After the local service-main merge and before push, compare both trees and adapt the service-main README and agent guides to its files, routes, interfaces, and environment destinations. See [branch differences](docs/BRANCH_DIFFERENCES.md); do not restore removed development-only files merely to match documentation.

---

## Project overview

LLM-powered microservice that extracts structured information from documents (PDF, DOCX, Excel, PPTX, TXT) using AWS Bedrock (Claude Sonnet), semantic chunking, and LanceDB embeddings.

**Supported products / workflows:**

| Product | Entry (HTTP) | MCP tool | LLM / prompts |
|---|---|---|---|
| STAR | `POST /star/text-mining` | `process_document` | `app/text_mining/star_mining/` + `prompt_star.py` |
| PRMS | `POST /prms/text-mining` | `process_document_prms` | `app/text_mining/prms_mining/` + `app/utils/prompt/prms/` |
| AICCRA | `POST /aiccra/text-mining` | `process_document_aiccra` | `app/text_mining/aiccra_mining/` + `prompt_aiccra.py` |
| STAR Bulk CapDev | `POST /star/mining-bulk-upload/capdev` | `process_document_capdev` | `app/text_mining/bulk_upload/upload_capdev.py` + `bulk_upload_capdev_prompt.py` |

Related surfaces:

- **FastAPI + MCP**: `app/mcp/client.py` (HTTP) spawns `app/mcp/server.py` (stdio MCP tools).
- **Static AICCRA UI**: `interface/aiccra_mining/` → `/ui` and `/static/*`. The development-only `interface/bulk_upload/` files and `/bulk-upload` route are absent from this branch; do not reintroduce them merely to match development.
- **Next.js Bulk Upload UI**: `frontend/` (SST / OpenNext). See [`frontend/AGENTS.md`](frontend/AGENTS.md).
- **DynamoDB** status tracking for bulk upload: table `bulk_upload_records` (prod) / `bulk_upload_records_test` (non-prod). Development has historical internal docs under `app/utils/dynamo/docs/`; these files are absent from the reviewed service-main snapshot. Current shared behavior is described in the [API guide](docs/API_GUIDE.md).
- **Feedback / interactions**: `/feedback`, `/feedback/{interaction_id}`; interaction client in `app/utils/interactions/`.

**Request rules:**
- STAR/AICCRA mining: send either `key` (+ `bucketName`) **or** `file`. The handlers reject requests with neither input, but do not reject both; an uploaded file takes precedence. Bulk CapDev follows the same input-selection behavior.
- PRMS mining: multisource — any combination of `keys`, `text`, and `audio_keys` (at least one required). Documents and audio must already exist in S3. Auth is CLARISA `X-API-Key` only (no `token` / `environmentUrl`).

---

## Repository layout

```
text-mining-service/
├── main.py                 # Lambda entry (Mangum → FastAPI app)
├── app/
│   ├── mcp/                # FastAPI client + MCP server tools
│   ├── text_mining/        # star_mining/; prms_mining/; providers/; shared/; AICCRA; CapDev
│   ├── middleware/         # STAR auth middleware
│   ├── schemas/            # Pydantic response schemas (STAR vs PRMS)
│   └── utils/              # config, S3, CLARISA, Dynamo, prompts, Slack, cron
├── frontend/               # Next.js 15 Bulk Upload app (nested AGENTS.md)
├── interface/              # Static HTML/JS UIs mounted by FastAPI
├── tests/                  # Fixtures + PRMS unit/API tests under tests/prms/
├── pyproject.toml          # Python deps (uv)
├── requirements.txt        # Used by Dockerfile / Lambda image
└── Dockerfile              # AWS Lambda Python 3.13 image
```

---

## Architecture (agent mental model)

```
Client → FastAPI (app/mcp/client.py)
       → MCP stdio client → MCP server (app/mcp/server.py)
       → STAR token/role checks where required (CLARISA runs at HTTP entry)
       → LLM pipeline (S3 → chunk → embed LanceDB → Bedrock → JSON)
       → Slack notification + optional interaction tracking
```

- Local HTTP API: `python -m app.mcp.client` → `http://localhost:8000` (`/docs`, `/redoc`).
- Lambda: `main.handler` wraps the same FastAPI app via Mangum.
- Do **not** treat `uv run python main.py` as the local API server; use the client module above.

---

## Setup commands

Use **Python 3.13**. The explicit virtual environment below follows the Dockerfile dependency input. `requirements.txt`, `pyproject.toml`, and the valid, up-to-date `uv.lock` all select LanceDB 0.36.0. Docker installs from `requirements.txt`, not the lockfile; other dependency selections can still differ between pip and uv workflows.

```bash
cd text-mining-service
python3.13 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

Create `.env` using the [README configuration](README.md#configuration); no `.env.example` template is included in this branch. `requirements.txt` is the Lambda packaging input. For an explicitly chosen lockfile workflow, use locked uv commands consistently in a separate environment; do not mix that dependency selection with the requirements-based environment or claim existing-environment tests cover the newly locked versions. Preserve the maintainer's lockfile changes and keep them separate from documentation edits in review.

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
| `python -m app.mcp.client` | Start FastAPI locally on port 8000 |
| `python app/mcp/server.py` | Run MCP server alone (usually spawned by the client) |
| `python app/utils/cronjob/setup_db_cleaner_cron.py install` | Install LanceDB temp cleanup cron |
| `cd frontend && npm run dev` | Next.js Bulk Upload UI (HMR) |
| `cd frontend && npm run lint` | ESLint for frontend |
| `cd frontend && npm run build` | Production Next build — **avoid during agent sessions** |

---

## Code style & conventions

### Backend (Python)

- Prefer changes in existing modules; match naming and logging style (`app/utils/logger/logger_util.py`).
- Keep product-specific logic separated: STAR under `text_mining/star_mining/`, PRMS under `text_mining/prms_mining/`, AICCRA under `text_mining/aiccra_mining/`, bulk CapDev under `text_mining/bulk_upload/`. Shared Bedrock invocations live in `text_mining/providers/`; common helpers in `text_mining/shared/`. Prompts under `app/utils/prompt/` (PRMS modular under `prompt/prms/`).
- Config comes from env via `app/utils/config/config_util.py` — do not hardcode secrets, bucket names for credentials, or webhook URLs.
- Auth: STAR uses management-token validation plus CLARISA; Bulk CapDev also checks roles 1/9/10. PRMS uses CLARISA `X-API-Key` only. AICCRA accepts token fields but its MCP tool does not validate them. Preserve actual behavior and describe it accurately; do not assume all routes have the same controls.
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

- Interactive API checks: start `python -m app.mcp.client`, then use `/docs` or curl against `/star/text-mining`, `/prms/text-mining`, `/aiccra/text-mining`, `/star/mining-bulk-upload/capdev`.
- Sample payloads / fixtures live under `tests/` (`test.json`, `test1.json`, `test2.json`) and `tests/prms/fixtures/`.
- PRMS automated tests: `python -m pytest tests/prms/unit -q` and `python -m pytest tests/prms/api -q`. Prefer targeted coverage for multisource/auth/prompt changes. The HTTP module attempts to verify/create a DynamoDB table on import; stub that function before importing the app for offline API checks. Test fixtures alone do not suppress every import-time effect.
- After import moves or API changes, ensure the MCP client still starts and OpenAPI at `/docs` reflects new routes.
- Frontend: `cd frontend && npm run lint`. Prefer `npm run dev` over `npm run build` while iterating.

---

## Security considerations

- Never commit `.env`, AWS keys, CLARISA passwords, Slack webhooks, or API keys.
- Do not log full tokens, `client_secret`, or API keys.
- STAR, PRMS, and Bulk CapDev mining routes have CLARISA dependencies. Dynamo/helper route declarations do not all have such dependencies. Preserve active controls; do not document helper routes as protected merely because the UI has a login.
- CORS is intentionally open in the FastAPI app; do not widen secret exposure in responses.
- Active LanceDB processing data is under `/tmp/miningdb`; logs are in `/tmp/logs/app.log`. Avoid committing runtime data or shipping large generated DB artifacts.
- Dockerfile copies `.env` into the image in this repo — treat that as a deployment smell; never add new secrets into the image or source.

---

## Deployment & CI

- **Container / Lambda**: `Dockerfile` → `CMD ["main.handler"]`.
- **GitHub Actions** (monorepo `.github/workflows/`): pushes trigger Jenkins jobs, e.g.:
  - `jenkins-trigger-ai-text-mining.yml` → `main-text-mining` on pushes and pull requests
  - Bulk Upload frontend: `jenkins-trigger-ai-bulk-upload-dev-prod.yml` → `main-text-mining` pushes; development has a separate frontend trigger
- Frontend deploy tooling: SST (`sst.config.ts`) + OpenNext; see nested AGENTS.md. Documentation-only updates are not excluded from the reviewed Jenkins triggers. Verify actual filters in the branch being pushed.

---

## PR / change guidelines

- Scope PRs to one concern when possible (e.g. bulk-upload vs core STAR mining).
- Touch prompts only when the task requires extraction-behavior changes; call that out in the PR summary.
- If you change REST contracts used by STAR/PRMS/AICCRA clients or the Next.js BFF routes (`frontend/app/api/*`), update callers and document the contract change.
- Do not rewrite unrelated legacy `interface/` code when working in `frontend/`, and vice versa.
- Before finishing a task that claims a fix: run the relevant local server or lint command and fix failures you introduced.

---

## Environment variables (high level)

Backend `.env` (see README for examples): AWS credentials/region, CLARISA (`CLARISA_*`, `CLARISA_VALIDATE_URL`), `CLIENT_ID` / `CLIENT_SECRET`, bucket key prefixes (`STAR_BUCKET_KEY_NAME`, `PRMS_BUCKET_KEY_NAME`, `AICCRA_BUCKET_KEY_NAME`), `MAPPING_URL`, `SLACK_WEBHOOK_URL`, `IS_PROD`, `MS_NAME`. PRMS audio is disabled by default; enable it with `PRMS_AUDIO_TRANSCRIBER=amazon_transcribe` plus optional `PRMS_TRANSCRIBE_*` / `PRMS_MAX_AUDIO_SECONDS`. There is no fixed ten-minute duration limit unless configured. The alternate Supabase modules and older CLARISA connection helpers are absent here; do not add imports or setup requirements for them. STAR tokens come from requests, not the development-only `AUTH_TOKEN_STAR` configuration entry.

See the [API guide](docs/API_GUIDE.md) for HTTP-vs-MCP response wrappers and the [high-level design](docs/HIGH_LEVEL_DESIGN.md) for active per-source PRMS extraction. Earlier draft specifications describe planning decisions, not guaranteed current behavior.

Frontend: `NEXT_PUBLIC_MINING_API_BASE_URL`, `NEXT_PUBLIC_STAR_API_BASE_URL`, `NEXT_PUBLIC_MANAGEMENT_API_BASE_URL`, `NEXT_PUBLIC_CLARISA_API_BASE_URL`, plus server-side `BULK_UPLOAD_API_KEY` / `MINING_API_BASE_URL` for BFF routes.

---

## Where to look first

| Task | Start here |
|---|---|
| New HTTP endpoint | `app/mcp/client.py` |
| New MCP tool / mining flow | `app/mcp/server.py` + matching module under `app/text_mining/` |
| PRMS multisource mining | `app/text_mining/prms_mining/` + `app/utils/prompt/prms/` |
| Shared Bedrock invoke | `app/text_mining/providers/bedrock_client.py` |
| Prompt / extraction shape | `app/utils/prompt/` + `app/schemas/star_mining_schemas.py` (STAR) or `app/schemas/prms_mining_schemas.py` (PRMS) |
| Organization cleanup after mapping | `app/text_mining/shared/organization_fields.py` (`clean_organization_fields`) |
| Auth | STAR: `app/middleware/star_auth_middleware.py`; PRMS/STAR HTTP: CLARISA via `validate_with_clarisa` in `client.py` |
| Bulk upload status | `app/utils/dynamo/`, Dynamo routes in `client.py` |
| Next.js Bulk Upload UX | `frontend/components/BulkUpload/` |
| AICCRA static UI | `interface/aiccra_mining/`; no legacy bulk-upload UI in this branch |
