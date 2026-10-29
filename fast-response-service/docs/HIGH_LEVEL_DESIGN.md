# Fast Response Service design

This is the implemented development-branch design. The [README diagram](../README.md#system-architecture) gives the call flow; the [API guide](API_GUIDE.md) defines request/error semantics.

## Components and execution

1. Uvicorn locally, or Mangum in Lambda, invokes `app.api.main:app`.
2. FastAPI validates `FastRequest` and calls the generation route in `app/api/routes.py`.
3. `return_response(prompt, text)` composes one string with a colon-space separator.
4. `invoke_model` calls Bedrock synchronously through a module-level boto3 client.
5. The first provider text block is returned in `FastResponse` with echoed inputs. The route translates caught exceptions to 400/500 HTTP errors.

The service has no dedicated UI, vector store, uploaded-file ingestion, chat memory, or database. There is no application-level cache, job queue, or retry/idempotency layer. SDK retries are separate from those application features.

## Provider boundary

| Concern | Implementation |
| --- | --- |
| Client | boto3 `bedrock-runtime`, constructed when `mining.py` is imported |
| Credentials | Service-specific BR access key/secret if supplied; otherwise standard boto3 credential resolution |
| Region | Explicit `us-east-1`; the dictionary's `AWS_REGION` value is not consumed here |
| Model | Hardcoded `us.anthropic.claude-sonnet-4-6` |
| Payload | One user text block, no system message; max tokens 4000, temperature 0.1 |
| Timeouts | Connect 60 s, read 300 s, adaptive retries with `max_attempts=3` |
| Parsing | JSON body, first content block text only |
| Observability | Stop reason and token usage logged; not returned through API |

Changing model, region, prompt concatenation, or response parsing changes behavior. Verify provider request compatibility and caller expectations together. Availability and quotas in a live account are not established by reading these constants.

## State, logging, and concurrency

Each request carries its own inputs; there is no conversation/session record. The Bedrock client and logger are module-level objects. The async route executes a synchronous SDK call directly, which occupies its worker during the call; no background job or nonblocking provider adapter is implemented.

Development creates a rotating file under service-relative `data/logs/app.log` during import, with a 5 MiB limit and five backups, in addition to stdout. Service-main uses `/tmp/logs/app.log`. Initialization requires a writable directory. Logger level is DEBUG; Uvicorn's CLI log-level option does not change that application constant.

The route logs the full prompt. Model calls log usage and stop reason, and error paths log exception text. Request/response logs are not a durable request database or evidence of successful upstream delivery. Handle them according to their contents rather than committing them as examples.

## Runtime and deployment

`api_server.py` launches `app.api.main:app`; its older AICCRA help text does not identify another application. `main.py` exports `Mangum(app)` as `handler`. The Dockerfile uses the Lambda Python 3.13 base image, installs requirements, and starts `main.handler`.

The existing Dockerfile copies `.env` and the full context. Image packaging and credential handling need to account for those actual copy instructions. No image was built or deployed as part of documentation review.

The service's GitHub workflow invokes Jenkins on service-main pushes, pull requests targeting service-main, and manual dispatch. It does not exclude documentation-only changes. Live Jenkins configuration and deployment details are outside the repository checks.

## Validation boundaries

Offline checks can validate schemas, exact provider payloads, output parsing, stop-reason handling, and error envelopes with a fake client and network blocked. They do not validate model quality, real AWS authorization, costs, latency, or deployment health. No fixed response-time or accuracy target is implemented by the service name.

The application declares MIT in OpenAPI metadata, while the root repository license file contains Apache 2.0. Documentation records this mismatch without making a new licensing decision or modifying behavior/configuration.
