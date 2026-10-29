# Partner Request Support backend

FastAPI backend for institution matching, CLARISA request review/response, and automatic evaluation. Read the [API guide](../docs/API_GUIDE.md) before calling processing or maintenance routes, because several write to external systems.

## Local setup

Use Python 3.13 and run from `partner-request-support/backend/`:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Docker installs `requirements.txt` with pip. `pyproject.toml` is a separate local declaration; its dependency list currently omits `pika`, which the email module imports. Install from requirements for the documented execution path and do not silently rewrite manifests or lockfiles during a documentation change.

## Configuration

This README describes `main-partner-request-support`, whose cache constant and cache SQL select `partner_request_cache_prod`. Local execution retains that choice. Use the development branch for its test-cache defaults.

Create `.env` in this backend directory with values supplied for the intended environment. No template is included in this checkout. A minimal placeholder configuration is:

```env
SUPABASE_URL=https://your-supabase-project.example
SUPABASE_KEY=YOUR_SUPABASE_KEY
OPENAI_API_KEY=YOUR_OPENAI_KEY
CLARISA_API_URL=https://your-clarisa.example/institutions
CLARISA_PARTNER_REQUESTS_URL=https://your-clarisa.example/partner-requests
CLARISA_CREATE_URL=https://your-clarisa.example/partner-requests/create
CLARISA_RESPOND_URL=https://your-clarisa.example/partner-requests/respond
CLARISA_COUNTRIES_URL=https://your-clarisa.example/countries
CLARISA_INSTITUTION_TYPES_URL=https://your-clarisa.example/institution-types
CORS_ORIGINS=http://localhost:3000
```

| Setting | Purpose |
| --- | --- |
| `SUPABASE_URL`, `SUPABASE_KEY` | Required for the import-time Supabase client |
| `OPENAI_API_KEY` | Required for the import-time OpenAI client used for web research |
| `AWS_ACCESS_KEY_ID_BR`, `AWS_SECRET_ACCESS_KEY_BR` | AWS credentials supplied to embedding/translation clients; otherwise check the standard boto3 chain |
| `AWS_REGION` | Used by the web-research Bedrock client; embedding/translation/template clients explicitly use `us-east-1` |
| `CLARISA_API_URL` | Institution catalog synchronization source |
| `CLARISA_PARTNER_REQUESTS_URL` | Request listing/pending fetch and lookup before responses |
| `CLARISA_CREATE_URL`, `CLARISA_RESPOND_URL` | Upstream creation/response destinations |
| `CLARISA_COUNTRIES_URL`, `CLARISA_INSTITUTION_TYPES_URL` | Catalogs used to map names to creation codes |
| `CORS_ORIGINS` | Browser origins; defaults differ between development and service-main |
| `S3_TEMPLATE_BUCKET`, `S3_TEMPLATE_KEY` | Excel template location |
| `BEDROCK_RULES_MODEL_ID` | Optional override for automatic rules evaluation |
| `BEDROCK_DUPLICATE_CHECK_MODEL_ID` | Optional override for same-institution verification |
| `RABBITMQ_URL`, `EMAIL_QUEUE_NAME` | Optional email microservice queue configuration |
| `MS_AUTH_USER`, `MS_AUTH_PASSWORD`, `EMAIL_SENDER`, `EMAIL_SENDER_NAME` | Email service authentication and sender metadata |
| `PRMS_ADMIN_NOTIFICATION_EMAIL` | Optional comma-separated admin recipients for manual-review notifications |

Treat the example URLs as placeholders. External CLARISA field/catalog requirements and authentication must be confirmed for the environment; the current client behavior is not proof of an external API's full contract.

Without RabbitMQ configuration, notifications are logged/simulated. With configuration, the service publishes email requests; a queued message is not proof of delivered email. Keep real credentials and requester data out of commits and examples.

## Run locally

```bash
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

`python api.py` also launches Uvicorn on `0.0.0.0:8000`. `main.py` exports the Lambda `handler`; it is not the local launcher. Open [Swagger UI](http://localhost:8000/docs) or [ReDoc](http://localhost:8000/redoc).

```bash
curl http://localhost:8000/health
```

Health returns process status without testing Supabase, CLARISA, model access, or email delivery. Module imports construct Supabase, OpenAI, and AWS clients, so missing configuration can fail before a route is available.

## Database and operational setup

The SQL files under `sql/` define the institution vector table/RPCs and the branch-specific cache table. Review and provision them deliberately in the intended database; initialization/synchronization is not a harmless smoke test. The cache SQL also creates a trigger and is not simply a universally repeatable migration.

- [Institution vector schema](sql/create_clarisa_vector_table.sql)
- [Production cache schema](sql/create_partner_cache_table.sql)

`src/populate_clarisa_db.py` populates/synchronizes institutions, creates embeddings, and can remove obsolete rows. Processing endpoints also perform synchronization with `delete_obsolete=True`. Confirm data ownership and intended environment before live execution.

The active cache constant in this service-main branch is `partner_request_cache_prod`; development selects `partner_request_cache_test`. `POST /api/clear-cache` clears the selected cache and is not a read-only readiness check.

## Deployment and validation

Build with the backend directory as context:

```bash
docker build -t partner-request-support .
```

The image uses Lambda Python 3.13 and starts `main.handler`. `template.yaml` defines a SAM Lambda/HTTP API deployment. These files do not establish the current running image, credentials, or Jenkins implementation. The frontend is a separate static-export deployment.

The scripts in `test/` perform real searches; they are examples, not an isolated test suite. For offline validation, replace external integrations before importing/invoking routes. Do not run a catalog sync, cache purge, request creation/response, or email operation solely to validate prose.

Locally, logs rotate in `backend/data/logs/app.log`; Lambda logs go to stdout/CloudWatch. Match and request data can appear in logs. See the [architecture guide](../docs/HIGH_LEVEL_DESIGN.md) for state, scoring, and side effects.
