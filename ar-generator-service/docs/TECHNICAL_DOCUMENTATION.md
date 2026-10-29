# AICCRA local data and operations guide

This guide describes development's actual local execution path and the production differences that must be respected. Use the [README](../README.md) for commands and the [API guide](API_GUIDE.md) for request semantics.

## CSV inputs and data loading

The development loader is `db_conn/mysql_connection.py`. When USE_CSV_DATA is true/1/yes, it reads a filename from TABLE_CSV_FILES under CSV_DATA_DIR and immediately returns the DataFrame. It does not run the MySQL rename/drop/grouping logic on those CSVs. The current default directory resolves to service app/; the missing-file message's reference to service root is stale.

| Source view | Prepared CSV |
| --- | --- |
| vw_ai_project_contribution | vw_ai_project_contribution_ar.csv |
| vw_ai_questions | vw_ai_questions_ar.csv |
| vw_ai_deliverables | vw_ai_deliverables_ar.csv |
| vw_ai_oicrs | vw_ai_oicrs_ar.csv |
| vw_ai_innovations | vw_ai_innovations_ar.csv |
| vw_ai_challenges | vw_ai_challenges_ar.csv |

Prepare source-appropriate fields rather than copying arbitrary raw database exports. Important consumers include:

| Consumer | Fields/expectations |
| --- | --- |
| Summary/tables | indicator_acronym, numeric year, Milestone expected value, Milestone reported value; table overviews also use indicator_title, cluster_acronym, Milestone achieved narrative |
| Semantic metadata | source table supplied by ingestion, year string metadata, indicator_acronym, table_type, applicable role/status/phase fields |
| DOI retrieval | indicator_acronym, year, doi; metadata used to retain/deduplicate the evidence |
| Questions/disaggregation | Prepared question/contribution rows with indicator/year and the question/phase/table labels needed by filters/prompts |
| Challenges | Prepared challenge/lesson fields; current fetch helper loads all rows rather than filtering year |
| Business filters | table_type labels such as contributions/deliverables/questions/oicrs/innovations; exact status/role/phase values consumed in code |

Summary functions compare DataFrame year directly to the integer request; structured retrieval normalizes year to strings. Incorrect CSV types can therefore affect paths differently. A successful CSV read is not proof that summaries or filters have adequate fields/data.

When CSV mode is disabled, development uses MYSQL_DATABASE_URL and SQLAlchemy/MySQL connector. Its transformations differ from production and do not add every label provided by the SQL Server path. Load errors are logged and return an empty DataFrame, so a missing file/schema/column may manifest later as empty context or a pipeline error.

Production has a separate `db_conn/sql_connection.py` with pyodbc imported at module load. Its CSV branch exists, but does not remove the import/system-driver dependency. Its SQL path can create/alter views, transform/filter rows, write temporary exports, and upload to S3. Do not run that loader as a harmless read-only check.

## AWS and local configuration

The active shared AWS dictionary reads the OS-named key/secret and AWS_REGION. Both values are explicitly required by Bedrock initialization. Older BR aliases in historical examples do not configure that path. The updated development [.env.example](../.env.example) uses placeholders and CSV mode; it is not a production runtime configuration file.

S3_VECTORS_BUCKET_NAME and S3_VECTORS_INDEX_NAME must select intended resources. Client creation is lazy for the vector store; the bucket/index are validated when requested. The bucket is not created by the application. Index creation uses dimension 1024, cosine, float32, and non-filterable chunk_json metadata.

The locked SDK versions are recorded in uv.lock; do not replace them with an unverified minimum-version recommendation. Check installed support/request behavior deliberately if an SDK operation fails. No documentation review certifies live query limits, IAM permissions, or provider availability.

Ordinary S3, KB, Slack, Supabase, and SQL Server settings serve ancillary or alternate paths and are not all needed to serve health. API pipeline imports are lazy; process startup can pass even when generation configuration is missing. Restart after configuration changes because module dictionaries/cache clients retain values.

## Rebuild and ingestion

The two narrative pipelines conditionally call recreate_index, which deletes then creates the configured index. Mid-year ingests five views; annual adds challenges. Ingestion serializes row chunks, invokes embeddings, skips empty/failed embeddings, and writes vectors in batches. Some failures return zero rather than raising.

This is a full selected-index rebuild, with no transaction or verified concurrency guard. It is not limited to the request year/indicator. Do not use rebuild as routine health validation, or infer success from an ingestion-completed log without checking counts and the intended resource state. No rebuild or provider write is required to verify documentation.

## Active and retained modules

| Path | Status in the current development checkout |
| --- | --- |
| app/llm/vectorize.py, vectorize_annual.py | Active API pipelines, S3 Vectors |
| app/llm/opensearch/ | Retained source; imports OPENSEARCH config not currently defined by config_util.py |
| app/llm/supabase/ | Retained source; includes a missing report_generation_prompt module reference |
| app/llm/knowledge_base.py | Separate reference; expects config/prompt imports not provided by the current active config/layout |
| tests/streamlit/generator.py | Manual UI invoking generation; not an isolated regression test |
| lakehouse_integration/ | Separate Python 3.10 ODBC diagnostic image/script; not the FastAPI production image |

These are not verified rollback/feature switches. Review their actual imports, dependencies, provider settings, and effects before any separately scoped execution or restoration.

## Jobs and ancillary effects

Development retains host-cron setup scripts that can modify crontab and call live services. `update_ar_data.py` targets the production annual endpoint with insert_data enabled; `update_chatbot_data.py` references an HTTP route absent from current report routes. Some scripts treat long waits/timeouts as acceptance; this does not prove durable background execution or successful completion.

KB synchronization starts an AWS ingestion job and may send Slack notifications. Lakehouse diagnostics connect to SQL Server and print connection context. Do not run these tools as documentation/unit checks, and do not infer that a schedule is installed from a setup script or the browser's calculated Sunday badge.

Production replaces the local cron approach with `api_server.handler` plus `app/utils/jobs/scheduled_jobs.py`, supporting update_ar_data, update_chatbot_data, and sync_knowledge_base. The AR job currently fixes indicator IPI 1.3/year 2025 and enables rebuild; verify such constants before any intended operational change. The dispatcher is part of production behavior, not present in development's simple Mangum adapter.

## Files, logs, and testing

Development explicitly writes context_<indicator>_<year>.json in the current directory from narrative pipelines, in addition to rotating logs under data/logs. CSV mode does not suppress those files or cloud model calls. Production suppresses the explicit context-dump calls and uses /tmp/logs.

The six existing test functions target filtering/metadata behavior, but importing the S3 Vectors package normally also imports ingestion/data/provider dependencies. Their assertions do not validate SQL Server, MySQL connectivity, AWS, browser downloads, cron installation, real report quality, or deployment. Offline extension checks should block network, use temporary synthetic CSVs, and replace provider/data/logging dependencies before import.

The existing API/UI metadata and older production design documents contain historical OpenSearch/model/year claims. During service-main integration, update those guides to the resulting production tree while preserving useful architecture/onboarding content. Root repository licensing text is separate from API metadata; no licensing/runtime change is made by these guides.

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

Ordinary pytest collection remains dependent on the application's eager imports unless separately configured; a missing SQLAlchemy/provider configuration error during collection is distinct from a failed filter/schema assertion. No application/test implementation is changed by this documentation bootstrap.
