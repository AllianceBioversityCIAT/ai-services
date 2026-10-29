# AI Services

CGIAR monorepo for AI-assisted reporting, document extraction, project insights, institution matching, interaction tracking and administration. Services have separate applications, dependencies and development/service-main branches.

Use this README to find the right service. Follow its own guide for the current checkout's setup and contracts; there is no repository-wide install, build or test command. `main` is the consolidated reference after integration, while service branches can retain different files and environment settings.

## Service index

| Service | Purpose | Start here |
| --- | --- | --- |
| Admin Module | Administration of projects, products, users and prompts | [Application](admin-module/), [package scripts](admin-module/package.json) |
| AI Feedback | Record AI interactions and optional feedback in DynamoDB; queue negative-feedback notifications | [README](ai-feedback-service/README.md) |
| AI Insights | Generate STAR project overviews and manage overview prompts | [README](ai-insights-service/README.md) |
| AR Generator | Generate AICCRA indicator narratives, tables and challenges/lessons reports | [README](ar-generator-service/README.md) |
| Chatbot | Query AICCRA reporting data through Bedrock Agents and a Knowledge Base | [README](chatbot-service/README.md) |
| CLARISA-Agresso | Match institutions between Agresso and CLARISA | [README](clarisa-agresso-service/README.md) |
| Fast Response | Apply a caller-supplied instruction to input text with Bedrock | [README](fast-response-service/README.md) |
| Mapping | Resolve staff/institution names to catalog identifiers | [README](mapping-service/README.md) |
| Partner Request Support | Match proposed institutions, review candidates and support CLARISA request decisions | [README](partner-request-support/README.md) |
| QA | AI Review of PRMS metadata and Quality Assessment of W3/Bilateral results | [README](qa-service/README.md) |
| Text Mining | STAR, PRMS, AICCRA and Bulk CapDev extraction, with a Bulk Upload frontend | [README](text-mining-service/README.md) |

For agent-assisted work, read the shared [AGENTS.md](AGENTS.md) and the service's nested instructions before editing. API, architecture and product guides are linked from each reviewed service README.

## Repository structure

```text
ai-services/
├── AGENTS.md                      # Shared working rules and branch workflow
├── admin-module/                  # Next.js administration application
├── ai-feedback-service/           # DynamoDB interaction/feedback API
├── ai-insights-service/           # STAR overviews and Prompt Manager API
├── ar-generator-service/          # AICCRA reports and static review interface
├── chatbot-service/               # AICCRA Bedrock Agent API and HTML interface
├── clarisa-agresso-service/       # Institution mapping scripts
├── fast-response-service/         # General-purpose Bedrock text response API
├── mapping-service/               # Staff/institution catalog matching API
├── partner-request-support/       # Institution review API and Next.js frontend
├── qa-service/                    # PRMS AI Review and Quality Assessment API
└── text-mining-service/           # Extraction API/MCP and Bulk Upload frontend
```

## Service capabilities

### Admin Module

A Next.js administration application with API routes for projects/products, users, prompt versions and prompt access. DynamoDB stores application records. Use its package manifest for the actual scripts/dependency versions and inspect configuration and access behavior before running it; no service README is currently included in this directory.

### AI Feedback

The active API records interactions through `POST /api/interactions` and can attach feedback later using the returned ID. DynamoDB is active storage; S3 files are a historical implementation. Negative feedback can attempt an email job through RabbitMQ. Search, summary, update and notification limits are documented in the [API guide](ai-feedback-service/docs/API.md). Importing the application can create its environment-specific table.

### AI Insights

Generates project overviews from STAR project/results context, supported documents in S3 and optional caller text. It can retrieve saved overviews, delete selected project files and read/replace the managed overview prompt. Prompt replacement affects future generation, not cached results. The implementation is a backend API, with no frontend in this service tree. See the [backend guide](ai-insights-service/backend/README.md) and [API contract](ai-insights-service/docs/API_GUIDE.md).

### AR Generator

Produces AICCRA mid-year/annual indicator narratives, indicator tables and challenges/lessons reports. The service-main path uses SQL Server, Amazon S3 Vectors and Bedrock, with a static HTML review/download interface. Development has a different local data path; preserve that distinction when integrating. See the [production/local comparison](ar-generator-service/docs/BRANCH_DIFFERENCES.md).

### Chatbot

FastAPI forwards questions, metadata filters and session/memory IDs to a configured Bedrock Agent and Knowledge Base. The HTML interface calls fixed chat/interaction destinations; serving it locally does not redirect those calls. Service-main includes Lambda packaging but no Streamlit entry point or local SQL/conversion tooling. Model selection and memory behavior depend on external agent settings. See the [interface guide](chatbot-service/interface/README.md).

### CLARISA-Agresso

A Python institution-mapping application that reads Agresso records, retrieves CLARISA institutions and produces match reports. Its modules include Supabase embedding-based matching and direct CLARISA OpenSearch matching. Use the [service README](clarisa-agresso-service/README.md) and inspect the selected script/configuration before execution; this directory is not documented as a standalone FastAPI service.

### Fast Response

A caller supplies an instruction and input text; Bedrock generates the returned text. Typical tasks include summarization, rewriting, translation and drafting. There is no dedicated frontend, retrieval index or conversation store. See the [API guide](fast-response-service/docs/API_GUIDE.md).

### Mapping

Matches staff and institution names using text/fuzzy OpenSearch retrieval, followed by an external LLM API selecting or rejecting a candidate. Staff identifiers come from STAR's carnet field and institution identifiers from CLARISA codes. This is not an embedding/vector-search implementation. See the [API guide](mapping-service/docs/API_GUIDE.md).

### Partner Request Support

A FastAPI backend and static-exported Next.js frontend support institution matching, manual review, web research and an optional automated decision flow. CLARISA authentication, cache selection and frontend destinations depend on the service branch/environment. See the [backend guide](partner-request-support/backend/README.md), [frontend guide](partner-request-support/frontend/README.md) and [API contract](partner-request-support/docs/API_GUIDE.md).

### QA

Two separate PRMS workflows share the service: **AI Review** at `POST /api/prms-qa` improves metadata and reviews impact-area scores; **Quality Assessment** at `POST /prms/quality-assessment` returns overall, section and evidence verdicts for W3/Bilateral results. Authentication differs between these routes. See the [API guide](qa-service/docs/API_GUIDE.md) rather than assuming one shared contract or access policy.

### Text Mining

FastAPI and MCP implement four workflows: STAR document extraction, PRMS multisource extraction, AICCRA document extraction and STAR Bulk CapDev spreadsheet extraction. A separate Next.js Bulk Upload application supports review and submission to STAR, alongside the AICCRA static interface. Inputs, authentication and side effects differ by workflow. See the [API guide](text-mining-service/docs/API_GUIDE.md) and [Bulk Upload frontend guide](text-mining-service/frontend/README.md).

## Setup and technology choices

| Area | Repository patterns; verify per service |
| --- | --- |
| Python APIs | FastAPI/Pydantic, Uvicorn locally and Mangum for applicable Lambda handlers |
| Dependencies | Service-local requirements/pyproject; lockfiles exist only in some services. Inspect what Docker installs |
| Models and retrieval | Bedrock, externally configured Agents/Knowledge Bases, S3 Vectors, OpenSearch, LanceDB and other service-specific providers |
| Storage/integrations | S3, DynamoDB, SQL Server, MySQL, Supabase, STAR, PRMS, CLARISA and RabbitMQ as used by each application |
| Frontends | Next.js/React applications and static HTML; package managers, Node versions and deployment modes differ |
| Runtime/deployment | Python 3.13 is common; native drivers and frontend runtimes have separate requirements. Inspect each service guide and deployment definition |

Start from the selected service guide instead of installing everything at the repository root. For example, [Fast Response local setup](fast-response-service/README.md#quick-start) uses its own requirements and launcher, [AI Insights](ai-insights-service/backend/README.md) runs from backend/, and [Bulk Upload](text-mining-service/frontend/README.md) has its own Node/runtime checks. No single command covers all services.

## Branch and contribution workflow

The normal promotion path is:

```text
task branch based on the service development branch
    → dev-<service> → main-<service> → staging → main
```

Actual names are listed in [AGENTS.md](AGENTS.md#branch-and-integration-workflow); directory names do not always equal branch suffixes. A branch contains the entire monorepo snapshot, so inspect the complete diff before integration. The maintainer handles release merges unless explicitly delegated.

Keep service-specific documentation alongside its code. After a development-to-service-main merge, compare the complete service trees and adapt guides for files, routes and intentional production settings that differ. Shared navigation/rules can be updated in staging for consolidation into main; do not merge all of main into a service branch merely to obtain documentation.

Read the current GitHub Actions branch/event filters before pushing or opening a PR. Some workflows invoke Jenkins even for documentation changes. An accumulated staging PR may include dependency, frontend or deployment changes as well as documentation; describe the actual diff and the validation it requires.

## Configuration, access and validation

Keep `.env`, credentials, generated exports/logs and real reporting data out of commits. Templates are examples; branch names do not automatically select environment variables or deployment destinations. Some interfaces have fixed API/analytics URLs that `.env` does not override.

Inbound authentication differs by service and endpoint. AWS IAM authorizes outbound AWS access; it does not establish HTTP caller authentication. Consult the service contract for token/API-key/ownership checks and do not infer authorization from email entry or CORS.

Use the checks defined by the relevant service and inspect scripts/imports before running them. Starting Feedback can create a DynamoDB table, and other calls can invoke paid models, upload/delete data, submit records or queue notifications. Static health responses and offline tests do not establish live provider, pipeline or deployment availability.

For service-specific support, use the linked README and implementation guides. For shared workflow questions or proposals, open a repository issue with the affected service, branch and reproducible context.
