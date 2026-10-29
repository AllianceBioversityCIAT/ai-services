# AICCRA production data and operations guide

This guide describes main-ar-generator's SQL Server, Lambda packaging, and operational effects. Use the [README](../README.md) for setup, the [API guide](API_GUIDE.md) for request semantics, and [branch differences](BRANCH_DIFFERENCES.md) before integration.

## SQL source loading and exports

The active loader is [db_conn/sql_connection.py](../db_conn/sql_connection.py), imported eagerly by routes and by production jobs/pipelines. pyodbc is imported at module load. ODBC Driver 18, Python dependencies, SQL service-principal settings and suitable source permissions are part of the production runtime.

load_data performs the following when CSV mode is false:

1. Connect through ODBC Driver 18 with SERVER, DATABASE, CLIENT_ID and CLIENT_SECRET, using the configured service-principal authentication string.
2. Create or alter all views in CREATE_VIEW_QUERIES, then commit. This is not a read-only retrieval helper.
3. Count/read the requested view and apply source-specific renames, column drops, year restrictions, grouping and table_type labels.
4. Write report-source JSONL/CSV in /tmp, upload to the ordinary S3 export bucket, and clean up those temporary files.

| Source view | Report transformation/use |
| --- | --- |
| vw_ai_project_contribution | Rename phase/year, retain 2025/2026, label contributions; totals and narratives |
| vw_ai_questions | Drop internal columns, retain 2025/2026, label questions; disaggregation |
| vw_ai_deliverables | Drop internal columns, retain 2025/2026, group by record/indicator/cluster, label deliverables |
| vw_ai_oicrs | Rename PDF/year, retain 2025/2026, group and label oicrs |
| vw_ai_innovations | Rename PDF, retain 2025/2026, group and label innovations |
| vw_ai_challenges | Label challenges; the current retrieval helper does not year-filter these rows |

The API accepts years 2021–2026, but the SQL report transforms do not guarantee source rows for every accepted year. Summary functions compare numeric year directly; structured retrieval normalizes year to a string. Correct data types and table labels affect totals and business rules.

Report exports use keys under aiccra/reports_generation/files/ with table_ar.jsonl and table_ar.csv names. Source/view/export failures can be logged and returned as an empty DataFrame, allowing downstream generation to fail or proceed with reduced evidence. insert_data:false does not suppress those loader effects.

load_full_data is a separate SQL source path for chatbot exports. It creates/alters views, performs its own broader transforms, uploads table JSONL/CSV under aiccra/chatbot/files/, and calls the per-record splitter. The splitter creates CSV and metadata sidecars under /tmp and uploads them; these are real data writes when invoked. Do not treat load_full_data as a no-effect metadata query.

## CSV inputs and data loading

USE_CSV_DATA enables an early prepared-CSV return in load_data only. It does not switch load_full_data, remove pyodbc imports, or skip startup-time S3/export dependencies. CSV_DATA_DIR defaults to app/; filenames are the six vw_ai_*_ar.csv mappings in the loader. The source's missing-file text saying service root is stale.

Prepared CSVs bypass SQL transforms/exports for load_data and must already contain fields required by their consumers. Contributions need indicator/year, numeric expected/reported values, and narrative/title/cluster fields where used. Other sources need appropriate table_type, DOI/question/role/status/phase fields for filters and prompts. A successful CSV read is not an evidence-completeness check.

For local work that cannot install pyodbc/native ODBC, use dev-ar-generator's CSV/MySQL implementation rather than changing production imports. Its transforms and side effects differ intentionally.

## AWS and production configuration

The production [.env.example](../.env.example) uses placeholders and USE_CSV_DATA=false. It is not a deployment operation or a copy of live Lambda settings.

| Client | Credential/configuration source |
| --- | --- |
| Bedrock Runtime | Explicit OS-named key/secret and AWS_REGION; guards require the keys |
| S3 Vectors | Same explicit OS-named key/secret and configured vector bucket/index/region |
| Ordinary S3 exporter | boto3 standard credential resolution and AWS_REGION; BUCKET_NAME selects export destination |
| Scheduled KB client | Tries the SDK credential chain first; construction-error fallback passes configured keys |
| SQL Server | ODBC Driver 18 and configured service-principal fields |
| Slack notifications | Optional SLACK_WEBHOOK_URL; missing configuration skips sending |

The KB client's constructor fallback is not a retry strategy for a later unauthorized API request. Do not assume OS-named keys configure every AWS client. No documentation check verifies live IAM, account/region access, SQL credentials, or provider quotas.

This branch installs requirements.txt and has no tracked lockfile. Review the actual built SDK version rather than inferring it from development's uv.lock or an unverified minimum. Vector bucket/index settings identify the resources used; the code creates/recreates the selected index, not the bucket.

FastAPI routes import SQL/export modules eagerly. api_server also imports scheduled jobs and annual-generation modules at startup. A health endpoint can therefore be unavailable because of native/import-time dependencies; a successful static health body still does not query sources or generate a report. Restart after configuration changes because module dictionaries/clients retain values.

## Rebuild and ingestion

Narrative insert_data:true deletes/recreates the whole selected vector index and ingests five mid-year or six annual source tables. Each load can trigger SQL view/export effects, and each row can require an embedding. Empty sources or failed embeddings may be skipped, and some errors return zero counts rather than raising.

Both narrative paths use the same configured resource. There is no documented rebuild transaction or concurrency guard. Rebuild is not a per-year refresh or routine health check. Capture deletion/creation/provider writes only in fakes for documentation validation.

## Active and retained modules

| Path | Current production status |
| --- | --- |
| app/llm/vectorize.py, vectorize_annual.py | Active S3 Vectors narratives/tables/challenges |
| app/s3_vectors/, app/retrieval/ | Active vector schema/ingestion and structured/semantic retrieval |
| db_conn/sql_connection.py | Active SQL Server loader and source exports |
| app/utils/jobs/scheduled_jobs.py | Active scheduler operations through api_server.handler |
| dev_server.py, main.py | Tracked auxiliary launchers/adapters, not the Docker command |
| Development OpenSearch/Supabase/KB reference modules | Absent here; not production feature switches |
| Development MySQL loader, cron/Streamlit/lakehouse tools, uv manifests | Absent here; use the development branch for those paths |

## Scheduled operations

api_server.handler classifies job-only events separately from Function URL/API Gateway-style events. A string job without HTTP event keys goes to execute_scheduled_job; HTTP-shaped requests go to Mangum with lifespan off. This routing is not an HTTP job-submission endpoint.

| Job | Current effects/limits |
| --- | --- |
| update_ar_data | Annual pipeline with fixed IPI 1.3/year 2025/insert_data:true; can alter/read/export SQL and rebuild vectors |
| update_chatbot_data | load_full_data on five source families, chatbot JSONL/CSV and per-record sidecars; partial-table success is possible |
| sync_knowledge_base | Starts a Bedrock ingestion job using configured KB/data-source IDs; returned job ID does not prove completed ingestion |

Jobs can attempt Slack notifications. Unknown job names return error status, which the hybrid wrapper maps to a 500-style Lambda response. A start/timeout/notification result is not evidence that the full data operation completed. No installed EventBridge schedule, cron state, real invocation, or pipeline run is established by reading this dispatcher.

## Packaging, files, and validation

The Dockerfile installs Python 3.13 dependencies and native ODBC support, then explicitly copies app/, db_conn/, web/, and api_server.py. Its command is api_server.handler. .dockerignore excludes .env and local/doc artifacts; live values belong to deployment configuration. dev_server.py and main.py are tracked but are not copied as image entry files.

This branch logs to /tmp/logs/app.log plus stdout and omits development's explicit context_<indicator>_<year>.json saves in active pipelines. SQL exports/per-record splitting use /tmp and ordinary S3. Logs, generated exports, and provider/error text may contain real reporting data and must stay out of commits/examples.

The six existing filter/schema assertions still need package-initialization isolation for provider-free collection. Normal imports of app.s3_vectors load ingestion and the SQL/provider stack. Their scope excludes ODBC installation, source permissions, AWS, real report quality, browser downloads, scheduler installation, and deployment. See the bootstrap below; it does not validate application startup.

Production's GitHub workflow targets pushes/PRs to main-ar-generator and manual dispatch, invoking ar-generator-pro-lambda without a documentation path exclusion. Only repository wiring is verified here. Root licensing text remains separate from API metadata; no licensing or runtime behavior is changed by these guides.

## Offline unit checks

From ar-generator-service/, in an environment with pytest and the schema dependencies (including pandas), this bootstrap runs the six existing assertions without executing the S3 Vectors package initializer. It preserves the actual filter/schema function code under test and blocks network connections. It does not validate package startup or provider imports.

```bash
python - <<'PY'
from pathlib import Path
import socket
import sys
import types
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path.cwd()))
import pytest

package = types.ModuleType("app.s3_vectors")
package.__path__ = [str(Path("app/s3_vectors").resolve())]
sys.modules["app.s3_vectors"] = package

def offline(*args, **kwargs):
    raise RuntimeError("Network blocked during isolated unit checks")

with patch.object(socket.socket, "connect", offline), patch.object(socket.socket, "connect_ex", offline):
    raise SystemExit(pytest.main([
        "-q", "-o", "cache_dir=/tmp/ar-generator-unit-cache",
        "tests/test_retrieval.py", "tests/test_vector_store_schemas.py",
    ]))
PY
```

Ordinary pytest collection remains dependent on the application's eager imports unless separately configured; a missing pyodbc/provider configuration error during collection is distinct from a failed filter/schema assertion. No application/test implementation is changed by this documentation bootstrap.
