# AI Insights: agent guide

This guide applies to `ai-insights-service/`. Read the [root guide](../AGENTS.md) and [service README](README.md). The code lives in `backend/`; run Python commands there so `api`, `ai`, `modules`, and `utils` imports resolve.

## Branch workflow and scope

Prepare work from `dev-ai-insights`, normally in a focused task branch. The integration path is `dev-ai-insights` → `main-ai-insights` → `staging` → `main`. The maintainer performs development-to-service-main integration unless delegated.

After the local service-main integration and before push, compare actual files, routes, dependencies, destinations, and documentation. The reviewed code snapshots currently match, but repeat the comparison rather than assuming that remains true. See [branch differences](docs/BRANCH_DIFFERENCES.md).

Finished service-main changes accumulate in staging for one consolidated PR for the agreed batch. Preparing docs does not authorize release merges, prompt writes, S3 deletion, or live deployments.

## Implementation map

| Task | Start in `backend/` |
| --- | --- |
| HTTP routes/authentication | `api/routes.py` |
| Request/response shape | `api/models.py` |
| App/CORS/health/schema | `api/main.py` |
| Overview orchestration | `modules/document_overview/processing.py` |
| Prompt reads/validation/full replacement | `modules/prompts/processing.py` |
| Prompt IDs, section order, placeholders | `ai/prompts/registry.py` |
| Code defaults | `ai/prompts/prompt_document_overview.py` |
| Bedrock call | `ai/models/claude.py` |
| Project files/cache/prompt JSON | `utils/s3/s3_util.py` |
| STAR metadata | `utils/star/star_client.py` |
| Textract | `utils/textract/textract_util.py` |
| Configuration / logging / integrations | `utils/config/`, `logger/`, `interactions/`, `notification/` |

This service does not currently contain an MCP server, a vector-search pipeline, or a frontend. Do not copy those architectural assumptions from Text Mining.

## Setup and entry points

Use Python 3.13. From `ai-insights-service/backend/`:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

Configure the environment before the final command. `PROMPTS_BUCKET_NAME` and `PROMPTS_PREFIX` are explicitly required at import. The interaction client also expects a configured `INTERACTION_SERVICE_URL` string, including for startup paths that do not request tracking.

See [backend configuration](backend/README.md#configuration) for CLARISA, STAR, AWS, and notification settings. Keep local secrets out of Git. Lambda uses its execution role and ignores app-specific static `INSIGHTS_AWS_*` credentials; preserve runtime-provided AWS credentials.

Docker installs `backend/requirements.txt` with pip. The separate uv graph can resolve different package versions; use an explicit Python version and locked commands consistently if that workflow is chosen. Do not silently regenerate lockfiles or describe an untested local environment as equivalent to deployment.

`backend/main.py` exports `main.handler` through Mangum. It is not the local Uvicorn launcher. The container is a Lambda image, not a server listening on port 8000.

## Overview behavior to preserve

- Generation uses CLARISA `X-API-Key` for `AI Insights Service - STAR`. The optional STAR token comes from the `Access-Token` header, falling back to `STAR_API_TOKEN`; it is not a JSON-body field.
- The last segment of `project_folder` is the STAR contract ID. A bucket/folder is still required with zero documents because generation lists S3.
- Allow zero-to-three supported documents, or zero-to-two when `text` is truthy. Reject no-context requests. The current implementation does not trim whitespace-only `text` before this decision.
- Preserve the received `text` in the returned and saved result, defaulting to an empty string when absent.
- PDF/images use Textract; other readers handle DOCX/TXT/Excel/PPTX. Extraction is parallel and results are sorted by file key. The 3,000,000-character guard covers extracted document text, not a complete prompt-token budget.
- Invalid model JSON can return `overview.raw_response`; the response validates the envelope, not the factual correctness of the overview.
- Cache writes are best-effort. GET reads cache/current files without regeneration; no cache returns HTTP 200 with `status: empty`.
- Adding/deleting files or changing a prompt does not invalidate the saved overview. File deletion keeps `response.json`, rejects path names, and is sequential rather than transactional.

## Prompt Manager behavior to preserve

- The registered prompt ID is currently `project-overview`. Code defaults come from the registry; saved `user_prompt` sections live in configured S3 storage.
- `GET /api/prompts` returns defaults when records are absent/unreadable. It does not persist a seed despite older comments describing seeding.
- `POST /api/prompts` validates a CLARISA key for `AI Insights Service - STAR (Prompt Update)` and fully replaces all four non-blank sections.
- Section order is role, context, user instructions, expected output format. Validate required placeholders across all four: missing, unknown, or repeated names fail. Use each of the five registered variables exactly once.
- Keep literal replacement semantics so ordinary JSON-object braces are not treated as Python formatting.
- Preserve the default prompt for reset/fallback. Prompt edits affect future generations without redeployment, not cached summaries. Caller-supplied `updated_by` is metadata, not a verified identity derived from the key.

## Authentication and external effects

Generation and prompt replacement have CLARISA dependencies. Prompt reads, cache reads, file deletion, health, and schema routes do not have those dependencies in the current declarations. Do not document them as protected by frontend login or silently change authentication during unrelated work.

Model calls, Textract jobs, S3 writes/deletes, prompt replacement, Slack, and analytics have real external effects. Read/stub integrations before offline checks; do not exercise live write/delete examples just to validate Markdown.

AWS clients are lazy. Required configuration and import-time client construction still matter. Logs can contain assembled prompts and source/user context. Do not print tokens, environment secrets, or real project evidence during a handoff.

## Validation and documentation

No automated Insights suite is checked in. For documentation changes, validate Markdown links, shell syntax, request/response examples against Pydantic models, exact route/auth declarations, and prompt placeholder requirements. Offline application smoke checks should stub S3/STAR/Bedrock/analytics/notifications and block network connections.

Do not claim model quality, OCR performance, live access, Docker build success, or Jenkins completion based on offline checks. `/health` reports process metadata without checking integrations.

Keep [README](README.md), [backend setup](backend/README.md), [product overview](docs/PRODUCT_OVERVIEW.md), [API guide](docs/API_GUIDE.md), and [high-level design](docs/HIGH_LEVEL_DESIGN.md) aligned with implemented behavior. Before finishing, report current branch, changed scope, validation and limits, and commit/push/merge status.
