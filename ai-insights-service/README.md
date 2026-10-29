# AI Insights Service

AI Insights generates project overviews from STAR project/results context, documents stored in S3, and optional user text. It also provides a Prompt Manager API so STAR can read and replace the active overview prompt without redeploying the backend.

The implementation is in `backend/`. No frontend application or automated test suite is included in this service tree. This documentation describes repository behavior; it does not certify a deployed environment or model accuracy.

## Start here

| Goal | Read |
| --- | --- |
| Understand the capabilities and boundaries | [Product overview](docs/PRODUCT_OVERVIEW.md) |
| Run the backend locally | [Backend README](backend/README.md) |
| Integrate the HTTP endpoints | [API guide](docs/API_GUIDE.md) |
| Follow components, storage, and execution | [High-level design](docs/HIGH_LEVEL_DESIGN.md) |
| Continue work with a coding agent | [AGENTS.md](AGENTS.md) |
| Review before service-main integration | [Branch comparison](docs/BRANCH_DIFFERENCES.md) |

## Capabilities

| Capability | Endpoint | Effect |
| --- | --- | --- |
| Generate an overview | `POST /api/document-overview` | Read context, invoke Bedrock, return the overview, and attempt to save `response.json` |
| Retrieve an overview and current files | `GET /api/document-overview` | Read cached `response.json` and list current S3 files; does not regenerate |
| Remove project files | `POST /api/document-overview/files/delete` | Delete named S3 files; keeps `response.json` |
| Read managed prompts | `GET /api/prompts` | Return code defaults and current saved sections |
| Replace a managed prompt | `POST /api/prompts` | Validate and persist a full replacement of the four prompt sections |
| Process metadata and health | `GET /`, `GET /health` | Return application metadata/status without checking dependencies |

The managed prompt ID is currently `project-overview`. Prompt changes affect future generation calls; cached project responses remain until explicitly regenerated.

## Context and documents

Generation uses the final path segment of `project_folder` as the STAR contract ID. It attempts to fetch project metadata and reported results and combines those with the supported files found under the supplied S3 prefix and optional `text`.

- Without a non-empty `text` value: at most three supported documents.
- With a non-empty `text` value: at most two supported documents.
- Zero documents are allowed when STAR context or user text is available.
- A request with no documents, no STAR context, and no user text fails.

The bucket and project folder remain required, including for text-only generation, because the implementation still lists the S3 folder. The limit is based on the truthiness of `text`; the current code does not trim whitespace-only strings before this decision.

Supported formats are PDF, JPG/JPEG, PNG, TIF/TIFF, DOCX, TXT, XLS/XLSX, and PPTX. PDFs/images use Textract; other formats use the standard document readers. Combined extracted document text is limited to 3,000,000 characters. This guard does not establish a complete model-token budget.

## Access and configuration

Generation requires a CLARISA `X-API-Key` for `AI Insights Service - STAR`. Prompt replacement requires a key for `AI Insights Service - STAR (Prompt Update)`. An optional `Access-Token` header supplies STAR context access; `STAR_API_TOKEN` is its server-side fallback.

Cache/file listing, file deletion, prompt reading, health, and generated API documentation have no CLARISA dependency in their route declarations. Any additional infrastructure access controls need separate verification. See the [API guide](docs/API_GUIDE.md#authentication).

The backend requires `PROMPTS_BUCKET_NAME` and `PROMPTS_PREFIX` at startup. Set `INTERACTION_SERVICE_URL` as well: its client is constructed on import even when a request does not ask for analytics. The [backend configuration table](backend/README.md#configuration) describes the remaining settings and local/Lambda credential behavior.

## Storage and response behavior

Project inputs and cached results use the request's bucket and project prefix. Prompt records use the separately configured prompts bucket/prefix. A generation attempt reads the active saved prompt each time, with code defaults as fallback when a prompt record is missing or cannot be read.

The overview is model-generated JSON. If JSON parsing fails, the service can return `overview.raw_response`. A successful HTTP response does not prove semantic correctness. The response also includes processed-document metadata, received text, timing, generation timestamp, cache status, and an optional interaction ID.

Cache writes are best-effort: generation may return successfully even if `response.json` was not saved. A later GET then returns the existing cache or `status: empty`, with `available_files`. Deleting documents or editing prompts does not invalidate or update that cache.

## Runtime and integration

Use Python 3.13 for the Lambda deployment path. Local Uvicorn runs from `backend/`; `main.handler` is the Mangum Lambda entry point. The Dockerfile installs `backend/requirements.txt` with pip, copies the application packages, and excludes `.env` files from the build context.

The CloudFormation template describes a container-image Lambda and Function URL. Its declared resource defaults are deployment inputs, not verified live settings. It bootstraps only `IS_PROD`; the complete required configuration must be supplied through the environment's configuration process.

```text
task branch from dev-ai-insights
    → dev-ai-insights → main-ai-insights → staging → main
```

The maintainer handles development-to-service-main integration. After the local merge and before push, compare service files, routes, dependency inputs, storage destinations, and documentation. The reviewed development and service-main code snapshots currently match; see [branch comparison](docs/BRANCH_DIFFERENCES.md) for reference commits.

GitHub workflows trigger Jenkins on pushes to `dev-ai-insights` and `main-ai-insights`, including documentation-only changes. Completed service-main updates can accumulate in `staging`; open the consolidated PR to `main` when the current service batch is ready.

## Validation and operations

There is no checked-in Insights test suite. For documentation, validate request/response examples, prompt placeholders, route names, local links, and shell syntax. An offline smoke check must replace S3, STAR, Bedrock, and notification/analytics calls before invoking routes. Live checks can overwrite prompts/cache, delete objects, invoke paid services, or send notifications.

Logs write to the console and `/tmp/logs/app.log`, with 5 MB rotation and five backups. The overview processor logs the assembled prompt, which can contain document text and STAR/user context. Handle logs accordingly.

`/health` is a process response, not an S3/STAR/Bedrock/Textract readiness test. Some static API descriptions still mention older document-count assumptions; use the handlers and current guide for the zero-to-three/zero-to-two behavior.
