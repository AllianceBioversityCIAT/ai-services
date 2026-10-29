# Chatbot service: agent guide

Read the [root instructions](../AGENTS.md), [README](README.md) and relevant [technical guide](TECHNICAL_DOCUMENTATION.md) before editing. These instructions describe `dev-chatbot-service`; verify the current branch and tree every time.

## Branch scope

Prepare work from `dev-chatbot-service`, using a focused task branch when appropriate, and preserve existing user commits. Normal promotion is dev-chatbot-service → main-chatbot-service → staging → main. The maintainer performs release merges unless explicitly delegated. Commit and push are separate operations.

Read [branch differences](docs/BRANCH_DIFFERENCES.md) before integration. After a maintainer's local merge into service-main, inspect complete trees and adapt docs to actual production packaging, credentials, log paths and interface destinations. Do not equate merging documentation with development/production parity.

## Implementation map

- HTTP entry: `api_server.py` → `app.api.main:app`; Lambda adapter: `main.handler`.
- Contract: `app/api/models.py`, `routes.py`; active chat: `app/llm/agents.py`.
- Retrieval settings: `app/utils/agents_utils/filter_builder.py`.
- Two UIs: `chatbot.py` calls the generator directly; `interface/chatbot_interface.html` calls HTTP. Read [nested interface instructions](interface/AGENTS.md) for HTML edits.
- SQL, direct OpenSearch, direct KB/model calls, S3 exports, OpenAI CLI and the five scripts under `app/utils/conversion/` are auxiliary. They can create clients at import, write data or incur charges.

Run from `chatbot-service/`. Use `pyproject.toml`/`uv.lock` for this dev snapshot (`uv sync --frozen`). Its pip requirements have trailing commas; do not fix manifests or deploy configuration as an incidental docs change. Auxiliary SQL requires undeclared pyodbc and native ODBC Driver 18.

## Constraints to preserve

- Coordinate contract changes with both UIs, examples and [API documentation](docs/API.md).
- Treat prompts, model IDs, retrieval filters, identity and authentication as behavior changes.
- Agent instructions/model/memory live externally; local prompt edits do not update them.
- `insert_data` is not used to execute a reload by the agent, despite route metadata. Health is static.
- No route authentication or memory ownership check is implemented; email identifiers and CORS are not authorization.
- HTML fixed URLs and Streamlit `.env` tracking URL are separate configuration surfaces. The HTML page calls the configured Lambda chat endpoint even when served locally; use the local API examples to test the local backend.
- Do not import the inactive feedback helper as a supported API; its models are missing.

## Checks and reporting

No dedicated service test suite is tracked here. For docs, resolve local links, parse examples and verify claims against implementation. For offline API checks, replace the generator; for agent checks, replace boto3 before import, use fictional events and block network. Replace logging to avoid generated files. Syntax-check extracted HTML JavaScript without executing fetch.

Read SQL/S3/CLI scripts before execution: some run at import or contact live systems. Do not run interfaces against external providers merely to validate prose. Never claim deployment, feedback, ingestion or credentials work based on stubs. Report branch, changed scope, checks, limits and commit/push state. Keep real `.env`, logs, exports, databases and reporting data out of commits.
