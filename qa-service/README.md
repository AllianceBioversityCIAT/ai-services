# PRMS QA Service

FastAPI service for two PRMS workflows: improving result metadata with AI Review and assessing W3/Bilateral results with traffic-light verdicts. Both use AWS Bedrock Claude Sonnet 4.6 and can read supporting evidence.

This documentation describes the code in this branch. Deployment availability and frontend behavior must be checked in the target environment.

## Start here

| Goal | Documentation |
| --- | --- |
| Understand the workflows and their limits | [Product overview](docs/PRODUCT_OVERVIEW.md) |
| Run the service locally | [Local setup](#local-setup) |
| Integrate either endpoint | [API guide](docs/API_GUIDE.md) |
| Follow the implementation and dependencies | [High-level design](docs/HIGH_LEVEL_DESIGN.md) |
| Explore source-specific evidence extraction | [Web scraping reference](app/web_scraping/WEB_SCRAPING_DOCUMENTATION.md) |

## Endpoints

| Method | Path | Purpose | Application authentication |
| --- | --- | --- | --- |
| POST | `/api/prms-qa` | Improve metadata and review impact-area scores | No active authentication dependency on this route |
| POST | `/prms/quality-assessment` | Return overall, section, and evidence verdicts | `X-API-Key`, validated through CLARISA |
| GET | `/` | Service information | None |
| GET | `/health` | Process health response | None |
| GET | `/docs`, `/redoc`, `/openapi.json` | Generated API documentation | None |

These are application routes. Any additional gateway or infrastructure access controls are environment-specific. `/health` does not verify Bedrock access, authentication connectivity, or evidence retrieval.

## Local setup

Run these commands from `qa-service/`.

### 1. Install dependencies

Use Python 3.13 and AWS credentials with permission to invoke the configured Bedrock model.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Chromium is used by the evidence scraper. Additional operating-system libraries may be needed for Playwright on Linux.

### 2. Configure the environment

Create a local `.env` file in `qa-service/` with the authentication endpoint supplied by the team:

```env
CLARISA_VALIDATE_URL=https://your-authentication-service.example/validate
IS_PROD=false
WEB_SCRAPING_DOWNLOAD_DIR=/tmp/evidence_downloads
```

The URL above is a placeholder. The application refuses to start if `CLARISA_VALIDATE_URL` is absent, even when only using the metadata-improvement endpoint.

| Setting | Use |
| --- | --- |
| `CLARISA_VALIDATE_URL` | Required CLARISA API-key validation endpoint |
| AWS credentials | Standard boto3 credential chain, such as a local AWS profile or the deployed IAM role |
| `WEB_SCRAPING_DOWNLOAD_DIR` | Optional download directory; defaults to `/tmp/evidence_downloads` |
| `SLACK_WEBHOOK_URL` | Optional notification destination; leave unset to skip notifications |
| `IS_PROD` | Labels Slack notifications as production when `true`; does not select the Bedrock model or region |

Both Bedrock clients currently use `us-east-1` and model ID `us.anthropic.claude-sonnet-4-6` in code. Changing `AWS_REGION` alone does not change these clients. Keep credentials and webhook values outside version control.

### 3. Start and check the server

```bash
python api_server.py --reload
```

Open [Swagger UI](http://localhost:8000/docs) or [ReDoc](http://localhost:8000/redoc). Basic checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/
```

The server defaults to `0.0.0.0:8000`. Use `--port 8001` for another port or `--log-level debug` for additional server output. See `python api_server.py --help` for options.

Use the complete request examples in the [API guide](docs/API_GUIDE.md). The older minimal title/description payload omits impact-area fields that the metadata workflow reads directly.

## Repository structure

```text
qa-service/
├── api_server.py                 # Local Uvicorn entry point
├── main.py                       # Lambda handler: main.handler
├── Dockerfile                    # Lambda Python 3.13 container
├── requirements.txt              # Dependencies installed by the Dockerfile
├── pyproject.toml                # Project metadata and dependencies
├── uv.lock
├── app/
│   ├── api/                     # FastAPI app, routes, request/response models
│   ├── llm/                     # Metadata improvement, assessment, Bedrock calls
│   ├── utils/
│   │   ├── assessment/          # Criteria, rules, contract, scoring, suggestions
│   │   ├── prompt/              # Prompt builders and assessment tool schemas
│   │   ├── config/
│   │   ├── interactions/
│   │   ├── logger/
│   │   ├── notification/
│   │   └── s3/
│   └── web_scraping/            # Shared evidence retrieval and formatting
├── docs/                        # Product, API, and architecture documentation
└── tests/                       # Deterministic and stubbed assessment checks
```

## Validation

With dependencies installed, run the existing assessment checks from `qa-service/`:

```bash
python tests/test_assessment_rules.py
python tests/test_assessment_e2e.py
```

The second script stubs Bedrock and scraping for its assessment scenarios; it is not a live deployment check. Its imports initialize AWS clients and application routes, so local AWS configuration and `CLARISA_VALIDATE_URL` may still be needed.

`tests/stress_test.py` sends concurrent requests to a hardcoded remote URL. Review its destination and data before deliberately running it; it is not part of the local checks above.

## Deployment and branch workflow

The Dockerfile uses the AWS Lambda Python 3.13 base image, installs dependencies and Chromium, and starts `main.handler` through Mangum.

```bash
docker build -t prms-qa-service .
```

This is a Lambda image. It does not start a Uvicorn server on port 8000; use `api_server.py` for local HTTP development. AWS resources, environment values, and Jenkins configuration must be checked in the target environment.

QA follows this integration path:

```text
documentation or feature branch from dev-qa
    → dev-qa → main-qa → staging → main
```

Keep QA-specific documentation alongside QA code. Before promoting a branch, review the complete diff, including pending code and environment differences. Documentation should describe the version of the code in its branch.

The repository's QA workflows trigger Jenkins on pushes and pull requests targeting `dev-qa` and `main-qa`, including documentation-only changes. The workflows call `qa-service-dev` and `qa-service`, respectively; they do not contain the Jenkins deployment implementation.

## Operations and troubleshooting

| Symptom | Check |
| --- | --- |
| Startup fails with `CLARISA_VALIDATE_URL is not configured` | Set the URL before starting the application |
| Assessment authentication fails | Send `X-API-Key`; verify CLARISA connectivity and access to `AI Traffic Light - PRMS` |
| HTTP 400 `CONTRACT_VIOLATION` | Match result types, form labels, and vocabulary in the [API guide](docs/API_GUIDE.md) |
| Bedrock access or throttling errors | Verify AWS credentials, model permissions, and quotas for `us-east-1` |
| Evidence remains grey or assessment is partial | Inspect per-item reasons, `coverage`, and scraper logs; some sources require access or cannot be extracted |
| Chromium cannot launch | Confirm Playwright's Chromium installation and required system libraries |

Application logs go to the console and `/tmp/logs/app.log` in both local and Lambda execution. File logs rotate at 5 MB with five backups. Scraper logs can include extracted evidence content; account for this when handling logs.

See the [high-level design](docs/HIGH_LEVEL_DESIGN.md) for failure handling and the [API guide](docs/API_GUIDE.md) for the distinction between quality verdicts and execution coverage.
