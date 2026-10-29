# Partner Request Support design

This is the implemented development-branch design. Deployment templates and configuration are not proof of live infrastructure state. Start with the [product workflows](PRODUCT_OVERVIEW.md) or [API guide](API_GUIDE.md).

## Components and calls

```text
Browser: Next.js static app
  ├─ CLARISA authentication (fixed environment URL)
  └─ FastAPI API (NEXT_PUBLIC_API_URL)
       ├─ CLARISA institutions / pending requests / catalogs / create / respond
       ├─ Supabase: institution vectors + branch-specific match cache
       ├─ AWS Bedrock: Titan embeddings + Claude formatting/rules/duplicate checks
       ├─ AWS Translate: English search alternative
       ├─ OpenAI Responses web search
       ├─ S3: Excel template
       └─ RabbitMQ email microservice: manual-review notifications
```

The browser calls Python directly. In deployment, API Gateway/Lambda invokes Mangum's `main.handler` in the container; local development uses `api:app` with Uvicorn. Next.js exports static assets for separate S3/CloudFront hosting. There is no deployed Next.js server acting as a backend gateway in this configuration.

## Manual-review pipeline

1. Excel upload or pending-request processing synchronizes the CLARISA institution catalog with Supabase, including embeddings and deletion of obsolete entries.
2. Excel processing can create CLARISA requests before matching. Pending processing recovers an empty snapshot from CLARISA, otherwise reuses the existing snapshot, and chooses explicit IDs or the ten oldest pending requests.
3. Match cache is checked by normalized name. Uncached rows use hybrid search and reranking; the batch API reassigns current request IDs, while other cached source metadata may remain from the earlier result.
4. Match/candidate results and optional web research are returned to the browser. Cache entries are written for computed results.
5. A separate human response call looks up upstream metadata and submits accept/reject with the supplied token/user.

[Matching details](../backend/docs/HOW%20THE%20SEARCH%20WORKS.md) distinguish vector retrieval weights from final scores. Manual-review labels differ from [automatic decision tiers](API_GUIDE.md#automated-evaluation).

## Automatic decision pipeline

The automatic route can create a request first, then searches the institution snapshot without the manual batch route's catalog-sync/cache orchestration. Excellent matches reject as duplicates; good/very-good candidates receive a same-institution check. Remaining cases use web research and rules evaluation to choose ACCEPT or MANUAL_REVIEW.

ACCEPT/REJECT are sent upstream only under the selected response/creation mode and available response inputs. MANUAL_REVIEW leaves the request pending and attempts notifications. Completeness metadata is informational on the web/rules path. Creation and response are not atomic; retries require checking external state.

## State and external clients

| State/client | Location and boundary |
| --- | --- |
| Institution snapshot | Supabase `clarisa_institutions_v2`; Titan vectors, SQL functions, synchronized source data |
| Match cache | `partner_request_cache_test` in development; `partner_request_cache_prod` in service-main; selected in code/SQL |
| Pending snapshot | Module-global Python list, refreshed from CLARISA; isolated per process/Lambda instance |
| Frontend session | Token/user/result state in React hooks |
| Provider clients | Constructed during imports for Supabase, OpenAI, and AWS; configuration can prevent startup |
| Email | RabbitMQ publisher; missing configuration logs/simulates rather than delivering |

Synchronization can invalidate cached matches. Cache hits avoid recomputing matches; they do not establish current institutional eligibility. Module globals are not a cross-instance work queue, lock, or transactional request state.

## Models and configuration boundaries

- Embeddings use `amazon.titan-embed-text-v2:0` with 1,024 dimensions. Embedding/translation clients explicitly use `us-east-1`.
- OpenAI web research uses `gpt-5-mini` with the web-search tool.
- Manual report formatting and default automatic rules evaluation use `us.anthropic.claude-sonnet-4-5-20250929-v1:0`.
- Automatic same-institution verification defaults to `us.anthropic.claude-haiku-4-5-20251001-v1:0`.
- `BEDROCK_RULES_MODEL_ID` and `BEDROCK_DUPLICATE_CHECK_MODEL_ID` override their respective clients, not every model in the pipeline. Web-research Bedrock uses `AWS_REGION` with a `us-east-1` fallback.

Verify model access in the intended AWS account/region. This code review does not measure cost, latency, accuracy, or live provider availability.

## Operational boundaries

CORS, login destination, cache constants/SQL, and environment badge differ between branches. See [branch differences](BRANCH_DIFFERENCES.md). The backend has no general FastAPI authentication dependency; body tokens serve upstream calls. Infrastructure controls must be assessed separately.

Health only reports process status. Local logs can contain institution/request details and rotate under `backend/data/logs`; Lambda logs use stdout. Do not commit logs or real payloads. Review existing live example scripts before running checks, and stub provider/data/email calls for offline validation.
