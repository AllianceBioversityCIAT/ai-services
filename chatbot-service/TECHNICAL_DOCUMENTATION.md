# Chatbot backend maintenance

This guide describes `main-chatbot-service`. See the [README](README.md) for setup and [API contract](docs/API.md) for payloads.

## Request flow

1. `api_server.py` launches `app.api.main:app`; `main.py` wraps the same application with Mangum for Lambda.
2. `app/api/main.py` mounts `interface/`, serves `/chatbot-ui`, exposes static metadata/health and includes the chat router.
3. `ChatRequest` validates message length and identifiers. The route lazily imports the agent and forwards request fields.
4. `run_agent_chatbot` builds metadata filters, includes applied filters in input text and invokes the configured Bedrock agent/alias.
5. Completion chunks are decoded as UTF-8 and accumulated into one JSON response. The browser displays the completed answer.

Filters are constructed before the generator's provider-call exception handler. Trace output is disabled. There is no structured citation field; citations generated in text remain in `message`. The accepted reload flag does not start a database refresh or ingestion, despite route response metadata.

## Change map

| Module | Responsibility |
| --- | --- |
| `app/api/models.py` | Request/response validation; coordinate caller/examples |
| `app/api/routes.py` | Lazy import, aggregation, errors and flag-derived reload metadata |
| `app/llm/agents.py` | Active AWS clients, invocation payload and generator errors |
| `app/utils/agents_utils/filter_builder.py` | KB metadata filter structure |
| `app/utils/config/config_util.py` | Environment/config dictionaries, including residual settings |
| `interface/chatbot_interface.html` | HTTP UI, fixed Lambda and production interaction URLs |
| `app/utils/logger/logger_util.py` | Console and `/tmp/logs/app.log`, 5 MiB rotation with five backups |
| `Dockerfile`, `requirements.txt`, `main.py` | Lambda image packaging, installed dependencies and handler |

## Retained helpers and absent tools

`app/utils/s3/upload_file_to_s3.py` uses the SDK credential chain and `BUCKET_NAME` for existence/upload helpers. `divide_jsonl_files.py` creates per-record CSV and metadata, uploads under `aiccra/chatbot/knowledge_base/` and deletes per-record temporary files. Line failures can be logged while processing continues. Neither helper is called by active chat; uploads do not prove KB ingestion completed.

`feedback_util.py` is unused and imports feedback model classes absent from current models. It is not a supported local feedback API. The HTML page sends interaction/feedback records to an external service.

This tree has no Streamlit entry point, SQL loader, conversion scripts, OpenAI CLI, direct KB/model/OpenSearch modules or full chatbot prompt template. Retained prompt files are not loaded by the active agent. SQL/OpenSearch configuration dictionaries and installed packages do not establish those implementations exist. Maintain the development tools on the development line.

## Configuration and lifecycle

The agent creates `bedrock-agent` and `bedrock-agent-runtime` clients with region only; requests use the runtime. Credentials come from the SDK chain, such as a deployment role, local profile or standard environment credentials (including a session token when required). S3 uses the same credential-chain approach. Do not reintroduce explicit development key arguments incidentally.

The API imports the agent lazily, so health/docs can work even if AWS client creation would fail. `.env` is loaded through python-dotenv; the HTML's URLs do not come from it. External agent configuration controls model, instructions, KB association and memory behavior.

## Installation and image behavior

Use Python 3.13 and requirements for local checks, as shown in the README. There is no manifest/uv lock here; dependencies are unpinned. Do not infer runnable Streamlit/OpenAI applications from retained package names.

The Lambda Dockerfile installs requirements into `LAMBDA_TASK_ROOT`, copies `.env` and the full context, and starts `main.handler`. Review build inputs for credentials or reporting artifacts. This packaging was inspected, not built/deployed during documentation validation.

## Offline verification

No dedicated service test suite is tracked here. Resolve local links and parse example JSON/Python/shell. Exercise Pydantic models, pure filters and API responses with a fake agent. Replace boto3 before agent import and block network; replace logging to avoid creating files. Extract the HTML script for syntax checking without executing fetch calls. Verify fixed destinations and compare complete trees with development.

Offline checks do not validate credentials, external agent/model/KB, freshness, feedback, Lambda or Jenkins. See the [branch comparison](docs/BRANCH_DIFFERENCES.md) for files intentionally absent from service-main and production settings to preserve.
