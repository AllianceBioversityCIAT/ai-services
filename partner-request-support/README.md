# Partner Request Support

Partner Request Support compares proposed institutions with the CLARISA institution catalog and supports manual review, web research, and an optional automated decision flow. It contains a FastAPI backend and a Next.js frontend exported as static files.

This documentation describes the development branch. The service-main branch preserves different cache-table and environment destinations; see [branch differences](docs/BRANCH_DIFFERENCES.md). Repository checks do not certify live CLARISA contracts, model accuracy, or deployment availability.

## Start here

| Goal | Documentation |
| --- | --- |
| Understand supported workflows | [Product overview](docs/PRODUCT_OVERVIEW.md) |
| Run/configure the backend | [Backend README](backend/README.md) |
| Run/configure the frontend | [Frontend README](frontend/README.md) |
| Integrate API calls and understand side effects | [API guide](docs/API_GUIDE.md) |
| Follow components and storage | [High-level design](docs/HIGH_LEVEL_DESIGN.md) |
| Understand matching scores | [How the search works](backend/docs/HOW%20THE%20SEARCH%20WORKS.md) |
| Continue work with an agent | [Service guide](AGENTS.md), [frontend guide](frontend/AGENTS.md) |

## Workflows

| Workflow | Entry | Behavior |
| --- | --- | --- |
| Spreadsheet review | `POST /api/process-partners` | Synchronize institutions, optionally create CLARISA requests, match spreadsheet rows, and cache results |
| Pending-request review | `GET /api/sync-partner-requests`, then `POST /api/process-api-partners` | Fetch pending CLARISA requests and process a default batch of ten, oldest first |
| Human response | `POST /api/respond-partner-request` | Accept/reject an existing request in CLARISA with the supplied user/token |
| Manual web research | `POST /api/manual-web-search` | Generate a research summary for a proposed institution |
| Automated evaluation | `POST /api/auto-partner-request` | Classify duplicates or run web/rules review; optionally create/respond in CLARISA |
| Catalog maintenance | `POST /api/sync-clarisa-institutions` | Update the Supabase institution snapshot/embeddings and optionally delete obsolete entries |

Processing is not a read-only search. Spreadsheet and pending-request processing synchronize database contents and update cache. Spreadsheet creation defaults to enabled, and the frontend explicitly enables it. Automated evaluation can perform web/model calls and send manual-review notifications even with auto-response disabled.

## Matching and decision boundaries

Matching uses Titan Text Embeddings V2, Supabase/pgvector candidates, language translation where applicable, and RapidFuzz reranking. The manual-review score is `0.60 × semantic + 0.30 × fuzzy name + 0.10 × fuzzy acronym`. Manual quality tiers are excellent at 0.85+, good at 0.70+, fair at 0.60+, otherwise no match.

Automated evaluation has its own tiers. An excellent score above 0.95 is treated as a duplicate and rejected; scores from 0.70 through 0.95 use a separate same-institution check. Unconfirmed duplicates, fair matches, and no-match cases proceed to web/rules evaluation, which returns ACCEPT or MANUAL_REVIEW. These tiers must not be interchanged with frontend review labels.

Field completeness is returned as information in the current automatic web/rules path; it is not an independent acceptance gate there. A score, model decision, or successful HTTP response is not a guarantee of institutional eligibility or a confirmed upstream response. See [API semantics](docs/API_GUIDE.md#automated-evaluation).

## Frontend and authentication

The Next.js app supports Excel upload, pending-request synchronization, ten-request processing batches, candidate inspection, manual web search, and human accept/reject actions. React hooks keep login state and results; the UI calls the configured Python API directly.

In this development branch, login targets the CLARISA test authentication host. The browser receives an access token and passes it as an internal `auth_token` value for creation/response operations. Those calls translate it to an upstream Bearer header.

The local FastAPI routes do not define a general authentication dependency. A frontend login does not establish protection of every backend route. Confirm infrastructure access controls and external catalog/endpoint contracts for the target environment.

## Storage and configuration

Supabase stores `clarisa_institutions_v2` and the development cache table `partner_request_cache_test`. Service-main uses `partner_request_cache_prod`. The table is selected by a code constant and matching SQL, not an environment flag. Preserve that distinction during integration.

Configuration includes Supabase access, CLARISA institution/pending/create/respond/catalog URLs, AWS Bedrock/Translate/S3 access, OpenAI, and optional RabbitMQ email settings. See the [backend configuration table](backend/README.md#configuration); no `.env.example` is included in the reviewed tree.

Cached results can be reused by normalized partner name. The batch API reassigns current request IDs; other cached source metadata can remain from the earlier result. Catalog changes can clear cached matches. The pending queue is a process-local snapshot fetched by sync (or recovered when empty), not a shared queue service.

## Runtime and integration

Use Python 3.13 for the Lambda backend path. The backend runs locally from `backend/` with Uvicorn and deploys as a Lambda container through Mangum's `main.handler`. Docker installs `requirements.txt`. The frontend uses Next.js 16.1.6 / React 19.2.3, static export, and S3/CloudFront infrastructure.

```text
task branch from dev-partner-request-support
    → dev-partner-request-support → main-partner-request-support → staging → main
```

After the maintainer's local service-main integration, compare cache constants/SQL, CORS, the frontend login host, and environment labels. Adapt service-main documentation before push rather than replacing production destinations with development values. Completed service updates accumulate in `staging` for the agreed consolidated PR to `main`.

The GitHub workflows trigger Jenkins on pushes to the development and service-main branches. They do not exclude documentation-only changes. The infrastructure templates describe deployment inputs, not verified live settings.

## Validation and references

The files in `backend/test/` are live search examples, not an isolated regression suite; one runs web searches at import. Do not run them as routine documentation checks. Offline checks should stub Supabase, CLARISA, AWS/model calls, and notifications and block network connections.

Validate examples, route/body shapes, batch selection, score boundaries, and automatic-decision branches separately from live provider accuracy. Frontend lint may report existing code issues; do not treat a documentation update as a validated build or deployment.

The [institution rules reference](backend/docs/CGIAR_INSTITUTION_RULES.md) is retained business context. Current executable routing is described in the API guide; this repository review is not an independent policy/legal determination. The [frontend refactoring note](frontend/docs/REFACTORING.md) records earlier structural work.
