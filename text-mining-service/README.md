# Text Mining Service

FastAPI and MCP service for four extraction workflows: STAR document mining, PRMS multisource extraction, AICCRA document mining, and STAR Bulk CapDev. A separate Next.js application supports reviewing and submitting bulk records to STAR.

This README describes the development tree based on `dev-text-mining`. Service-main has deliberate differences, including removal of the legacy bulk-upload interface. See [branch differences](docs/BRANCH_DIFFERENCES.md) before integration. Deployed availability and pipeline results require separate verification.

## Start here

| Goal | Read |
| --- | --- |
| Understand the four workflows | [Product overview](docs/PRODUCT_OVERVIEW.md) |
| Integrate HTTP endpoints and decode responses | [API guide](docs/API_GUIDE.md) |
| Integrate PRMS sources and MDS-shaped results | [PRMS integration guide](docs/prms-integration-guide.md) |
| Follow implementation components | [High-level design](docs/HIGH_LEVEL_DESIGN.md) |
| Run the Bulk Upload frontend | [Frontend README](frontend/README.md) |
| Continue work with a coding agent | [Service guide](AGENTS.md), [frontend guide](frontend/AGENTS.md) |

## Four workflows

| Workflow | HTTP endpoint | MCP tool | Input |
| --- | --- | --- | --- |
| STAR | `POST /star/text-mining` | `process_document` | One S3 document or uploaded file |
| PRMS | `POST /prms/text-mining` | `process_document_prms` | Existing S3 documents/audio and/or inline text |
| AICCRA | `POST /aiccra/text-mining` | `process_document_aiccra` | One S3 document or uploaded file; optional custom prompt |
| STAR Bulk CapDev | `POST /star/mining-bulk-upload/capdev` | `process_document_capdev` | Capacity Development spreadsheet; optional row IDs to skip |

STAR and Bulk CapDev use a CLARISA `X-API-Key` at the HTTP layer and STAR token validation inside MCP. Bulk CapDev also checks roles. PRMS uses CLARISA only. The AICCRA route accepts optional token fields but currently does not validate them in its MCP tool. See [API authentication](docs/API_GUIDE.md#authentication).

## Backend setup

Use Python 3.13 and run from `text-mining-service/`. Install `uv` before these steps.

```bash
uv venv
source .venv/bin/activate
uv pip install -r pyproject.toml
```

This installs the local dependency declarations. For an environment based on the checked-in lockfile, use `uv sync --frozen` and then `uv run --frozen ...` consistently. Some optional local dependencies, such as `psycopg2`, may require system build libraries.

The Lambda Dockerfile installs `requirements.txt` with pip. These dependency sources are currently different: the development lockfile contains LanceDB 0.21.2, while `requirements.txt` pins 0.36.0; `pyproject.toml` leaves LanceDB unpinned. Choose the environment deliberately and report which was tested. Updating documentation does not reconcile dependencies.

### Configuration

Create a local `.env` in the service directory using values supplied for your environment. Do not commit it.

```env
AWS_REGION=us-east-1
CLARISA_VALIDATE_URL=https://your-clarisa.example/validate
IS_PROD=false
STAR_BUCKET_KEY_NAME=star/text-mining/files/test
PRMS_BUCKET_KEY_NAME=prms/text-mining/files/test
AICCRA_BUCKET_KEY_NAME=aiccra/text-mining/files/test
```

The URL is a placeholder. AWS credentials must be available to boto3, such as through a profile or deployed role. The shared Bedrock provider also reads `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` when supplied.

| Setting | Purpose |
| --- | --- |
| `CLARISA_VALIDATE_URL` | Validation endpoint for CLARISA-protected HTTP routes |
| `STAR_BUCKET_KEY_NAME`, `PRMS_BUCKET_KEY_NAME`, `AICCRA_BUCKET_KEY_NAME` | Product upload/reference prefixes; the request supplies the bucket |
| `MAPPING_URL` | Staff/institution mapping integration |
| `IS_PROD` | Chooses production/test DynamoDB table names and notification labels |
| `SLACK_WEBHOOK_URL` | Optional notifications; leave unset to skip them |
| `CLIENT_ID`, `CLIENT_SECRET` | Credentials encoded by the UI token helper; not CLARISA API keys |
| `MS_NAME` | Authentication-notification service label |
| `PRMS_AUDIO_TRANSCRIBER` | Set `amazon_transcribe` to enable PRMS audio; disabled by default |
| `PRMS_MAX_AUDIO_SECONDS` | Optional duration limit; no limit configured by default |

PRMS limits and configurable defaults are detailed in the [integration guide](docs/prms-integration-guide.md#61-limits-summary). Audio requires access to Amazon Transcribe and the S3 media. Text-only PRMS requests do not require a request bucket, but still use Bedrock and may invoke mapping.

The main Bedrock provider uses Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6`) with the configured AWS region. The embedding client uses Titan Text Embeddings V2 in `us-east-1`; not every AWS client follows `AWS_REGION`.

### Start locally

```bash
uv run python -m app.mcp.client
```

Open [Swagger UI](http://localhost:8000/docs) or [ReDoc](http://localhost:8000/redoc). The module starts Uvicorn on port 8000. Run it from the service directory so relative static-interface paths resolve.

The HTTP app starts MCP subprocess sessions when processing requests. `main.py` is the Lambda adapter (`main.handler`), not the local server launcher. No `/health` route is defined in this branch.

Importing the HTTP app attempts to verify/create the bulk-upload DynamoDB table. Starting the server can therefore contact AWS before a mining request. Use a development environment and intentional configuration for live checks.

## Interfaces and auxiliary routes

| Surface | Location / routes | Notes |
| --- | --- | --- |
| AICCRA static UI | `interface/aiccra_mining/`, `GET /ui` | Present in development and service-main snapshots |
| Legacy Bulk Upload UI | `interface/bulk_upload/`, `GET /bulk-upload` | Present in development; absent in the reviewed service-main snapshot |
| Next.js Bulk Upload | `frontend/` | Separate process/deployment; see its [README](frontend/README.md) |
| Status tracking | `/dynamo/bulk-upload-records/...` | Reads/updates complete, failed, links, and record metadata |
| Feedback | `POST /feedback`, `GET /feedback/{interaction_id}` | External interaction-service integration |
| S3/UI helpers | `/list-s3-objects`, `/s3/list`, `/s3/download-template`, `/api/auth/token` | See the [API guide](docs/API_GUIDE.md#auxiliary-routes) for behavior and access distinctions |

DynamoDB tables are `bulk_upload_records` and `ai-requests-prod` when `IS_PROD=true`, otherwise `bulk_upload_records_test` and `ai-requests-testing`. The code does not establish authentication on every auxiliary route; do not infer access controls from the frontend login.

## Validation

An automated PRMS suite exists under `tests/prms/`. With the development environment installed:

```bash
uv run pytest tests/prms/unit -q
uv run pytest tests/prms/api -q
```

Inspect tests and configuration before running them. Unit scenarios mock external work where needed. API tests import the application, whose startup can attempt DynamoDB access; mocking individual requests does not suppress that import-time behavior. Use isolated credentials and stub external clients for offline checks. These tests do not establish production model quality.

For frontend checks, follow [frontend validation](frontend/README.md#validation). Do not run production builds during interactive frontend development unless explicitly requested.

For documentation changes, verify links, shell syntax, route names, request examples, and branch differences. Live mining can upload data, invoke paid models, send Slack messages, and record analytics.

## Deployment and integration

The Dockerfile uses AWS Lambda Python 3.13 and starts `main.handler`. It explicitly copies `.env` before copying the service tree, so inspect the build context and how deployment supplies configuration; do not add secrets to version control. This image does not start an ordinary Uvicorn server.

```text
task branch from dev-text-mining
    → dev-text-mining → main-text-mining → staging → main
```

The maintainer handles the development-to-service-main merge. After the local merge and before push, compare service files, route declarations, static interfaces, dependency inputs, and environment destinations. Adapt service-main documentation to its actual tree rather than assuming it matches development.

Jenkins triggers depend on the workflow version in each branch. Development has a backend push trigger for `dev-text-mining` and a separate frontend trigger. The reviewed service-main backend workflow targets `main-text-mining`; an older workflow still mentions `dev-lambda` in development. See [branch differences](docs/BRANCH_DIFFERENCES.md) rather than copying workflow names between branches.

## Operations and maintenance

Logs write to the console and `/tmp/logs/app.log`, with 5 MB rotation and five backups. LanceDB processing tables are under `/tmp/miningdb`. Avoid committing logs, source documents, transcripts, or temporary databases.

Model output and metadata can appear in logs. Static OpenAPI prose and some analytics labels still mention older model versions; inspect the shared provider for the current invoked model. This documentation update does not change those code paths.

See [high-level design](docs/HIGH_LEVEL_DESIGN.md) for failure behavior and [branch differences](docs/BRANCH_DIFFERENCES.md) for the service-main review checklist.
