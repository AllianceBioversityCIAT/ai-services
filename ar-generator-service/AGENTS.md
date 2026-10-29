# AICCRA Report Generator: agent guide

Read the [root instructions](../AGENTS.md), [README](README.md), and relevant source before editing. For browser work also read [web instructions](web/AGENTS.md). This guide describes development's local CSV/MySQL path, not a production-equivalent Lambda environment.

## Branch and scope rules

- Development is `dev-ar-generator`; production service-main is `main-ar-generator`. The maintainer uses local development and a production Lambda; do not invent a separate test Lambda or infer deployed inventory from files.
- Preserve local user commits. This documentation branch started from local development `ec875c50`, which includes an existing root `.gitignore` commit beyond remote development. Do not reset or silently drop it.
- The service trees intentionally differ substantially. Read [branch differences](docs/BRANCH_DIFFERENCES.md) before integration. Do not make them identical by copying the local loader, launcher, dependencies, debug files, or cron scripts into production paths.
- Production's Docker command uses `api_server.handler`, including HTTP/EventBridge dispatch. Development's `main.handler` is only a simple Mangum adapter. Preserve production's dispatcher, scheduled jobs, ODBC image, SQL Server loader/export helper, requirements, logger, workflow, and analytics destination unless separately asked to change them.
- After the maintainer's local development-to-service-main merge, compare the complete incoming diff, preserve intentional differences, and adapt main-specific docs as part of the already-authorized review. Keep commits/pushes within the user's requested scope.
- Shared guide changes belong in separable commits. Do not change other services, prompt behavior, model settings, dependencies, or deployment configuration as a documentation cleanup.

## Implementation map

| Path | Responsibility |
| --- | --- |
| `dev_server.py` | Local Uvicorn launcher, dotenv before app import |
| `main.py` | Simple development Mangum adapter |
| `app/api/main.py`, `routes.py`, `models.py` | FastAPI app, lazy report imports, complete JSON responses, static UI, validation |
| `app/llm/vectorize.py` | Active mid-year pipeline, summary, semantic/DOI merge, context debug file |
| `app/llm/vectorize_annual.py` | Annual summary/cluster drafting, tables, challenges, context debug file |
| `app/llm/invoke_llm.py` | Titan embeddings and accumulated Claude stream |
| `app/s3_vectors/` | SDK client, index rebuild, ingestion, metadata/chunk serialization |
| `app/retrieval/` | Semantic queries, structured evidence, business filters |
| `db_conn/mysql_connection.py` | Development CSV/MySQL loader; no active pyodbc import |
| `app/utils/prompts/` | Reporting and disaggregation instructions; behavior, not incidental copy |
| `app/utils/cronjob/` | Retained host-cron setup and scripts, some calling production |
| `web/` | Static UI with fixed API/analytics destinations |
| `tests/test_retrieval.py`, `test_vector_store_schemas.py` | Six filter/schema assertions; package imports need isolation |
| `tests/streamlit/`, `lakehouse_integration/` | Separate potentially live diagnostic/manual tools |

## Contracts and effects

- API bodies use `ChatRequest`: required free-text indicator and year 2021–2026, optional insert_data default false. Tables/challenges require the same body but consume only year; do not describe them as per-indicator rebuild operations.
- The public report API returns complete JSON. Bedrock streaming is internal; synchronous generation is not a persistent job or client token stream. Do not infer successful background processing from a timeout.
- `insert_data=true` on narratives deletes/recreates the entire configured S3 Vectors index, not only one indicator/year. Mid-year and annual rebuild the same index with different table sets. Ingestion can skip rows/failures and is not transactional.
- `insert_data=false` still invokes AWS and reads structured data. CSV mode avoids database connections only in development's active loader; it is not an offline mode.
- Active AWS configuration uses `AWS_ACCESS_KEY_ID_OS` / `AWS_SECRET_ACCESS_KEY_OS` and AWS_REGION. The old BR aliases do not configure the active client. Bedrock requires explicit keys; do not promise Lambda-role fallback for that path.
- Development's current loader reads prepared CSVs directly or transforms MySQL data. Production imports `pyodbc` and a different SQL Server loader; even its CSV branch does not remove the import dependency. Production SQL reads can create/alter views and export to S3.
- CSV lookup defaults to `app/`. The source's missing-file message saying service root is stale. Prepared `table_type`, year, and business fields matter; do not assume arbitrary raw CSVs match production processing.
- Routes have no general token/API-key dependency. CORS and infrastructure descriptions do not establish deployed authorization. Generated metadata still contains historical OpenSearch/model/year statements.
- HTTP 200 can contain status:error or error prose; mid-year, annual, and challenges have different failure handling. Use [API guide](docs/API_GUIDE.md#responses-and-failure-semantics), then check executable branches.

## UI and retained tools

Serving `/web` locally does not make API requests local. Inspect `API_BASE_URL` and `AI_FEEDBACK_URL` before browser work; production and development retain different analytics URLs. UI tracking can send generated content and requester identity. Stub both endpoints for offline tests.

The OpenSearch, Supabase, and KB modules are reference paths with missing imports/config assumptions in this checkout, not validated rollback switches. Cron setup can modify the host crontab; cron/update scripts can rebuild production data, synchronize KBs, send Slack notifications, or call an absent public endpoint. Do not run them as tests.

## Setup and verification

Use Python 3.13, `uv sync --frozen --python 3.13`, and `uv run --frozen python dev_server.py --host 127.0.0.1 --reload` from this service. Production requirements/Docker are different and not present here. Do not add pyodbc to local development merely to match production packaging.

Read tests and package initializers before running them. The two named files target filter/schema behavior, but normal collection eagerly imports data/provider modules through app.s3_vectors.__init__. Use the documented offline bootstrap to isolate that initializer and block network; pytest must be available in the selected environment and is not declared in pyproject. Streamlit/cron/lakehouse tools are separate from those six assertions.

For documentation checks, validate links, example bodies, commands, branch inventory, and source claims. For offline API/data/provider checks, block network, prevent real dotenv loading, stub logger/clients before import, use fictional temporary CSVs, and never rebuild a real index. Preserve generated context/log/CSV artifacts outside commits.

Report local/offline results separately from AWS, SQL Server, model-quality, Jenkins, or deployment checks. The development `.env.example` intentionally enables CSV; adapt the production template separately during service-main review rather than changing live environment settings.
