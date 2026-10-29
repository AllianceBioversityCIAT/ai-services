# Mapping Service: agent guide

Read the [root instructions](../AGENTS.md), [README](README.md), and relevant source before editing. This guide describes development. Mapping uses OpenSearch text/fuzzy retrieval plus an external LLM API; it does not implement vector embeddings or direct Bedrock invocation.

## Scope and branches

- Development: `dev-mapping`; service-main: `main-mapping`. Refresh references before integration.
- Prepare focused service work from development. The maintainer handles release merges unless explicitly delegated. Keep shared-guide changes separate in commits/review.
- Service-main has a Dockerfile absent from development, adds `mangum` to requirements, and has a different logger resolver. Preserve these differences; see [branch comparison](docs/BRANCH_DIFFERENCES.md).
- After the maintainer's local development-to-main merge, compare all incoming files and update main-specific documentation before push. This follow-up is part of the agreed service workflow; do not stop at reporting documentation drift when adjustments are already authorized. Leave commit/push within the user's requested scope.
- Do not bring unrelated services or deployment changes into a documentation task. A branch snapshots the entire monorepo.

## Implementation map

| Path | Responsibility |
| --- | --- |
| `api_server.py` | Uvicorn launcher; actual default port 8001, stale port/health help text |
| `main.py` | Mangum Lambda handler |
| `app/api/main.py` | FastAPI app and router prefix `/map` |
| `app/api/models.py` | Entries, environment literals, nullable mapping result fields |
| `app/api/routes.py` | POST `/fields` route under the prefix |
| `app/mapping/opensearch_mapping.py` | Query construction, index routing, result parsing, LLM call, fallbacks |
| `app/utils/config/config_util.py` | Module-level STAR/CLARISA/LLM configuration |
| `app/utils/prompts/` | Staff/institution matching prompts |
| `app/utils/logger/logger_util.py` | Import-time directory/file logging and stdout |
| `requirements.txt`, `pyproject.toml` | Different dependency declarations; development requirements omit Mangum |

## Contracts and behavior to preserve

- Public operation: `POST /map/fields`. No GET root or health route is implemented. No route authentication, rate limiting, or CORS middleware is configured here.
- `environment` defaults to `prod`, including on a development checkout. It changes only the institution index; staff always uses STAR's base index. It does not switch hosts, credentials, the LLM URL, or logger settings.
- Empty entries are accepted and make no external requests. Empty string values and unbounded array lengths are also accepted by the current schema. Do not silently tighten validation in docs work.
- Entries run sequentially. OpenSearch has no explicit HTTP timeout; LLM validation has a 300-second timeout. Synchronous calls run directly inside the async route.
- `_normalize` uses NFD followed by ASCII encoding with ignored characters. It strips accents and drops other non-ASCII characters; it is not a Unicode-preserving lowercase normalizer.
- Query size is 3, with original/normalized multi-match clauses and fuzzy clauses. Staff uses first/last names; institution uses acronym/name. These are text queries, not vector search.
- LLM request is `{prompt, input_text}` using type-specific prompt constants and candidate metadata. No authentication header is added by this HTTP call. The external endpoint chooses its model.
- `selected_candidate` refers to a 1-based candidate position, not an entity ID. The prompts suggest a confidence threshold, but code does not enforce a minimum or a 0–100 range when returning an accepted candidate.
- LLM failure or an out-of-range integer selection can fall back to the first hit with fixed score 90. A truthy parsed object with no selected candidate yields null fields/0. Other malformed shapes/types can reach the per-entry error handler instead. See [API semantics](docs/API_GUIDE.md#selection-and-scores).
- No hits, model rejection, and caught entry errors all appear as null mapped fields/0 in an HTTP 200 batch response; no error/source flag distinguishes them. Do not present 200 or score 90 as proof of LLM verification.
- Preserve input order and duplicate values. Staff IDs come from `carnet`; institution codes are converted to strings when present/truthy.

## Run and checks

Use Python 3.13 from `mapping-service/`, install `requirements.txt` for the local API, and run `python api_server.py --host 127.0.0.1 --reload` or Uvicorn's `app.api.main:app` on port 8001. Lambda uses `main.handler`, but development requirements omit its Mangum dependency. There is no development Dockerfile or lockfile to infer an image build from.

No isolated tests/lint configuration were found. For offline verification, stub logging before import, prevent real dotenv loading, block network, and replace HTTP calls. Check request validation, empty/mixed batches, query bodies/Basic auth, environment selection, nested/direct/fenced LLM responses, fallback cases, and per-entry exceptions. Use fictional staff/catalog data; do not call live endpoints for documentation checks.

For docs-only work, verify local links, example syntax, source claims, and the Markdown-only diff. Do not change prompts, mapping thresholds/selection, dependencies, logging code, or packaging merely to make the documentation simpler.

## External effects and data

OpenSearch calls use `/_search` and do not implement catalog writes, but nonempty requests send data to configured search/LLM services and create logs. Candidate staff email/center metadata can be sent to the LLM. Logs can include terms, candidates, and parsed/extracted model data; keep real records, credentials, and logs out of commits.

Development ignores `LOGS_DIR`. Service-main tries that variable, then its service log directory, then `/tmp/mapping-service/logs`, and avoids duplicate handler installation. Directory creation success is not a guarantee that opening the log file will succeed.

Service-main's Dockerfile copies `.env` and the full context. Do not copy secrets into examples or change build inputs during unrelated documentation work. No Mapping-specific workflow was found in the reviewed checkout; external Jenkins triggers remain unknown. Do not infer that a push cannot deploy.
