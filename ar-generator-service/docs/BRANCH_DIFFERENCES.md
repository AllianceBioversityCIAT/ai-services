# Development and production branch differences

Initial comparison: local development `ec875c50` (service code from remote `d79ce98c`) against production service-main `2ca56cd1`. There are 43 differing tracked service paths before this documentation update. Local development also has an existing root `.gitignore` commit; it was preserved as the documentation base rather than reset.

The maintainer's deployment model is local development/testing and a production Lambda, without a separate test Lambda assumed. A clean merge must not erase the intentional runtime separation.

## Runtime matrix

| Area | Development | Production service-main |
| --- | --- | --- |
| Local startup | dev_server.py with CSV/MySQL environment | Same tracked dev_server.py helper, but SQL/ODBC imports remain; container is the production packaged path |
| Lambda adapter | main.handler, simple Mangum | Docker targets **api_server.handler**, HTTP plus EventBridge dispatch |
| Source data | db_conn/mysql_connection.py, prepared CSV or MySQL | db_conn/sql_connection.py, pyodbc/ODBC 18 SQL Server/Fabric; CSV branch still imports pyodbc |
| SQL processing | Development-specific transforms; CSV returned directly | View creation/alteration, richer transforms, selected year filtering, S3 exports |
| Packaging | pyproject + uv.lock; no service-root Dockerfile/requirements | ODBC-enabled Lambda Python 3.13 Dockerfile, .dockerignore and requirements |
| Scheduled operations | Host-cron scripts, some targeting production | scheduled_jobs.py invoked through hybrid handler |
| Debug context | Narrative pipelines save context JSON locally | Explicit context-save calls omitted |
| Logs | Service-relative data/logs, ar-generator-microservice logger | /tmp/logs, ar-generator-service logger |
| Ordinary S3 exporter | Explicit shared OS-named AWS key/secret | boto3 standard credential resolution for this client |
| UI generation base | Fixed production Lambda URL | Same fixed production Lambda URL |
| UI analytics host | clv3b6bv9d.execute-api.us-east-1.amazonaws.com | i8s5i8c21i.execute-api.us-east-1.amazonaws.com |
| Retained alternatives/tools | OpenSearch/Supabase/KB modules, Streamlit, ODBC diagnostic | Different/absent reference tools; do not assume a deployment dependency |
| Product/design/technical guides | Local workflow and shared reporting behavior | Reconciled with current SQL Server/Lambda/S3 Vectors production behavior |

Current active S3 Vectors client, metadata schema, semantic/filter helpers, API models, and most reporting logic are shared. Active report imports differ because they point to different structured loaders. routes.py also eagerly imports load_full_data in production, pulling in SQL/export dependencies at app startup, unlike development's lighter route import path.

## Preserve on the production side

- Keep the ODBC-enabled Dockerfile and its api_server.handler command, requirements, .dockerignore, production logger, hybrid dispatcher, scheduled_jobs.py, SQL Server loader, and divide_jsonl_files helper unless a separate runtime change is requested.
- Keep production imports through db_conn/sql_connection.py in the pipelines, ingestion, and structured retrieval. Do not replace them with development's local loader to resolve conflicts quickly.
- Preserve the intended production analytics host, ordinary S3 credential behavior, and notification formatting differences. Treat changing them as behavior/configuration work.
- Keep development-only context dumping and local cron/reference tooling out of active production execution paths unless deliberately integrated. File presence and active runtime use are separate decisions.
- Both branches currently share explicit OS-named keys for Bedrock/S3 Vectors. Do not assume all other clients use the same credential source.
- Development's updated .env.example enables CSV and uses local placeholders. Adapt main's example for the intended production setup; do not copy those settings into live Lambda configuration.

## Public and background interfaces

The four report routes and request schemas are broadly shared, including the 2021–2026 year constraint and complete JSON responses. Neither branch's shown routes implement /api/update-chatbot-data; production's supported chatbot refresh interface is a scheduler event dispatched internally.

Production's hybrid handler treats job-only events such as `{"job":"update_ar_data"}` as scheduler work only when HTTP event keys are absent. HTTP-shaped events go to Mangum. The three supported jobs are update_ar_data, update_chatbot_data, and sync_knowledge_base. The AR job uses fixed IPI 1.3/year 2025/rebuild settings in this snapshot; inspect actual source before any operational execution.

The production-branch GitHub workflow targets push/PR base main-ar-generator and manual dispatch, invoking Jenkins job ar-generator-pro-lambda. That workflow is absent from development, where only a Text Mining workflow is currently tracked. Preserve production automation during integration; no live Jenkins or scheduler state is established by this review.

## Local production integration review

Reviewed local service-main `8e0ac988` against production base `2ca56cd1` and development documentation tip `2c0df941`. The documentation commits were applied on top of production as local commits rather than a two-parent merge, so ancestry equality with development is not the correctness criterion.

- The incoming local commits change ten Markdown files, the configuration example, and the pre-existing root .gitignore change. No application, SQL loader, model, prompt, dependency, packaging, job, UI JavaScript, or workflow file changed relative to production base.
- Production's Dockerfile, .dockerignore, requirements, api_server handler, scheduled jobs, SQL Server loader/export helpers, log configuration, analytics destination, and production workflow remain byte-for-byte identical to the production base.
- Development-only MySQL/reference/cron/Streamlit/lakehouse/uv paths remain absent intentionally. dev_server.py and main.py were already shared tracked files and remain available as auxiliaries, distinct from the packaged api_server.handler.
- Production READMEs, API/design/product/technical guides, agent instructions and .env.example are now aligned to the actual SQL/ODBC/dispatcher path. The example defaults to CSV disabled; no live environment was edited.
- Offline checks use fake SQL/AWS/export/job clients and isolated filter/schema collection. They do not verify actual native-driver installation, source permissions, model quality, a running schedule, Jenkins, or deployment.

## Integration checklist

1. Refresh references and inspect all incoming commits, including the pre-existing local root .gitignore commit. Branches snapshot other services too; service-only diffs do not establish the whole merge scope.
2. Let the maintainer integrate development into main-ar-generator locally without pushing yet.
3. Inspect the resulting entire tree and service diff. Recheck all files in the inventory below, and any new changes since this baseline.
4. Preserve the production runtime/data/handler/packaging/jobs/workflow differences above. Do not treat matching development exactly as the goal.
5. Adapt service-main README, API/design/product/technical guides, web instructions, agent guides, and configuration example to the resulting production tree. Reconcile the pre-existing detailed guides rather than leaving local instructions labelled as production.
6. Verify schemas, offline route/filter behavior, handler event routing with fakes, imports/packaging references, and local documentation links. Separate these from live ODBC, SQL side effects, vector writes, model calls, browser analytics, pipeline, or deployment checks.
7. Leave release merges/pushes with the maintainer. Completed service work accumulates in staging for the agreed consolidated PR to main.

## Initial file inventory

The labels describe committed development versus production before this documentation task. They do not mean that a future Git merge will automatically delete or keep a file; review the actual merge result.

| Service-relative path | Initial difference |
| --- | --- |
| `.dockerignore` | Production only |
| `.env.example` | Present in both; differs |
| `.gitignore` | Present in both; differs |
| `Dockerfile` | Production only |
| `README.md` | Present in both; differs |
| `api_server.py` | Production only |
| `app/api/routes.py` | Present in both; differs |
| `app/llm/invoke_llm.py` | Present in both; differs |
| `app/llm/knowledge_base.py` | Development only |
| `app/llm/opensearch/vectorize_os.py` | Development only |
| `app/llm/opensearch/vectorize_os_annual.py` | Development only |
| `app/llm/supabase/vectorize_db.py` | Development only |
| `app/llm/vectorize.py` | Present in both; differs |
| `app/llm/vectorize_annual.py` | Present in both; differs |
| `app/retrieval/sql_retrieval.py` | Present in both; differs |
| `app/s3_vectors/ingestion.py` | Present in both; differs |
| `app/utils/config/config_util.py` | Present in both; differs |
| `app/utils/cronjob/setup_cron.py` | Development only |
| `app/utils/cronjob/setup_cron_chatbot.py` | Development only |
| `app/utils/cronjob/setup_cron_kb_sync.py` | Development only |
| `app/utils/cronjob/sync_knowledge_base.py` | Development only |
| `app/utils/cronjob/update_ar_data.py` | Development only |
| `app/utils/cronjob/update_chatbot_data.py` | Development only |
| `app/utils/jobs/scheduled_jobs.py` | Production only |
| `app/utils/logger/logger_util.py` | Present in both; differs |
| `app/utils/notification/notification_service.py` | Present in both; differs |
| `app/utils/prompts/kb_generation_prompt.py` | Development only |
| `app/utils/s3/divide_jsonl_files.py` | Production only |
| `app/utils/s3/upload_file_to_s3.py` | Present in both; differs |
| `db_conn/mysql_connection.py` | Development only |
| `db_conn/sql_connection.py` | Production only |
| `docs/HIGH_LEVEL_DESIGN.md` | Production only |
| `docs/PRODUCT_OVERVIEW.md` | Production only |
| `docs/TECHNICAL_DOCUMENTATION.md` | Production only |
| `lakehouse_integration/.env.example` | Development only |
| `lakehouse_integration/Dockerfile` | Development only |
| `lakehouse_integration/check_fabric.py` | Development only |
| `lakehouse_integration/steps.sh` | Development only |
| `pyproject.toml` | Development only |
| `requirements.txt` | Production only |
| `tests/streamlit/generator.py` | Development only |
| `uv.lock` | Development only |
| `web/app.js` | Present in both; differs |
