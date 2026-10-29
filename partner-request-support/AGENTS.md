# Partner Request Support: agent guide

Read the [root instructions](../AGENTS.md), [service README](README.md), and the relevant component README before editing. This service combines a FastAPI backend and a static Next.js frontend. Documentation here describes `main-partner-request-support`; its cache table, default CORS origin, frontend login, and badge retain production choices. Local execution does not switch them to development.

## Scope and integration

- Development: `dev-partner-request-support`; service-main: `main-partner-request-support`. Verify references before starting.
- Prepare focused work from development. The maintainer handles development-to-service-main integration unless explicitly delegated. Review the complete incoming diff; a branch snapshots the whole monorepo.
- This branch selects `partner_request_cache_prod`, defaults CORS to `https://d2xsau6p4hnevy.cloudfront.net` plus localhost, uses `https://api.clarisa.cgiar.org/auth` for login, and displays Production Environment. Preserve these production cache constants/SQL, CORS, frontend login URL, and environment label. Read [branch differences](docs/BRANCH_DIFFERENCES.md) before adapting service-main docs.
- Keep shared `AGENTS.md` changes separable from service documentation. Do not change other services, dependencies, or Jenkins configuration as part of documentation maintenance.

## Implementation map

| Path | Responsibility |
| --- | --- |
| `backend/api.py` | FastAPI routes, request models, synchronization, orchestration, automatic decisions |
| `backend/main.py` | Mangum Lambda handler |
| `backend/src/mapping_clarisa_comparison.py` | Translation, hybrid candidate search, reranking, manual-review labels |
| `backend/src/supabase_client.py` | Vector RPCs and branch-specific cache table |
| `backend/src/populate_clarisa_db.py` | Institution synchronization, embeddings, deletion of obsolete records |
| `backend/src/embeddings.py` | Titan Text Embeddings V2 |
| `backend/src/web_search.py` | OpenAI web research, Bedrock formatting/rules/duplicate checks |
| `backend/src/notifications.py`, `email_microservice.py` | Manual-review notifications through RabbitMQ |
| `backend/config/config_util.py` | AWS and email configuration |
| `backend/sql/` | Vector schema/RPCs and cache schema |
| `frontend/app/` | Browser review workflow; read [frontend instructions](frontend/AGENTS.md) |

## Contracts and behavior

Use [API guide](docs/API_GUIDE.md) as navigation, then verify `api.py` and callers. Several docstrings describe earlier behavior. In particular:

- `process-api-partners` accepts a bare JSON array, not an object. Omitted/null/empty IDs select the oldest ten requests in the current pending snapshot; explicit IDs select matching pending requests.
- `sync-clarisa-institutions` accepts a bare boolean. Processing also synchronizes with deletion enabled and writes cache.
- Excel upload defaults `create_requests=true`; the frontend explicitly enables it. Use the actual template: parsing uses positional columns.
- Manual quality tiers and automatic decision tiers are distinct. Preserve exact boundary comparisons. Reranking is 60% semantic, 30% name, 10% acronym; retrieval's 70/30 name/acronym weights are a separate stage.
- Automatic web/rules acceptance uses the rules result. Completeness is informational in that path, despite an older helper docstring calling it a gate.
- `auto_respond=false` does not disable paid models or manual-review notifications. `create_in_clarisa=true` creates first and can submit a decision even with auto-response false. Creation and response are not atomic.
- Local orchestration fields (`user_id`, flags, token) are not all fields in the external CLARISA create payload. Confirm environment-specific catalogs/authentication before integration.
- Frontend login does not imply backend-wide access control: routes have no general FastAPI authentication dependency. Preserve current behavior unless a separate behavior change is requested.

## Runtime and checks

From `backend/`, use Python 3.13, install `requirements.txt`, and run `python -m uvicorn api:app --host 127.0.0.1 --port 8000`. Docker installs requirements; `pyproject.toml` currently omits `pika`. Do not silently reconcile manifests in an unrelated task.

Import constructs provider clients; inspect configuration before importing. `GET /health` only reports process health. `backend/test/` contains live examples, including import-time web calls, rather than an isolated test suite. Do not run them for routine validation.

For offline route checks, stub CLARISA, Supabase, AWS/OpenAI, and notifications before import and block network. Validate request shapes, batching, score boundaries, and decisions without asserting provider accuracy. For frontend checks, use its npm scripts after inspecting [frontend README](frontend/README.md).

For documentation-only work, check local links, example syntax, source consistency, and the Markdown-only diff. Live sync, cache clearing, request creation/response, real email, Docker/deployment, or paid model checks need their own deliberate scope. Never include tokens, real request records, or generated logs in commits.
