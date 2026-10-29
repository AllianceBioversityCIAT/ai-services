# AI Insights backend

Python FastAPI backend for project-overview generation, cached-result retrieval, document deletion, and managed prompts. See the [service README](../README.md) for capabilities and the [API guide](../docs/API_GUIDE.md) for request examples.

## Local setup

Run from `ai-insights-service/backend/` with Python 3.13:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The Dockerfile installs this same requirements input. These requirements are unpinned; the checked-in `uv.lock` provides a separate resolved environment from `pyproject.toml`. For a deliberate lockfile workflow, use `uv sync --locked --python 3.13` and locked runs consistently. Do not assume an arbitrary pip installation reproduces the lockfile or a deployed image.

## Configuration

Create `.env` in this backend directory with values supplied by the team. This local example uses placeholders, not a deployed configuration:

```env
AWS_REGION=us-east-1
PROMPTS_BUCKET_NAME=example-insights-prompts
PROMPTS_PREFIX=ai-insights/prompts
INTERACTION_SERVICE_URL=https://your-analytics.example
CLARISA_VALIDATE_URL=https://your-clarisa.example/validate
IS_PROD=false
```

| Setting | Behavior |
| --- | --- |
| `PROMPTS_BUCKET_NAME` | Required non-blank configuration; prompt JSON storage |
| `PROMPTS_PREFIX` | Required non-blank configuration; surrounding slashes are removed |
| `INTERACTION_SERVICE_URL` | Configure before startup; the import-time analytics client expects a string URL |
| `CLARISA_VALIDATE_URL` | CLARISA key-validation endpoint for protected operations |
| `STAR_API_BASE_URL` | Optional STAR metadata API base; without it STAR enrichment is skipped |
| `STAR_API_TOKEN` | Optional fallback when the request has no `Access-Token` header |
| `AWS_REGION` | AWS client region, default `us-east-1` |
| `INSIGHTS_AWS_ACCESS_KEY_ID`, `INSIGHTS_AWS_SECRET_ACCESS_KEY` | Optional local static credentials, taking precedence over local `AWS_*` credential values |
| AWS profile/standard credential chain | Local fallback when static keys are not provided |
| `SLACK_WEBHOOK_URL` | Optional notification destination; leave unset to skip |
| `IS_PROD` | Labels notifications; does not select prompt buckets or STAR destinations |

In Lambda, client creation uses the execution role and ignores/removes app-specific `INSIGHTS_AWS_*` keys. The code preserves the runtime's AWS credentials. Keep secrets out of committed files and examples.

## Run and inspect

With configuration available and the virtual environment activated:

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

Alternatively, `python -m api.main` starts the application on `0.0.0.0:8000`. `main.py` exports the Lambda handler; it is not the local Uvicorn launcher.

```bash
curl http://localhost:8000/health
curl http://localhost:8000/openapi.json
```

Open [Swagger UI](http://localhost:8000/docs). Health and schema reads do not prove external access works.

## Container and deployment inputs

Build with this backend directory as the context:

```bash
docker build -t ai-insights-service .
```

The image uses the Lambda Python 3.13 base and starts `main.handler`. It does not run Uvicorn on port 8000. `.dockerignore` excludes `.env`, environments, docs, and the uv lockfile from the context; application configuration must be supplied separately.

`infrastructure/cloudformation/lambda-function.yaml` defines the Lambda/Function URL and IAM permissions. It initially supplies only `IS_PROD`; deployment must also supply the mandatory prompt settings and analytics URL before application startup. Function URL CORS is configured at that layer; the app adds its own CORS middleware only outside Lambda.

No automated test suite is included. See the [service validation notes](../README.md#validation-and-operations) and [agent guide](../AGENTS.md) before live checks. Review template permissions, resource parameters, and actual environment configuration without assuming that the template proves a running deployment.
