# Mapping Service design

This is the implemented design of `main-mapping`. The [README diagram](../README.md#system-architecture) provides the component flow; the [API guide](API_GUIDE.md) defines the public contract and failure semantics.

## Components and execution

Uvicorn's `api_server.py` launches `app.api.main:app` on port 8001 by default. `main.py` exports `Mangum(app)` for Lambda, and this branch includes Mangum in both requirements and pyproject. The FastAPI app registers the mapping router under `/map`, making the operation `/map/fields`.

The route calls `map_entries_to_ids` directly. Each entry selects an index, searches OpenSearch, builds candidates, optionally validates them through the LLM endpoint, and appends one result. Entries are processed sequentially with no batch queue, concurrency pool, local catalog store, or result cache.

## Retrieval and normalization

1. Staff selects the STAR base index for either environment; institution selects the configured CLARISA test/prod index. Hosts and Basic-auth credentials come from the corresponding configuration dictionary.
2. `_normalize` performs NFD decomposition and ASCII encoding with ignored characters. This removes accents but can also discard non-Latin characters; it does not lowercase text.
3. Original and normalized values are deduplicated, preserving order. Each gets a `best_fields` multi-match clause (boost 2.0) and a `cross_fields` clause (boost 1.0).
4. Staff fields are `first_name^2` and `last_name^2`; institution fields are `acronym^2` and `name`. Additional fuzzy clauses use the unboosted field names, normalized text, fuzziness 1, and boost 0.5.
5. A bool query requires one should-clause match and requests three hits. This is lexical/fuzzy retrieval, not a vector query. OpenSearch field mappings/analyzers are external configuration and are not established here.

Candidate metadata comes from `_source`; `_score` is rounded to four decimals and sent to the LLM as context, rather than returned as the public score. Staff candidates include carnet, composed first/last name, email, and center. Institutions include code, name, acronym, and website link.

## LLM boundary and decision paths

The type-specific Python prompt plus candidate text is posted as `{prompt, input_text}` to the full `LLM_API_URL`. Mapping does not choose the provider/model or invoke AWS directly. The HTTP request has a 300-second timeout and adds no authentication header.

Parsing supports a successful Fast Response-style envelope, direct JSON, and attempted fenced-JSON cleanup. No Pydantic model validates the selection object. Candidate position and confidence are therefore not a strongly validated provider contract.

A valid selected position returns that candidate and the supplied confidence. Null/missing selection in a truthy object yields no match. Request/parser failure or an out-of-range integer position can return the first hit with fixed score 90. Other malformed shapes can reach the entry error handler and yield null/0. See the [decision table](API_GUIDE.md#selection-and-scores) rather than treating all parser failures alike.

The prompt's confidence guidance is not a separate code-enforced threshold. Public responses contain neither a fallback/source flag nor the provider reasoning. Null/0 also represents no hits and caught errors, so a successful HTTP batch response is not a per-entry provider-success report.

## Runtime, configuration, and logging

`load_dotenv` and configuration dictionaries are evaluated during import, and the mapping module snapshots those values. Configuration changes require restart. The logger is imported before `config_util.py` calls `load_dotenv` in the current application import chain; a `LOGS_DIR` override must already be present in the process environment at logger initialization. No public-route authentication, rate limiting, or CORS middleware is configured in this app.

OpenSearch requests have no explicit timeout. The async route executes blocking requests sequentially; LLM timeout does not bound the full batch. The service implements searches, not catalog writes, but search/LLM requests and logs have external/data effects.

This branch resolves the log directory from `LOGS_DIR`, service-relative `data/logs`, or `/tmp/mapping-service/logs`, then initializes stdout/file handlers when the logger has none. Files rotate at 5 MiB with five backups and logger level DEBUG. Development uses a fixed service-relative directory; see [branch comparison](BRANCH_DIFFERENCES.md). Logs can contain names, candidate identifiers, decisions, and parsed/extracted model response data. Candidate staff email/center metadata can be transmitted to the LLM.

## Deployment boundaries

This branch's Dockerfile provides a Lambda Python 3.13 image, installs requirements including Mangum, copies `.env` plus the full context, and starts `main.handler`. Development lacks this Dockerfile and omits Mangum from requirements. This branch's logger tries `LOGS_DIR`, then service-relative logs, then `/tmp/mapping-service/logs` when directory creation fails. That resolver does not certify successful later file opening or deployed availability.

No Mapping-specific GitHub workflow was found in the reviewed tree. Live Jenkins wiring, OpenSearch access, LLM/model choice, and deployment settings cannot be inferred from local code or the lack of a workflow file.

## Validation boundaries

Offline tests should replace HTTP and logging before import, prevent real dotenv reads, and block network. Validate exact indices, query variants, Basic auth, request timeout differences, selection/parser branches, low-confidence acceptance, fixed fallback scores, and mixed-batch continuation. These checks do not measure real catalog quality, provider accuracy, latency, permissions, or pipeline health.
