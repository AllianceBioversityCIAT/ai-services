# Text Mining Service

FastAPI and MCP service for four extraction workflows: STAR document mining, PRMS multisource extraction, AICCRA document mining, and STAR Bulk CapDev. A separate Next.js application supports reviewing and submitting bulk records to STAR.

This README describes `main-text-mining`. It includes the four extraction workflows, the AICCRA static interface, and the Next.js Bulk Upload application. The legacy `/bulk-upload` HTML interface is absent from this branch. See [branch differences](docs/BRANCH_DIFFERENCES.md) for preserved development/production differences. Deployed availability and pipeline results require separate verification.

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

Use Python 3.13 and run from `text-mining-service/`. The commands below use the same dependency input as the Lambda Dockerfile:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

This selects the dependency declarations used for Lambda packaging. It does not reproduce the entire Lambda runtime or prove a fresh installation/deployment works. `pyproject.toml` also contains optional local dependencies such as `psycopg2`, which may require system build libraries.

`requirements.txt`, `pyproject.toml`, and `uv.lock` all select LanceDB 0.36.0. The lockfile is valid and passes `uv lock --check --offline` against `pyproject.toml`. Docker installs `requirements.txt` with pip; it does not use the uv lockfile to install dependencies. Other unpinned dependencies can still resolve differently between these workflows, so report the environment actually tested. The setup below follows the Lambda requirements; no fresh installation or Docker build was performed during this documentation review.

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

This is a local test configuration example, not a description of deployed production values. The URL is a placeholder. AWS credentials must be available to boto3, such as through a profile or deployed role. The shared Bedrock provider also reads `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` when supplied.

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
python -m app.mcp.client
```

Open [Swagger UI](http://localhost:8000/docs) or [ReDoc](http://localhost:8000/redoc). The module starts Uvicorn on port 8000. Run it from the service directory so relative static-interface paths resolve.

The HTTP app starts MCP subprocess sessions when processing requests. `main.py` is the Lambda adapter (`main.handler`), not the local server launcher. No `/health` route is defined in this branch.

Importing the HTTP app attempts to verify/create the bulk-upload DynamoDB table. Starting the server can therefore contact AWS before a mining request. Use a development environment and intentional configuration for live checks.

## Interfaces and auxiliary routes

| Surface | Location / routes | Notes |
| --- | --- | --- |
| AICCRA static UI | `interface/aiccra_mining/`, `GET /ui` | Present in this branch; its JavaScript targets the service-main backend |
| Next.js Bulk Upload | `frontend/` | Separate process/deployment; see its [README](frontend/README.md) |
| Status tracking | `/dynamo/bulk-upload-records/...` | Reads/updates complete, failed, links, and record metadata |
| Feedback | `POST /feedback`, `GET /feedback/{interaction_id}` | External interaction-service integration |
| S3/UI helpers | `/list-s3-objects`, `/s3/list`, `/s3/download-template`, `/api/auth/token` | See the [API guide](docs/API_GUIDE.md#auxiliary-routes) for behavior and access distinctions |

The legacy `/bulk-upload` route and `interface/bulk_upload/` assets are not available here; they remain development-only. The Next.js frontend and `/star/mining-bulk-upload/capdev` extraction endpoint are present. Its constants use `star/text-mining/files/prod/bulk_upload/` and production STAR result links; verify environment values before live work.

DynamoDB tables are `bulk_upload_records` and `ai-requests-prod` when `IS_PROD=true`, otherwise `bulk_upload_records_test` and `ai-requests-testing`. The code does not establish authentication on every auxiliary route; do not infer access controls from the frontend login.

## Validation

An automated PRMS suite exists under `tests/prms/`. With the chosen virtual environment activated:

```bash
python -m pytest tests/prms/unit -q
python -m pytest tests/prms/api -q
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

In this branch, `.github/workflows/jenkins-trigger-ai-text-mining.yml` targets pushes and pull requests to `main-text-mining`. The separate frontend production workflow targets pushes to `main-text-mining`. The development-specific backend workflow is absent here. These triggers do not exclude documentation-only changes; inspect actual workflow contents before a push.

## Operations and maintenance

Logs write to the console and `/tmp/logs/app.log`, with 5 MB rotation and five backups. LanceDB processing tables are under `/tmp/miningdb`. Avoid committing logs, source documents, transcripts, or temporary databases.

Model output and metadata can appear in logs. Static OpenAPI prose and some analytics labels still mention older model versions; inspect the shared provider for the current invoked model. This documentation update does not change those code paths.

See [high-level design](docs/HIGH_LEVEL_DESIGN.md) for failure behavior and [branch differences](docs/BRANCH_DIFFERENCES.md) for the service-main review checklist.

## Retained product references

This branch also contains older STAR/AICCRA product and design documents. Their introductions identify them as historical references and link to the current guides; their model versions and performance descriptions should not be treated as verified runtime facts.

- [AICCRA technical reference](docs/AICCRA_TEXT_MINING_DOCUMENTATION.md)
- [AICCRA design reference](docs/AICCRA_Text_Mining_SDD.md)
- [STAR product reference](docs/STAR_Text_Mining_Product_Overview.md)
- [STAR design reference](docs/STAR_Text_Mining_SDD.md)
