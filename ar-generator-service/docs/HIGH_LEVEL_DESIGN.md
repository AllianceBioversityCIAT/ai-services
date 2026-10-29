# AICCRA Report Generator design

This is the implemented production design on main-ar-generator, with the local-development boundary called out explicitly. The [README diagram](../README.md#system-architecture) and [API guide](API_GUIDE.md) provide the call flow and public contract.

## Purpose and components

The service converts AICCRA structured reporting evidence into indicator narratives, summary tables, and cross-cluster challenges/lessons content. It provides one FastAPI app and a static review interface. Generated material requires source review; neither a model response nor the interface establishes official report approval.

| Component | Current responsibility |
| --- | --- |
| HTTP/UI | FastAPI route orchestration, request models, static mounting |
| Source loader | Active SQL Server/Fabric transformations/exports; optional prepared CSV override in load_data only |
| Ingestion | Row chunks, Titan embeddings, metadata records, selected-index rebuild |
| Vector retrieval | S3 Vectors semantic query with indicator/year/source-table filters |
| Structured retrieval | DOI, question/contribution, and challenge evidence without vector similarity |
| Business rules | Shared/cancelled/phase/question exclusions and DOI deduplication |
| Generation | Claude narrative synthesis, cluster drafts/editorial passes, table overviews |
| Scheduled operations | Hybrid Lambda dispatcher, AR refresh/chatbot export/KB sync, Slack notifications |

## Production entry and data path

The Dockerfile installs ODBC/Python requirements, copies the production modules/assets, and starts api_server.handler. That hybrid entry point classifies HTTP-shaped events for Mangum and job-only events for the scheduler dispatcher. dev_server.py remains available in the checkout as an auxiliary local launcher but is not copied as the image entry point.

FastAPI routes eagerly import the SQL/export stack; api_server additionally imports scheduled jobs and the annual pipeline. Lazy report function helpers do not make the packaged app independent of startup-time SQL/AWS dependencies.

The SQL loader imports pyodbc, connects through ODBC Driver 18 with service-principal settings, creates/alters reporting views, reads source rows, and applies source-specific transforms/table_type labels. Several reporting tables are limited to 2025/2026. It writes report-source CSV/JSONL under /tmp and uploads to ordinary S3. load_full_data separately builds broader chatbot exports and per-record CSV/metadata files.

A prepared-CSV branch exists only in load_data; it returns rows before SQL processing/export and does not remove import dependencies. load_full_data does not use that override. Development's MySQL/CSV implementation, alternate providers, cron/manual tools, and uv manifests are not part of this production tree.

## Vector storage and retrieval

The active store is Amazon S3 Vectors, not the retained OpenSearch code. Index configuration uses float32 vectors, dimension 1024, cosine distance, and `chunk_json` as a non-filterable metadata key. Other metadata includes source table, string year/indicator, phase/status/role labels, and has_doi where applicable.

A vector record uses a table/row-position key, a Titan embedding, filterable metadata, and serialized chunk JSON. Query results are reconstructed from that JSON. The semantic helper requests top_k=10000 by default; local tests do not establish acceptance of its request settings or completeness under live provider limits.

Rebuild deletes/recreates the selected index and ingests all configured tables. Empty sources and failed embeddings can be skipped. There is no transaction, dedicated per-request index, or concurrency guard around this destructive path. Do not describe insert_data as a harmless refresh or a year-only update.

## Report flows

### Mid-year

Contribution totals use sums. The report combines semantic candidates from four source families with structured DOI rows, deduplicates by DOI/cluster/indicator, and excludes Shared deliverables/innovations. It builds a prompt without development's explicit context JSON save call, and generates one narrative. Oversized-input contingencies remove unsuitable deliverables and later cap selected context categories; non-input errors can be swallowed into a None pipeline result.

### Annual

Annual context separates semantic evidence from structured question/contribution evidence. Business filters exclude specified Shared/cancelled rows and AWPB/Progress phases. Totals use means for IPI 2.2 and IPI 3.3, otherwise sums. The pipeline generates a summary and per-cluster draft/editorial passes using a ThreadPoolExecutor, then adds disaggregated target content for selected indicators. Cluster failures can appear as prose inside an otherwise returned report.

### Tables and challenges

Tables load structured contribution data for the year, group indicators by PDO/IPI family, calculate targets/achievements, and generate brief overviews where narratives exist. The implementation returns four current column types rather than every historical projected-target field mentioned in older docs.

Challenges load the full challenges source. The helper does not apply a year filter, even though a year is used in the prompt/response. No-data and caught-error cases can return explanatory prose that the route marks success.

See [API failure semantics](API_GUIDE.md#responses-and-failure-semantics) before interpreting any HTTP success as a validated report.

## Provider and configuration boundaries

Active Bedrock and S3 Vectors use the shared OS-named key/secret dictionary and AWS_REGION. Bedrock guards require both explicit values before client construction. Titan Text Embeddings V2 provides embedding text; active Claude generation uses Sonnet 4.5 with temperature 0.1 and max tokens 8000. Internally streamed deltas are accumulated; public endpoints return complete JSON.

Model/region/prompt/criteria changes are behavior changes. A model ID in a source file is not proof of access, output quality, latency, or live quotas. Ordinary S3 export authentication differs between branches: development passes the explicit shared credentials; production's exporter leaves credential resolution to boto3's chain.

## Runtime, UI, and state

The static UI currently sends generation to a fixed production Lambda base and analytics to a separately configured host. Serving it locally does not route those calls to the local API. Tracking can include identity parameters and generated output; the browser date badge is calculated, not an observed ingestion status.

This branch omits the explicit development context-dump calls and uses /tmp/logs/app.log plus stdout, with logger name ar-generator-service. SQL/export operations use /tmp for intermediate data and ordinary S3 for their configured destinations. Development instead writes context JSON and service-relative logs. Neither the HTTP API nor those files provide a durable job lifecycle or a validated reporting evidence database.

The app has no general route authentication dependency. CORS and metadata descriptions do not establish infrastructure authorization. The API's metadata also contains historical technology/year/license statements; current source and the repository license file are separate evidence.

## Scheduling, packaging, and development boundary

The current tree contains the SQL Server/pyodbc loader, ODBC-enabled Lambda image, requirements file, .dockerignore, hybrid `api_server.handler`, scheduler job dispatcher, and export helper. Its loader can create/alter all reporting views, transform/filter data, and export CSV/JSONL to S3. A read-style generation call may therefore write external resources even with insert_data:false.

The hybrid handler distinguishes supported scheduler events from HTTP-shaped events. Job implementations refresh AR data, export chatbot source data, or start KB ingestion; notifications may be sent to Slack. Those jobs are not the local host-cron tools retained only in development. Do not run real jobs as unit tests. Starting a KB ingestion job is distinct from verifying completion.

The maintainer's workflow uses the separate development branch for local testing rather than a separate test Lambda. The production image excludes .env/local artifacts and uses explicitly selected copy instructions; live configuration belongs to deployment settings. Preserve the complete [branch matrix](BRANCH_DIFFERENCES.md) and adapt production documentation after the local merge. Repository code does not verify deployed schedules, infrastructure triggers, or running versions.

## Validation

Six existing assertions cover chunk metadata, DOI deduplication, and post-filters, but package initialization pulls in data/provider imports during ordinary test collection. Use the technical guide's offline bootstrap for isolated execution. Offline route/data/provider checks should block network, use temporary fictional CSVs, stub provider/data/logging before import, and capture rebuild operations only in fakes. Live SQL/view/export operations, S3 Vectors writes, model calls, browser analytics, cron installation, and deployment are separate deliberate activities.
