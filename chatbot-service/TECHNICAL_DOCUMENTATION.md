# Chatbot backend maintenance

This guide maps `dev-chatbot`. See the [README](README.md) for setup and [API contract](docs/API.md) for payloads.

## Request flow

1. `api_server.py` launches `app.api.main:app`; `main.py` wraps the same app with Mangum.
2. `app/api/main.py` mounts `interface/`, serves `/chatbot-ui`, exposes static metadata/health and includes the chat router.
3. `ChatRequest` validates message length and identifiers. The route lazily imports the agent and forwards all request fields.
4. `run_agent_chatbot` builds metadata filters, includes applied filters in the input text and invokes the configured Bedrock agent/alias.
5. Completion chunks are decoded as UTF-8. FastAPI joins them into JSON; Streamlit progressively displays them.

Filters are constructed before the generator's provider-call exception handler. Trace output is disabled. The API exposes no structured citation field; citations generated in text remain part of `message`.

## Change map

| Module | Responsibility |
| --- | --- |
| `app/api/models.py` | Request/response validation; coordinate callers and examples |
| `app/api/routes.py` | Lazy import, aggregation, nested HTTP errors and reload metadata |
| `app/llm/agents.py` | Active AWS clients, invocation payload and generator errors |
| `app/utils/agents_utils/filter_builder.py` | KB metadata filter structure |
| `app/utils/config/config_util.py` | Environment names and configuration dictionaries |
| `chatbot.py` | Direct-agent Streamlit UI and external interaction tracking |
| `interface/chatbot_interface.html` | HTTP UI, fixed URLs and external tracking |
| `app/utils/logger/logger_util.py` | Console and file logging |

## Auxiliary paths and side effects

These modules are not part of an active agent chat request:

| Path | Behavior and prerequisites |
| --- | --- |
| `app/llm/knowledge_base.py` | Direct `retrieve_and_generate_stream`; hardcoded inference-profile account/region/model need review before reuse |
| `app/llm/invoke_llm.py` | Titan v2 embeddings and direct Claude 3.7 invocation; does not set the Agent's model |
| `app/llm/vectorize_os.py` | Direct OpenSearch indexing/retrieval and LLM helpers; imports SQL loader and creates clients on import |
| `db_conn/sql_connection.py` | Uses pyodbc/ODBC Driver 18, can create/alter views, writes JSONL/CSV and invokes splitting/uploads; catches errors and can return an empty DataFrame |
| `app/utils/s3/divide_jsonl_files.py` | Creates per-record CSV and metadata, uploads both under `aiccra/chatbot/knowledge_base/`, deletes per-record files; logs/continues on line errors |
| `app/utils/s3/upload_file_to_s3.py` | S3 existence/upload helpers with explicit development AWS credentials |
| `jsonl_to_json.py` | Reads/writes hardcoded paths at import; not an inert library |
| `openai_chatbot.py` | Independent interactive OpenAI vector-store search and Responses experiment |
| `app/utils/feedback/feedback_util.py` | Unused local-file/S3 helper with missing feedback model imports |

SQL extraction and S3 upload do not establish that KB ingestion completed. The active agent reload block is commented out. API `insert_data=true` metadata does not demonstrate database or ingestion activity. `pyodbc` is not declared here; do not make auxiliary SQL a prerequisite of normal chat setup.

## Client lifecycle and configuration

Configuration loads on import. The active agent constructs `bedrock-agent` and `bedrock-agent-runtime` clients; requests invoke the runtime. Development passes access/secret keys explicitly and does not explicitly forward a session token. Review actual credential-provider behavior before adopting temporary credentials. Service-main uses the SDK credential chain for these clients.

API agent import is lazy; health/docs can work even if agent import would fail. Streamlit imports the agent at startup. Editing a prompt file does not change external agent instructions or its model.

## Offline verification

There is no dedicated tracked service test suite in this snapshot. Useful checks:

- Resolve local documentation links and parse fenced JSON, Python and shell examples.
- Exercise Pydantic models and pure filter construction with fictional values.
- Replace the agent generator before testing API aggregation/errors.
- Replace `boto3.client` before importing the agent to inspect invocation arguments with fake completion events.
- Block network and replace logging to avoid generated repository files.
- Extract the HTML script for syntax checking without executing fetch calls.

Offline checks do not validate credentials, deployed resources/models, metadata compatibility, freshness, feedback, SQL/ODBC, Lambda or Jenkins. Inspect the [branch inventory](docs/BRANCH_DIFFERENCES.md) and compare complete trees again after the local service-main merge, preserving production choices.
