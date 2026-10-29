# Fast Response Service: agent guide

Read the [root guide](../AGENTS.md), [README](README.md), and relevant implementation before editing. These instructions describe `main-fast-response`, which writes logs to `/tmp/logs/app.log`. This is a small Python API with a single generation operation; do not import assumptions about retrieval, storage, or frontends from other services.

## Scope and branches

- Development: `dev-fast-response`; service-main: `main-fast-response`. Verify current references before integration.
- Prepare focused work from development. Maintainers handle development-to-service-main merges unless explicitly delegated. Keep shared guide changes separate from service work in commits/review.
- The active log location in this branch is `/tmp/logs`, including local execution; development uses service-relative `data/logs`. Preserve that intentional runtime difference and keep branch-specific documentation aligned after integration. See [comparison](docs/BRANCH_DIFFERENCES.md).
- A branch snapshots the whole monorepo. Review incoming commits/diffs before authorized integration; do not copy unrelated service changes or merge all of main merely to obtain docs.

## Implementation map

| Path | Responsibility |
| --- | --- |
| `api_server.py` | Local argparse/Uvicorn launcher; some help text still says AICCRA |
| `main.py` | Mangum `handler` for Lambda |
| `app/api/main.py` | FastAPI app, CORS, root/health routes, global errors, OpenAPI metadata |
| `app/api/models.py` | Request/response schemas |
| `app/api/routes.py` | Generation route, logging, 400/500 mapping |
| `app/llm/mining.py` | Prompt concatenation, import-time boto3 client, model call and parsing |
| `app/utils/config/config_util.py` | dotenv and AWS variable mapping |
| `app/utils/logger/logger_util.py` | Import-time file logging and stdout |
| `Dockerfile`, `requirements.txt` | Actual Lambda packaging/install path |
| `pyproject.toml`, `uv.lock` | Separate local dependency metadata/lockfile |

## Behavior to preserve

- `POST /api/fast-response` takes required string `prompt` and `input_text`. Current schemas accept empty strings and have no text-length limits; no route authentication/rate limit is implemented. Do not silently change validation, auth, or contracts in docs work.
- The provider receives exactly `f"{prompt}: {text}"` as one user text block. Prompt composition and model settings are behavior, including string-only edits.
- Model is `us.anthropic.claude-sonnet-4-6`; region is hardcoded `us-east-1`. `AWS_REGION` is read but does not override this client. There is no model-ID environment override.
- Request parameters are `max_tokens=4000`, temperature 0.1, and Anthropic messages version `bedrock-2023-05-31`. Return only the first content block's text; non-`end_turn` stop reasons log a warning without changing success status.
- SDK calls are synchronous inside an async route. SDK timeouts/retries are not an end-to-end SLA; do not describe streaming, background jobs, or bounded response times as implemented.
- Route exceptions use FastAPI's nested `detail` object. Declared `ErrorResponse` documentation does not remove that wrapper. Missing/wrong-typed fields normally produce 422; caught `ValueError` produces 400; other caught exceptions produce 500.
- Health does not invoke Bedrock. Importing the app constructs a provider client and creates the log directory/file, which can fail before health is available.

## Run and validate

Use Python 3.13 from `fast-response-service/`. Docker installs `requirements.txt`; use `python -m pip install -r requirements.txt` for the documented local path. A pip install does not consume `uv.lock`; inspect all declarations before any dependency change.

Local: `python api_server.py --host 127.0.0.1 --reload` or `python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload`. Lambda: `main.handler`.

No isolated service test suite or lint configuration was found. For offline verification, replace boto3 client construction before importing the app, block network, and avoid loading real `.env` data or writing service logs (use a temporary/stub logger). Exercise successful generation, exact composed payload, validation errors, exception wrappers, and nonterminal stop reasons using fake responses. Never claim a live model/deployment check from mocks.

For documentation-only changes, check local links, example syntax, source consistency, and the scoped Markdown diff. No build, model call, credential change, or deployment is needed for that validation.

## Packaging and external effects

The existing Dockerfile copies `.env` and the whole build context into the Lambda image. Git ignore patterns do not exclude Docker inputs. Record this behavior without copying secrets into examples or changing packaging in unrelated work.

The workflow under `.github/workflows/jenkins-trigger-fast-response.yml` triggers on push/PR targeting service-main and manual dispatch, with no docs path exclusion. No dev-branch workflow was found in the reviewed checkout; external Jenkins configuration is unknown. Do not push, merge, or deploy without the user's requested scope.

Logs include the full user prompt and model token/stop metadata. Keep credentials, real payloads, logs, generated artifacts, and virtual environments out of commits. The repository LICENSE is Apache 2.0 while API metadata says MIT; do not silently resolve that mismatch as a documentation cleanup.
