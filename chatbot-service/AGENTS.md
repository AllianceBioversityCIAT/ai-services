# Chatbot service: agent guide

Read the [root instructions](../AGENTS.md), [README](README.md) and [technical guide](TECHNICAL_DOCUMENTATION.md). These instructions describe `main-chatbot-service`; verify the current branch/tree before editing.

## Branch scope

Normal work starts from `dev-chatbot-service` in a focused task branch when appropriate. Promotion is dev-chatbot-service → main-chatbot-service → staging → main. When the maintainer requests review after a local service-main merge, adapt documentation on that service-main to the actual tree. The maintainer performs release merges unless delegated; commit and push remain separate operations.

Read the [branch comparison](docs/BRANCH_DIFFERENCES.md). Preserve service-main's Docker/requirements installation, SDK credential chain, `/tmp/logs` and production interaction URL. Do not restore development-only files simply to match trees.

## Implementation map

- Local HTTP: `api_server.py` → `app.api.main:app`; Lambda: `main.handler` via Docker's Python 3.13 image.
- Contract: `app/api/models.py` and `routes.py`; active chat: `app/llm/agents.py`.
- Retrieval settings: `app/utils/agents_utils/filter_builder.py`.
- UI: `interface/chatbot_interface.html`; read its [nested instructions](interface/AGENTS.md).
- S3 helpers are retained but not called by chat; the inactive feedback helper imports missing models.

Install from `requirements.txt` in the service directory. There is no pyproject/uv lock, Streamlit entry point, SQL loader, converter suite or direct OpenSearch/LLM/KB module here. Dependency names or residual config dictionaries are not proof those tools exist.

## Behavior constraints

- Coordinate models/routes, HTML callers, examples and [API contract](docs/API.md).
- Treat prompts, model IDs, retrieval filters, identity and authentication as behavior changes. Agent model/instructions/memory are externally configured; local template edits do not update them.
- `insert_data` does not execute reload here; route metadata can still claim it. Health is static.
- No route authentication or memory ownership check exists. Email identifiers and CORS are not authorization.
- The HTML calls fixed Lambda and production interaction URLs even when served locally; Python `.env` does not override them.
- The Dockerfile copies `.env` and full context. Keep real credentials and reporting artifacts out of commits/images; do not change deployment configuration incidentally during docs work.

## Checks and reporting

No dedicated service test suite is tracked. Validate links/examples and implementation consistency. Use fake generators for API tests, fake boto3 before agent import, blocked network and replaced logging. Syntax-check extracted JavaScript without executing fetch. Retained S3 helpers can write to AWS; inspect them before execution.

Do not infer live deployment, credentials, ingestion or feedback success from stubs. Report branch, scope, checks/limits and commit/push state. Preserve user changes and avoid adding logs, exports, local databases, credentials or generated output.
