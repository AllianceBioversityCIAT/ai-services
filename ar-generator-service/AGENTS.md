# AICCRA production Report Generator: agent guide

Read the [root instructions](../AGENTS.md), [README](README.md), and relevant source before editing. For browser work read [web instructions](web/AGENTS.md). This guide describes **main-ar-generator**, including SQL Server, production Lambda packaging, and scheduled operations.

## Scope and integration

- Development is dev-ar-generator; service-main is main-ar-generator. The maintainer uses local CSV/MySQL development and one production Lambda rather than a separate test Lambda.
- Preserve intentional branch differences in the [branch matrix](docs/BRANCH_DIFFERENCES.md). Do not make production match a local machine by removing pyodbc, changing structured-loader imports, replacing the Lambda dispatcher, or copying local debug/cron paths into production execution.
- The Docker command is api_server.handler, not main.handler. Keep the ODBC-enabled image, requirements, .dockerignore, SQL Server loader/exports, job dispatcher, workflow, production logger and analytics host unless a separate behavior/deployment change is requested.
- Compare the complete incoming diff after maintainer integration, including root/shared files and other services. Keep the existing root ignore changes and user commits intact. Adapt production docs as part of the authorized review; leave commit/push within the user's requested scope.
- Shared guide work should remain separable in commits/review. Do not change prompts, model settings, dependencies, logging, API behavior, or deployment configuration merely to simplify documentation.

## Implementation map

| Path | Responsibility |
| --- | --- |
| Dockerfile, .dockerignore, requirements.txt | Production Lambda Python 3.13 image, ODBC 18 and Python dependencies |
| api_server.py | HTTP/EventBridge detection, Mangum adapter, scheduled-job dispatch |
| dev_server.py | Auxiliary local Uvicorn launcher; still needs this branch's native/import stack |
| main.py | Simple alternate Mangum adapter; not Docker's selected handler |
| app/api/main.py, routes.py, models.py | App, eager SQL-loader import, lazy report functions, complete JSON, UI, schema validation |
| db_conn/sql_connection.py | SQL views, source transforms, prepared CSV override in load_data, S3 exports, load_full_data |
| app/llm/vectorize.py, vectorize_annual.py | Active S3 Vectors report pipelines; no development context-dump calls |
| app/llm/invoke_llm.py | Titan embeddings and accumulated Claude stream |
| app/s3_vectors/, app/retrieval/ | Index operations, ingestion/schema, semantic/structured retrieval and filters |
| app/utils/jobs/scheduled_jobs.py | Production AR refresh, chatbot export and KB synchronization |
| app/utils/s3/ | Ordinary S3 upload client and per-record chatbot CSV/metadata splitting |
| app/utils/prompts/, config/, logger/, notification/ | Report behavior, environment values, /tmp logs, optional Slack |
| web/ | Static UI, fixed production API/analytics destinations and browser downloads |
| tests/test_retrieval.py, test_vector_store_schemas.py | Six filter/schema assertions; isolate package initialization for offline collection |

## Contracts and external effects

- All four POST report routes use ChatRequest: required free-text indicator, year 2021–2026, nullable insert_data default false. Tables/challenges consume only year at route level and do not forward the rebuild flag.
- Public reports are complete JSON, not streamed tokens or durable background jobs. HTTP 200 can contain status:error or error prose. Read [API semantics](docs/API_GUIDE.md#responses-and-failure-semantics) and preserve the route-specific differences.
- Narrative insert_data:true deletes/recreates the whole configured S3 Vectors index and ingests five/six source tables. Mid-year and annual share that configured index; there is no documented rebuild transaction/lock or per-year index isolation.
- Even insert_data:false can alter SQL views and export files to ordinary S3 through load_data. Reads are not necessarily side-effect-free. Loader/retrieval/ingestion errors can become empty structures/zero counts and allow incomplete downstream generation.
- SQL Server uses pyodbc/ODBC 18 and service-principal configuration. Several report-source transforms restrict rows to 2025/2026 despite the API's wider year range. Preserve transforms, table_type labels, exports, cleanup, and data semantics during changes.
- USE_CSV_DATA affects load_data only, not load_full_data, and does not remove import-time pyodbc/S3 dependencies. Default is false; CSV lookup resolves to app/ and expects prepared rows. Use development for pyodbc-free local work.
- Bedrock/S3 Vectors use explicit OS-named keys and configured region. The ordinary S3 export client instead uses boto3's standard credential chain. Do not promise identical credential resolution across clients.
- API routes have no general token/API-key dependency. CORS and outbound IAM permissions do not establish caller authorization; infrastructure controls require separate verification.
- api_server imports scheduled jobs/annual pipeline at startup; FastAPI routes also import SQL/export code eagerly. Health returning static metadata does not establish generation configuration or provider access.

## Scheduler and browser boundaries

The hybrid handler accepts job-only events with a string job name only when HTTP event keys are absent. Preserve requestContext/rawPath/body/httpMethod discrimination and Mangum handling. Supported job names are update_ar_data, update_chatbot_data, and sync_knowledge_base. The AR job currently uses IPI 1.3/year 2025/rebuild true. KB start success is not ingestion completion.

The UI targets the production Lambda even when served locally. Production analytics is i8s5i8c21i.execute-api.us-east-1.amazonaws.com, distinct from development. Inspect/stub both destinations before browser checks. Tracking may include identity parameters/generated output; it is not authentication. The date badge calculates a Sunday rather than querying ingestion state.

## Run and verify

Production installs requirements.txt in the ODBC-enabled Docker image and starts api_server.handler. There is no tracked pyproject/uv lockfile here. Local diagnostics can use dev_server.py or app.api.main:app only in a suitable Python 3.13/ODBC environment; uv/CSV-only startup belongs to development. Do not build/publish merely to check docs.

Read package initializers as well as test functions. app.s3_vectors.__init__ imports ingestion/data/provider code during normal collection, including production pyodbc dependencies. The technical guide's offline bootstrap runs the six actual filter/schema assertions without that initializer and blocks network; it does not validate startup.

For offline API/loader/provider/handler checks, block network, prevent real dotenv loading, stub logger/pyodbc/providers before import, use synthetic temporary data, and capture exports/rebuilds/jobs only in fakes. Never call SQL, rebuild an actual index, invoke a real job, or send Slack/analytics as a documentation check.

Report checks separately from real ODBC installation, AWS/SQL credentials, model quality, Jenkins, or deployment. Only docs and the example template are adjusted by this production-alignment task; actual Lambda environment values remain outside its scope.
