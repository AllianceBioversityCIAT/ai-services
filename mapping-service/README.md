# Mapping Service

Mapping Service resolves free-text staff and institution names to identifiers from configured OpenSearch catalogs. It retrieves candidates with text/fuzzy queries, then asks an external LLM API to select a candidate or reject the match. Staff IDs come from STAR's `carnet`; institution IDs come from CLARISA's `code`.

This guide describes `main-mapping`, which includes a Lambda Dockerfile, Mangum in requirements, and a log-directory resolver; see [branch differences](docs/BRANCH_DIFFERENCES.md). The implemented retrieval uses text queries, not a vector/embedding search. There is no dedicated frontend or local catalog database.

## Start here

| Goal | Read |
| --- | --- |
| Run locally | [Quick start](#quick-start) |
| Understand the workflow | [Product overview](docs/PRODUCT_OVERVIEW.md) |
| Integrate the API and interpret scores | [API guide](docs/API_GUIDE.md) |
| Follow components and external calls | [System architecture](#system-architecture), [detailed design](docs/HIGH_LEVEL_DESIGN.md) |
| Continue implementation | [Agent guide](AGENTS.md) |
| Review branch integration | [Branch differences](docs/BRANCH_DIFFERENCES.md) |
| Diagnose failures or missing matches | [Troubleshooting](#troubleshooting) |

## Quick start

### 1. Install local dependencies

From the monorepo root, using Python 3.13:

```bash
cd mapping-service
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

This installs the local API and Lambda-adapter dependencies from this branch's `requirements.txt`, including `mangum`. `pyproject.toml` also declares Mangum. A Lambda Dockerfile is present in this branch; no tracked dependency lockfile is included. Development differs in these packaging/dependency details; see the [branch comparison](docs/BRANCH_DIFFERENCES.md).

### 2. Configure the external services

Create `.env` in `mapping-service/` with values for the intended catalogs and LLM endpoint. Example placeholders:

```env
STAR_OPENSEARCH_URL=https://star-search.example
STAR_OPENSEARCH_BASE_INDEX=example-staff-index
STAR_OPENSEARCH_USERNAME=YOUR_STAR_USERNAME
STAR_OPENSEARCH_PASSWORD=YOUR_STAR_PASSWORD
CLARISA_OPENSEARCH_URL=https://clarisa-search.example
CLARISA_OPENSEARCH_PROD_INDEX=example-institutions-prod
CLARISA_OPENSEARCH_TEST_INDEX=example-institutions-test
CLARISA_OPENSEARCH_USERNAME=YOUR_CLARISA_USERNAME
CLARISA_OPENSEARCH_PASSWORD=YOUR_CLARISA_PASSWORD
LLM_API_URL=http://localhost:8000/api/fast-response
```

The OpenSearch URLs are base URLs; code appends the selected index and `/_search`. `LLM_API_URL` is the complete generation endpoint. It receives `prompt` and `input_text`; the [Fast Response service](../fast-response-service/README.md) is one compatible API shape, but Mapping does not start it or select a model itself.

Configuration is loaded into module-level values during import. Restart the service after changing `.env`. Use supplied environment values rather than the fictional search URLs above, and keep credentials out of commits.

### 3. Start the API

```bash
python api_server.py --host 127.0.0.1 --reload
```

The launcher's actual default port is **8001**. Its help text incorrectly mentions 8000, and its printed `/health` URL does not correspond to an implemented route. Equivalent direct command:

```bash
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8001 --reload
```

| Local resource | URL |
| --- | --- |
| Swagger UI | [API documentation](http://localhost:8001/docs) |
| ReDoc | [API reference](http://localhost:8001/redoc) |
| OpenAPI schema | [Schema](http://localhost:8001/openapi.json) |
| Mapping operation | `POST http://localhost:8001/map/fields` |

There is no `GET /` or `/health` application route in this checkout. `main.py` exposes `main.handler` for Lambda; it is not the local server launcher.

### 4. Check the local route without external searches

In another terminal:

```bash
curl -X POST http://localhost:8001/map/fields \
  -H 'Content-Type: application/json' \
  -d '{"entries":[],"environment":"test"}'
```

Expected response:

```json
{"results": []}
```

An empty batch makes no OpenSearch/LLM requests. This confirms local route execution, not catalog access or match quality. Actual nonempty mapping requests contact the configured services and can invoke a paid LLM API.

## System architecture

```mermaid
flowchart TB
    Caller["Calling application: entries and environment"]
    API["FastAPI: POST /map/fields"]
    Select["Per-entry type and index selection"]
    Staff["STAR OpenSearch: configured staff index"]
    Institutions["CLARISA OpenSearch: test or prod institution index"]
    Candidates["Candidate metadata: requested top three hits"]
    Prompts["Type-specific staff or institution prompt"]
    LLM["External HTTP LLM API: LLM_API_URL"]
    Decide["Selection, no-match, or first-hit fallback"]
    Results["MappingResponse: ordered results"]

    Caller --> API --> Select
    Select -->|"staff"| Staff
    Select -->|"institution"| Institutions
    Staff --> Candidates
    Institutions --> Candidates
    Candidates --> Prompts --> LLM --> Decide
    Candidates -->|"Fallback on unusable validation"| Decide
    Select -->|"No hits or entry error"| Results
    Decide --> Results --> Caller
```

Entries are processed sequentially. OpenSearch uses HTTP Basic authentication; the LLM request sends JSON without an authentication header in this implementation. Mapping does not directly call Bedrock or maintain embeddings. Its prompts live in Python modules, and the selected LLM/model depends on the configured external endpoint.

The [detailed design](docs/HIGH_LEVEL_DESIGN.md) covers query construction, parsing, timeouts, logging, and branch-specific runtime behavior.

## Project structure

```text
mapping-service/
├── README.md                       # Setup, architecture, usage, operations
├── AGENTS.md                       # Implementation map and working rules
├── docs/                           # API, product, design, branch comparison
├── api_server.py                   # Local Uvicorn CLI, default port 8001
├── main.py                         # Mangum Lambda handler
├── Dockerfile                      # Lambda Python 3.13 image, main.handler
├── requirements.txt                # Local API and Lambda-adapter dependencies
├── pyproject.toml                  # Project metadata; also declares mangum
└── app/
    ├── api/
    │   ├── main.py                 # FastAPI app and /map router registration
    │   ├── models.py               # Request and result schemas
    │   └── routes.py               # POST /fields under the /map prefix
    ├── mapping/opensearch_mapping.py # Search, normalization, LLM parsing, fallback
    └── utils/
        ├── config/config_util.py   # dotenv and catalog/LLM configuration
        ├── logger/logger_util.py   # stdout and rotating file logger
        └── prompts/
            ├── prompt_staff.py
            └── prompt_institutions.py
```

`.env`, virtual environments, and generated logs are local artifacts. This branch tries `LOGS_DIR`, service-relative `data/logs`, then `/tmp/mapping-service/logs` for directory creation, and writes `app.log` in the selected directory. It installs handlers only when none already exist. Development uses a fixed service-relative directory.

## API and examples

`POST /map/fields` takes a JSON object containing `entries` and optional `environment`. Each entry has a string `value` and a `type` of `staff` or `institution`.

```json
{
  "entries": [
    {"value": "Example Person", "type": "staff"},
    {"value": "Example Research Institute", "type": "institution"}
  ],
  "environment": "test"
}
```

**Omitting `environment` selects `prod`**, even on the development branch. This field changes only the CLARISA institution index. Staff always uses `STAR_OPENSEARCH_BASE_INDEX`; it does not switch staff credentials, the LLM endpoint, logging, or the Git branch's deployment settings.

Illustrative successful response:

```json
{
  "results": [
    {
      "original_value": "Example Person",
      "type": "staff",
      "mapped_id": "EXAMPLE-001",
      "mapped_name": "Example Person",
      "mapped_acronym": null,
      "score": 94
    },
    {
      "original_value": "Example Research Institute",
      "type": "institution",
      "mapped_id": "9001",
      "mapped_name": "Example Research Institute",
      "mapped_acronym": "ERI",
      "score": 92
    }
  ]
}
```

These names, identifiers, and scores are fictional. Real results depend on catalogs and LLM output. Array order follows input order, including duplicate input values.

### Python

Using a client environment with `requests` installed:

```python
import requests

response = requests.post(
    "http://localhost:8001/map/fields",
    json={
        "entries": [{"value": "Example Research Institute", "type": "institution"}],
        "environment": "test",
    },
    timeout=360,
)
response.raise_for_status()
for result in response.json()["results"]:
    print(result["original_value"], result["mapped_id"], result["score"])
```

The client timeout is illustrative. It does not impose a server-side deadline or establish that a timed-out request made no external calls.

## Matching and score semantics

OpenSearch queries combine original text with an accent-stripped ASCII variant, `multi_match` clauses, and fuzzy clauses. Staff queries target first/last names; institution queries target acronym/name. Search requests ask for three hits.

The LLM receives candidate positions and metadata. A selected candidate uses the returned `confidence_score`; the API does not enforce the prompt's suggested minimum confidence or a 0–100 bound. If LLM validation fails or returns an out-of-range integer selection, the service can choose the first OpenSearch hit with a **fixed score of 90**. This score is not the OpenSearch relevance score or a measured probability.

No hits, a no-match decision, or a caught per-entry error produces null mapped fields and score 0. These outcomes are indistinguishable in the public response. There is no fallback/error/source flag, so HTTP 200 and score 90 alone do not prove successful LLM validation. See [API semantics](docs/API_GUIDE.md#selection-and-scores) for exact cases.

## Configuration and runtime

| Setting | Effect |
| --- | --- |
| `STAR_OPENSEARCH_URL`, `STAR_OPENSEARCH_BASE_INDEX` | Staff search host and index, for both request environments |
| `STAR_OPENSEARCH_USERNAME`, `STAR_OPENSEARCH_PASSWORD` | Staff search Basic auth |
| `CLARISA_OPENSEARCH_URL` | Institution search host |
| `CLARISA_OPENSEARCH_TEST_INDEX`, `CLARISA_OPENSEARCH_PROD_INDEX` | Institution index selected by the request's environment |
| `CLARISA_OPENSEARCH_USERNAME`, `CLARISA_OPENSEARCH_PASSWORD` | Institution search Basic auth |
| `LLM_API_URL` | Full generation endpoint; no model ID is configured inside Mapping |
| `LOGS_DIR` | First log-directory candidate in this branch; supply it in the process environment before startup. Development ignores it. |

The logger is imported before `config_util.py` loads dotenv in the current app import chain. For explicit log selection, export `LOGS_DIR` before starting the process; a value only in `.env` is not loaded in time for that initial selection.

The route has no implemented API-key/token dependency, rate limiter, or CORS middleware. OpenSearch credentials authenticate outbound searches; they do not authenticate callers of `/map/fields`. Deployment access controls must be checked separately.

The async route directly executes synchronous HTTP calls. The OpenSearch request has no explicit timeout; the LLM request uses 300 seconds. Multiple entries can make multiple sequential provider calls, so there is no bounded batch latency established by this implementation.

## Deployment and promotion

```text
task branch from dev-mapping
    → dev-mapping → main-mapping → staging → main
```

This service-main branch has a Lambda Python 3.13 Dockerfile, includes `mangum` in requirements, and uses a logger resolver that tries `LOGS_DIR`, the service log directory, then `/tmp/mapping-service/logs`. Preserve these implementation differences during integration. The image starts `main.handler`; the local Uvicorn command remains a separate execution path.

The current Dockerfile copies `.env` and the full build context into its image. This records the checked-in packaging, not a verified build or deployment. No Mapping-specific GitHub workflow was found among the reviewed workflows; external Jenkins triggers are not established by that absence.

After the maintainer's local merge, compare the resulting tree and **adjust the main-specific documentation before push**. The [branch guide](docs/BRANCH_DIFFERENCES.md) records files, dependencies, and logging behavior to check. Completed service work accumulates in staging for the agreed consolidated PR to main.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `/health` or `/` returns 404 | These routes are not implemented, despite the launcher's printed health URL. Use `/openapi.json` or the empty-batch check above. |
| The server is not on port 8000 | The launcher defaults to 8001. Set `--port` explicitly if needed; its help text is stale. |
| HTTP 422 | Check the required entries array, string values, exact type literals, and `environment` (`test` or `prod`). One invalid entry rejects the request before mapping starts. |
| HTTP 200 but all IDs are null | Check logs and OpenSearch credentials/indices/connectivity. No hits, LLM rejection, malformed selection, and per-entry errors can all yield null/0 results. |
| A match scores 90 during LLM outages | First-hit fallback assigns 90. The response does not identify fallback separately from an LLM-selected match. |
| Staff does not change with `environment=test` | Staff always uses the configured STAR index. The environment selector affects institution indexing only. |
| Configuration changes appear ineffective | Restart after editing `.env`; configuration values are captured at import. |
| Log initialization fails on a read-only filesystem | Set a suitable `LOGS_DIR` in the process environment before startup, or inspect the resolver's service-directory and `/tmp/mapping-service/logs` fallbacks. File opening can still fail after directory selection; see [branch differences](docs/BRANCH_DIFFERENCES.md). |
| Lambda import fails because Mangum is missing | This branch declares `mangum` in both requirements and pyproject. Verify that the actual image/environment installed this branch's dependencies; development requirements omit it. |

Logs use stdout and a rotating file (5 MiB, five backups), with logger level DEBUG. They can contain search terms, candidate names/IDs, and LLM decisions or extracted response text. Staff candidate email/center metadata is sent to the LLM when present. Use fictional data in examples and redact shared diagnostics.

## Validation and references

No service-specific test suite or lint configuration was found in the reviewed tree. Documentation/offline checks should verify schemas, test/prod routing, query normalization, LLM result parsing, fallback scores, and mixed-batch behavior using mocked HTTP clients and blocked network connections.

An empty-batch check or offline mock does not verify live catalogs, credentials, model quality, Jenkins, or Lambda availability. See the repository [LICENSE](../LICENSE) for its Apache 2.0 text.
