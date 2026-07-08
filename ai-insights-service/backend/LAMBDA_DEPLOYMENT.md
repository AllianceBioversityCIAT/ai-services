# Lambda Deployment Playbook (FastAPI + Mangum)

Change log for adaptations applied to `ai-insights-service/backend` so the service can run as an **AWS Lambda (container image)** behind a **Function URL**, plus a reusable checklist for other microservices in this monorepo.

Historical reference: pattern used in `text-mining-service` (Mangum + `public.ecr.aws/lambda/python` image + writable paths under `/tmp`).

---

## Goal

Take a FastAPI microservice (local uvicorn) and prepare it to:

1. Package as a Lambda container image
2. Be invoked via `main.handler` (Mangum ASGI adapter)
3. Be provisioned with CloudFormation (function, IAM role, Function URL)

---

## Reusable checklist (copy for another service)

Mark each item when adapting a new component:

| # | Change | Why | Status in ai-insights |
|---|--------|-----|------------------------|
| 1 | `mangum` dependency in `requirements.txt` / `pyproject.toml` | ASGI adapter → Lambda event | Already present |
| 2 | `main.py` exports `handler = Mangum(app)` | Entrypoint required by Lambda (`CMD ["main.handler"]`) | Already present |
| 3 | Write only under `/tmp` (logs, DBs, locks, temp) | Lambda filesystem is read-only except `/tmp` | Already present (`utils/logger`) |
| 4 | `Dockerfile` based on `public.ecr.aws/lambda/python:3.13` | Official Lambda runtime/image | **Added** |
| 5 | `.dockerignore` | Smaller image; keep local secrets out of the build | **Added** |
| 6 | AWS clients optionally use static keys (fallback to IAM role) | Do not embed `AWS_ACCESS_KEY_ID` / secret in Lambda | **Added** |
| 7 | CloudFormation template (Image Lambda + URL + IAM) | Infra as code, reusable per environment | **Added** |
| 8 | Document env vars, timeout/memory, and IAM permissions | Avoid blind deploys on the next service | This file |
| 9 | CI: ECR push + `cloudformation deploy` (no SSH/`update-function-code`) | CFN owns Lambda create/update | Documented below (Jenkinsfile kept outside git) |

---

## Changes applied to this service (changelog)

### Already present (audit 2026-07-08)

- **`main.py`**: loads dotenv, imports `api.main.app`, exports `handler = Mangum(app)`.
- **`requirements.txt` / `pyproject.toml`**: include `mangum`.
- **`utils/logger/logger_util.py`**: writes logs under `/tmp/logs` (Lambda-safe).
- **`utils/config/config_util.py`**: reads `IS_PROD`, Slack, CLARISA, and interaction URL from env.
- No LanceDB or other persistent local paths outside `/tmp`.

### Added / modified in this session

#### 1. `Dockerfile`

- Base: `public.ecr.aws/lambda/python:3.13`
- `pip install -r requirements.txt -t "${LAMBDA_TASK_ROOT}"`
- Copies application packages: `api/`, `ai/`, `modules/`, `utils/`, `main.py`
- `CMD ["main.handler"]`
- Does **not** copy `.env` into the image (secrets via Lambda env / SSM)

#### 2. `.dockerignore`

Excludes `.env`, virtualenvs, caches, markdown, and `infrastructure/` from the build context.

#### 3. boto3 clients (IAM-friendly)

Files:

- `utils/s3/s3_util.py`
- `utils/textract/textract_util.py`
- `ai/models/claude.py`

Behavior:

- If `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` are set → use them (local dev).
- Otherwise → `boto3` uses the default credential chain (**Lambda execution role**).

#### 4. CloudFormation

File: `infrastructure/cloudformation/lambda-function.yaml`

Creates:

- `AWS::IAM::Role` (logs + S3 read + Bedrock invoke + Textract)
- `AWS::Lambda::Function` (`PackageType: Image`)
- `AWS::Lambda::Url` + `lambda:InvokeFunctionUrl` permission
- Outputs: ARN, function name, Function URL, role ARN

Relevant parameters:

| Parameter | Purpose |
|-----------|---------|
| `EnvironmentName` | Name suffix (`dev`, `prod`, …) |
| `ImageUri` | Full ECR image URI (with tag) |
| `MemorySize` / `Timeout` / `EphemeralStorageSize` | Sizing (defaults: 2048 MB / 300 s / 1024 MB) |
| `CorsAllowOrigin` | Function URL CORS |
| `IsProd` | App `IS_PROD` flag |
| `SlackWebhookUrl`, `ClarisaValidateUrl`, `InteractionServiceUrl` | Optional env vars |
| `DocumentsBucketArn` | Optional IAM scope for S3 |

**Note:** do not set `AWS_REGION` in Environment — it is a reserved variable; Lambda injects it automatically.

---

## Suggested deploy flow

### A. Once per environment: ECR repository

```bash
aws ecr create-repository --repository-name ai-insights-service --region us-east-1
```

(Or let CI create it / reuse an existing repository.)

### B. Build & push image

From `ai-insights-service/backend`:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
REPO=${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/ai-insights-service
TAG=dev  # or commit sha / semver

aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

docker build -t ${REPO}:${TAG} .
docker push ${REPO}:${TAG}
```

### C. Create / update CloudFormation stack

```bash
STACK=ai-insights-service-dev
IMAGE_URI=${REPO}:${TAG}

aws cloudformation deploy \
  --stack-name ${STACK} \
  --template-file infrastructure/cloudformation/lambda-function.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    EnvironmentName=dev \
    ImageUri=${IMAGE_URI} \
    IsProd=false \
    CorsAllowOrigin=* \
    DocumentsBucketArn=arn:aws:s3:::YOUR_DOCS_BUCKET
```

### D. Retrieve the Function URL

```bash
aws cloudformation describe-stacks \
  --stack-name ${STACK} \
  --query "Stacks[0].Outputs[?OutputKey=='LambdaFunctionUrl'].OutputValue" \
  --output text
```

Quick health check:

```bash
curl -sS "${FUNCTION_URL}health"
```

### E. Later code updates

After pushing a new image, either:

1. Redeploy the stack with the same or a new `ImageUri` (tag or digest), **or**
2. `aws lambda update-function-code --function-name ai-insights-service-dev --image-uri ${IMAGE_URI}`

---

## Quick map: files to touch in ANOTHER service

Assuming a similar FastAPI layout:

```text
<service>/
  main.py                 # -> Mangum handler
  requirements.txt        # -> + mangum
  pyproject.toml          # -> + mangum (if applicable)
  Dockerfile              # -> copy and adjust package COPY paths
  .dockerignore
  infrastructure/
    cloudformation/
      lambda-function.yaml  # -> adjust name, IAM (S3/Bedrock/...), env vars
  <app package>/          # write paths -> /tmp
  utils/logger/...        # /tmp/logs
```

Minimum code steps:

1. Ensure the FastAPI `app` is importable from `main.py`
2. `handler = Mangum(app)`
3. Find disk writes (`open`, local DB, logs) and move them to `/tmp`
4. Make boto3 not require hardcoded keys
5. Adjust template IAM to the AWS services the component uses
6. Tune timeout/memory for the workload (Textract/LLM often need ≥ 128–300 s)

---

## Differences vs text-mining-service

| Topic | text-mining | ai-insights (this work) |
|-------|-------------|-------------------------|
| Entry | `main.handler` + Mangum | Same |
| Image | Lambda Dockerfile | Lambda Dockerfile (does not copy `.env`) |
| Vector DB | LanceDB under `/tmp/miningdb` | N/A |
| Reference cache | S3 JSON for cold starts | N/A |
| CFN infra | None for backend; frontend OpenNext yes | **Yes**, `lambda-function.yaml` for the backend |
| Credentials | Explicit keys in several clients | Fallback to IAM role |

---

## Local verification (without Lambda)

Still valid for development:

```bash
cd ai-insights-service/backend
uv sync   # or pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
# or: python -m api.main
```

Mangum is only involved when the runtime invokes `main.handler`.

---

## Jenkins CI/CD (CloudFormation creates/updates the Lambda)

The Jenkins pipeline is **not stored in this git repo** (see root `.gitignore`). Keep it in Jenkins job config (or a private ops repo). Expected flow vs `text-mining-service` PROD:

| Step | text-mining | ai-insights |
|------|-------------|-------------|
| Clone | Same pattern | Same |
| Build image | Bake `.env` into Docker context | Build `ai-insights-service/backend` with **no** `.env` in the image |
| Push ECR | Tag `latest` | Same idea |
| Deploy | SSH → `aws lambda update-function-code` | **`aws cloudformation deploy`** with `ImageUri` (creates/updates Lambda) |

### What to configure before the first Jenkins run

1. Create ECR repository `ai-insights-service` (if missing).
2. Create Secrets Manager secret (dotenv text), e.g. `prod/microservice/ai-insights`, optional keys:
   - `SLACK_WEBHOOK_URL`
   - `CLARISA_VALIDATE_URL`
   - `INTERACTION_SERVICE_URL`
3. In the Jenkins job environment (not git): branch, stack name, ECR image URI, Secrets Manager id, optional `DocumentsBucketArn`.
4. Jenkins AWS credentials need: ECR push, Secrets Manager read, CloudFormation deploy, IAM role create/update (`CAPABILITY_NAMED_IAM`), Lambda create/update.

### Pipeline stages (summary)

1. Start — Slack notification  
2. Clone — checkout deploy branch  
3. Startup — `docker build` in `ai-insights-service/backend`  
4. Build — tag + push image to ECR  
5. Deploy — load secrets → `cloudformation deploy` → print stack outputs (Function URL)  

First successful deploy **creates** the Lambda, execution role, and Function URL. Later builds push a new image and update the same stack with the new `ImageUri`.

---

## Out of scope / follow-ups

- Create the ECR repository via CloudFormation (optional; CI assumes the repo exists).
- Move secrets to native SSM/Secrets Manager dynamic references inside the template (instead of parameter overrides).
- Function URL auth (`AWS_IAM`) or API Gateway in front (currently `AuthType: NONE`).
- Validate cold start and timeout with real documents (async Textract + Bedrock).
- Dev/staging twin of the Jenkins job (same flow, different branch / stack / secret id).

When replicating on another service: copy this playbook and the CFN template, update names/IAM, and keep the Jenkins pipeline outside git if that is your team convention.
