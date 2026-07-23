# PRMS AI-Assisted Extraction: Implementation Specification

> **Source of truth:** [`bilateral-ai-workflow-ai-consolidated.md`](bilateral-ai-workflow-ai-consolidated.md)
>
> **Target service:** `text-mining-service`
>
> **Target product:** PRMS bilateral reporting
>
> **Status:** Draft for implementation
>
> **Scope:** AI-assisted extraction only. AI Review is explicitly excluded.

---

## 1. Purpose

Refactor the existing PRMS mining flow so one request can analyze documents, audio, free text, or any combination of these source groups. All three groups are independently optional, but at least one non-empty source is required. Independent source extraction must run concurrently. Once every source has been converted to text, the service must identify candidate results across the combined corpus, run a final model-based validation stage, and return the same logical mining response currently consumed by PRMS.

The implementation must:

- Keep the existing `POST /prms/text-mining` endpoint.
- Move PRMS mining out of `app/llm/mining.py` into a dedicated PRMS module.
- Preserve STAR behavior in `app/llm/mining.py`.
- Authenticate the PRMS HTTP endpoint only through CLARISA using the `X-API-Key` header.
- Remove PRMS token and `environmentUrl` authentication from both HTTP and MCP contracts.
- Preserve Slack success/failure notifications.
- Preserve interaction tracking.
- Support all agreed initial result types except Knowledge Product.
- Minimize latency without sacrificing deterministic response validation.

---

## 2. Scope

### 2.1 In scope

- Multisource request handling.
- Zero or more S3 document keys or directly uploaded documents.
- Zero or one non-empty free-text source.
- Zero or more audio sources referenced by S3 key and transcribed through an adapter after download.
- Validation that at least one document, audio, or free-text source is present.
- Concurrent source extraction with bounded workers.
- Combined-corpus chunking and retrieval.
- Candidate discovery and MDS extraction.
- Initial support for five result types.
- A final model validation pass over extracted candidates.
- Deterministic Pydantic validation after model calls.
- Existing OpenSearch field mapping and organization cleanup where applicable.
- CLARISA `X-API-Key` validation at the FastAPI boundary.
- Slack notifications and interaction tracking.
- Focused unit and API tests.

### 2.2 Out of scope

- AI Review of an existing PRMS result.
- Traffic-light ratings.
- Evidence mismatch detection after a result is created.
- Reanalysis triggered from the PRMS result form.
- Draft creation, persistence, promotion, sharing, or deletion.
- RabbitMQ job orchestration in PRMS.
- PRMS frontend changes.
- Email, WebSocket, or center webhook notifications.
- ToC extraction or validation.
- Impact area scoring.
- Knowledge Product extraction.
- Changes to STAR, AICCRA, or STAR Bulk CapDev mining behavior.

---

## 3. Supported Result Types

The initial release must identify and extract:

1. `Capacity Sharing for Development`
2. `Policy Change`
3. `Innovation Development`
4. `Innovation Use`
5. `Other Output / Other Outcome`

`Knowledge Product` must not be identified or returned by this implementation. If source content only supports Knowledge Products, the response is:

```json
{
  "results": []
}
```

The canonical field inventory for Innovation Use and Other Output / Other Outcome must be supplied by PRMS before their Pydantic models and prompt rules are considered complete. Field names must not be invented from UI labels.

---

## 4. Current-State Constraints

The implementation starts from these current behaviors:

- `POST /prms/text-mining` accepts one S3 `key` or one uploaded `file`.
- It requires form fields `token` and `environmentUrl`.
- The MCP tool authenticates those fields through `PrmsAuthMiddleware`.
- `process_document_prms` lives in `app/llm/mining.py` alongside STAR mining.
- Document parsing supports PDF, DOCX, TXT, XLS/XLSX, and PPTX, but not legacy DOC.
- PRMS uses one monolithic prompt covering three result types.
- `MiningResponse` accepts a union of three Pydantic result models.
- Model usage is logged, but `invoke_model` returns only model text.
- Slack and interaction tracking are implemented around the current PRMS function.

The refactor must not alter the `process_document` STAR path or its authentication.

---

## 5. Architectural Decisions

### D1. Dedicated PRMS package

Remove `process_document_prms` from `app/llm/mining.py`. Place all new PRMS orchestration in a dedicated package, following the existing product-specific AICCRA and bulk-upload patterns.

Recommended structure:

```text
app/
|-- llm/
|   |-- star_mining/
|   |   `-- mining.py                    # STAR pipeline orchestration
|   |-- prms_mining/
|   |   |-- __init__.py
|   |   |-- mining.py                    # PRMS pipeline orchestration + format_mining_response
|   |   |-- source_extraction.py         # bounded parallel extraction
|   |   |-- models.py                    # internal source/invocation models
|   |   `-- prompt_builder.py            # prompt composition
|   |-- shared/
|   |   |-- organization_fields.py       # clean_organization_fields (STAR + PRMS post-mapping)
|   |   `-- ...
|   `-- ...
|-- schemas/
|   |-- star_mining_schemas.py           # STAR result schemas (CapDev, Policy, Innov Dev)
|   `-- prms_mining_schemas.py           # PRMS result schemas (5 supported indicators)
`-- utils/
    `-- prompt/
        |-- prompt_prms.py               # common prompt and composition exports
        `-- prms/
            |-- common.py
            |-- capacity_sharing.py
            |-- policy_change.py
            |-- innovation_development.py
            |-- innovation_use.py
            |-- other_output_outcome.py
            `-- final_validation.py
```

The exact prompt file split may be reduced if the modules remain independently testable. Pipeline orchestration, source extraction, and prompt content must not be placed in one large file.

### D2. One extraction model call, modular prompt content

The initial implementation will use one extraction model invocation for all five result types, not one invocation per type.

The extraction prompt will be assembled from:

- Common behavior and output rules.
- Shared MDS field instructions.
- One independently maintained section per supported result type.
- A single discriminated JSON output schema.

Rationale:

- One call avoids sending the same corpus to five model invocations.
- It reduces total latency and token usage.
- It allows one source passage to support multiple result types.
- Modular prompt fragments preserve maintainability without introducing runtime fan-out.

This decision must be revisited only if evaluation fixtures show that one combined call cannot meet extraction-quality targets.

### D3. Separate final validation model call

After initial extraction, the pipeline will execute a second model invocation that validates the candidate set. Its output must use the same result schema.

The final validation stage receives:

- The candidate results produced by extraction.
- The supporting source excerpts used during extraction.
- The controlled reference data needed for validation.
- A versioned validation rule set.

The detailed domain rules are pending. The implementation may create the validator interface, prompt module, telemetry, and tests with an approved minimal rule set, but production activation is blocked until the final rules are supplied.

The validator must never:

- Add a candidate unsupported by the sources.
- Add a field value without source support.
- Change the output into prose.
- Introduce Knowledge Product or ToC.

### D4. Bounded parallel source extraction

Each independent document or audio source is processed by a worker. Concurrency must be bounded by configuration rather than creating an unbounded thread per source.

Recommended initial implementation:

```python
max_workers = min(PRMS_EXTRACTION_MAX_WORKERS, len(extractable_sources))
```

Use `ThreadPoolExecutor` because the current pipeline and MCP tool are synchronous and source retrieval/parsing is predominantly I/O-bound. The worker result order must be normalized back to request order using a stable `source_index`.

Free text requires no worker; it is normalized directly into the corpus.

### D5. Preserve the logical response contract

The endpoint continues to return the current logical result structure:

```json
{
  "results": []
}
```

When interaction tracking returns an ID, preserve the current wrapper behavior:

```json
{
  "json_content": {
    "results": []
  },
  "interaction_id": "..."
}
```

No draft IDs, job IDs, AI Review ratings, or frontend-specific metadata are added in this scope.

### D6. Fail the request if a declared source cannot be processed

The initial correctness policy is all-or-nothing source extraction. If any declared source cannot be downloaded, parsed, or transcribed, the request fails before model invocation.

This avoids returning candidates derived from an incomplete evidence set without telling existing clients. Partial success can be introduced later only with an explicit response-contract extension for per-source warnings.

### D7. CLARISA is the only PRMS authentication layer

The FastAPI endpoint must use:

```python
Depends(validate_with_clarisa("AI Text Mining - PRMS"))
```

The endpoint requires the `X-API-Key` header. It must no longer accept `token` or `environmentUrl`, and the MCP tool must not call `PrmsAuthMiddleware`.

This is intentionally different from the current STAR flow, which still has both CLARISA endpoint validation and its existing downstream authentication. STAR must remain unchanged.

---

## 6. HTTP API Contract

### 6.1 Endpoint

```http
POST /prms/text-mining
Content-Type: multipart/form-data
X-API-Key: <clarisa-api-key>
```

### 6.2 Request fields

| Field | Type | Required | Description |
|---|---|---:|---|
| `bucketName` | string | Conditional | S3 bucket used by `keys` and as the upload destination for direct files. Required when any document/audio source uses S3. |
| `keys` | array of string | No | Existing S3 object keys for documents. Repeat the form field for multiple values. |
| `files` | array of binary | No | Documents uploaded directly to the endpoint. |
| `text` | string | No | Free-text context supplied by the user. Blank or whitespace-only text is ignored. |
| `audio_keys` | array of string | No | Existing S3 object keys for audio sources. This is the only accepted audio input. |
| `user_id` | string | No | User identifier used only for interaction tracking. |

Documents, audio, and free text are independently optional source groups. At least one non-empty item across `keys`, `files`, `text`, and `audio_keys` is required.

Valid source combinations include:

- Documents only: one or more values across `keys` and `files`.
- Audio only: one or more values in `audio_keys`.
- Free text only: a non-blank `text` value.
- Any combination of documents, audio, and free text.

The endpoint must not require a document when audio or free text is present. It must not require audio or free text when documents are present. `bucketName` is not required for a free-text-only request.

Audio must be uploaded to S3 before this endpoint is called. The endpoint does not accept multipart audio binaries and must not define an `audio_files` field. For every `audio_keys` value, the mining pipeline downloads the object from `bucketName` and performs speech-to-text before prompt assembly.

Removed fields:

- `token`
- `environmentUrl`

### 6.3 Legacy field compatibility

To avoid an abrupt migration for existing callers, the first release should accept legacy singular aliases:

- `key` is normalized into `keys=[key]`.
- `file` is normalized into `files=[file]`.

Rules:

- Singular and plural fields may coexist.
- Exact duplicate S3 keys are deduplicated while preserving first occurrence order.
- Direct file names are not sufficient for deduplication; every uploaded file is treated as a distinct source.
- The OpenAPI description must mark `key` and `file` as deprecated aliases.
- `token` and `environmentUrl` receive no compatibility period because their removal is an explicit security-contract change.

### 6.4 Accepted source formats

The first implementation must define allowlists in configuration or constants, not infer support only from extensions.

Documents currently implementable with existing parsers:

- `.pdf`
- `.docx`
- `.txt`
- `.xls`
- `.xlsx`
- `.pptx`

Legacy `.doc` is requested by the product specification but unsupported by the current parser. It must remain rejected with HTTP 415 until a safe parser is selected and tested.

Audio formats and maximum duration are blocked on the transcription-provider decision. The endpoint must reject audio when no transcription provider is configured; it must not silently ignore it.

### 6.5 Validation rules

- Reject an empty source set with HTTP 400.
- Reject a missing `bucketName` when any S3 key or direct upload is present.
- Reject unsupported MIME type or extension with HTTP 415.
- Reject source-count, file-size, page-count, text-length, or audio-duration limits with HTTP 413.
- Reject duplicate content only if a reliable content hash is available; name equality alone is not duplicate proof.
- Reject an invalid or absent `X-API-Key` with the existing CLARISA validation behavior.
- Return HTTP 503 when CLARISA is unavailable, matching `validate_with_clarisa`.
- Do not log the API key or raw free text.

### 6.6 Example request

```bash
curl -X POST http://localhost:8000/prms/text-mining \
  -H 'X-API-Key: <api-key>' \
  -F 'bucketName=prms-policy-documents' \
  -F 'keys=prms/text-mining/files/report-1.pdf' \
  -F 'keys=prms/text-mining/files/attendance.docx' \
  -F 'files=@additional-context.txt' \
  -F 'audio_keys=prms/text-mining/audio/field-note.m4a' \
  -F 'text=Focus on outcomes reported during 2026' \
  -F 'user_id=user@example.org'
```

---

## 7. MCP Tool Contract

Keep the MCP tool name `process_document_prms` so the FastAPI client continues to use the established internal surface.

Target tool signature:

```python
async def process_document_prms(
    bucket: str | None = None,
    keys: list[str] | None = None,
    text: str | None = None,
    audio_keys: list[str] | None = None,
    user_id: str | None = None,
) -> dict:
    ...
```

Directly uploaded HTTP document files are uploaded to S3 by `app/mcp/client.py` before the MCP call. Their generated keys are appended only to `keys`. Audio is never uploaded through this endpoint; `audio_keys` must reference objects that already exist in S3.

The tool must not accept:

- `token`
- `environmentUrl`

The tool must not invoke `authenticate_prms`, `PrmsAuthMiddleware`, or any replacement user-token validation.

If `PrmsAuthMiddleware` has no remaining consumers after the refactor, its deletion should be handled as part of implementation cleanup. Do not delete it if another route still imports or uses it.

---

## 8. Internal Domain Models

Introduce typed internal models so extraction workers and prompt assembly do not exchange unstructured dictionaries.

### 8.1 Source descriptor

```python
class PrmsSourceType(str, Enum):
    DOCUMENT = "document"
    FREE_TEXT = "free_text"
    AUDIO = "audio"


class PrmsSource(BaseModel):
    source_id: str
    source_index: int
    source_type: PrmsSourceType
    bucket_name: str | None = None
    object_key: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    text: str | None = None
```

`source_id` is request-local and must not be presented as a persisted PRMS evidence ID.

### 8.2 Extracted source

```python
class ExtractedPrmsSource(BaseModel):
    source_id: str
    source_index: int
    source_type: PrmsSourceType
    content: str
    segments: list[str]
    page_count: int | None = None
    character_count: int
    extraction_seconds: float
```

Future provenance can replace `segments: list[str]` with richer page/offset objects. The initial model must at least retain `source_id` on every combined-corpus segment.

### 8.3 Model invocation result

Refactor PRMS model invocation so internal code receives both text and usage:

```python
class ModelUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class ModelInvocationResult(BaseModel):
    text: str
    usage: ModelUsage
    stop_reason: str
    model_id: str
    duration_seconds: float
```

Do not change STAR's `invoke_model` return type unless a separate, verified refactor is intentionally performed. PRMS may own its model client/helper inside the dedicated package to keep the change isolated.

---

## 9. Processing Pipeline

### 9.1 End-to-end sequence

```text
FastAPI /prms/text-mining
  1. Validate X-API-Key with CLARISA
  2. Normalize singular/plural request fields
  3. Validate source set and limits
  4. Upload direct document files to S3
  5. Call MCP process_document_prms

MCP process_document_prms
  6. Build typed source descriptors
  7. Run document/audio extraction workers concurrently
  8. Fail if any declared source fails
  9. Normalize free text and extracted content
 10. Chunk content with source identifiers
 11. Create embeddings and retrieve relevant combined-corpus chunks
 12. Build one modular extraction prompt
 13. Invoke Bedrock for candidate extraction
 14. Parse JSON and run preliminary structural validation
 15. Build final validation prompt from candidates + supporting excerpts
 16. Invoke Bedrock for final validation
 17. Parse JSON and validate the final discriminated schema
 18. Map controlled fields through OpenSearch
 19. Clean organization fields
 20. Format the current MiningResponse
 21. Track the interaction
 22. Send Slack success notification
 23. Return current logical response
```

On any exception, the MCP layer sends the existing PRMS failure notification and returns the established structured error behavior. HTTP status translation should be improved only where it can be done without changing unrelated MCP behavior.

### 9.2 Source extraction workers

`source_extraction.py` must expose one orchestration function and small type-specific adapters:

```python
def extract_sources(
    sources: list[PrmsSource],
    max_workers: int,
) -> list[ExtractedPrmsSource]:
    ...
```

Adapter responsibilities:

- `extract_document_source`: retrieve from S3 and parse by supported type.
- `extract_audio_source`: retrieve the object identified by `audio_keys` from S3 and transcribe it through the configured speech-to-text provider.
- `extract_free_text_source`: normalize text without using the worker pool.

Worker rules:

- Never mutate shared lists from worker threads.
- Collect each future result in the orchestration thread.
- Cancel outstanding futures when a terminal source error is detected where practical.
- Sort successful results by `source_index` before corpus assembly.
- Include `source_id` in errors and logs, but do not log document content.
- Use request-scoped temporary resources and clean them in `finally` blocks.
- Do not create one LanceDB table per source unless evaluation proves it necessary.

### 9.3 Corpus assembly

The combined corpus must preserve source boundaries:

```text
<source id="source-1" type="document" name="report.pdf">
...
</source>

<source id="source-2" type="free_text">
...
</source>
```

The implementation may use a structured internal representation instead of XML-like text, but the model must be able to distinguish source identity and source role.

Document sources are potential formal evidence. Free text and audio transcripts can be the only input used to identify and pre-fill a candidate result, but they are never eligible as formal evidence. The prompt must preserve that distinction without suppressing candidates from audio-only or free-text-only requests.

### 9.4 Retrieval and embeddings

The current PRMS flow embeds all chunks and retrieves chunks using the complete prompt as the query. The refactor should:

- Chunk each source independently so chunks never merge content from two sources.
- Attach `source_id` and stable chunk index metadata.
- Store all chunks for the request in one temporary LanceDB table.
- Use a concise, versioned retrieval query focused on the five supported result types rather than the full extraction prompt.
- Retrieve enough content to preserve cross-document relationships.
- Keep Excel rows as independent chunks if Excel remains supported.
- Clean the temporary table on success and failure according to existing cleanup conventions.

Embedding generation may also use bounded concurrency if the embedding provider and SDK are verified as thread-safe. This is an optimization after concurrent source extraction, not a prerequisite for the first refactor.

---

## 10. Prompt Architecture

### 10.1 Extraction prompt

Use one runtime prompt assembled from modular sections:

```text
SYSTEM/COMMON RULES
  - supported result types
  - no fabrication
  - source roles
  - ToC and Knowledge Product exclusions
  - multi-result behavior
  - JSON-only output

COMMON MDS FIELDS
  - title, description, keywords, geography, contacts/contributors

TYPE-SPECIFIC RULES
  - Capacity Sharing for Development
  - Policy Change
  - Innovation Development
  - Innovation Use
  - Other Output / Other Outcome

OUTPUT SCHEMA
  - discriminated result union

COMBINED SOURCE EXCERPTS
  - source identifiers and roles retained

REFERENCE CATALOGS
```

Prompt requirements:

- Return `{"results": []}` when no supported result is found.
- Do not return Knowledge Product candidates.
- Do not return ToC or impact area fields.
- Do not treat free text or audio as formal evidence.
- Permit free text or audio to be the sole basis for identifying a candidate draft while making no claim that either is formal evidence.
- Separate multiple results even if they share a source.
- Do not merge results solely because their titles or keywords are similar.
- Use exact discriminator values expected by Pydantic.
- Omit unsupported optional fields rather than inventing defaults, except where a canonical PRMS enumeration explicitly defines a not-collected value.
- Include source references internally if the response contract is extended for provenance.

### 10.2 Why not one prompt call per indicator

One call per indicator is not the initial design because it would:

- Repeat the same source corpus up to five times.
- Increase input tokens and Bedrock cost.
- Increase fan-out and aggregation complexity.
- Require deduplication of candidates found by multiple prompts.
- Risk inconsistent interpretations of shared fields.

Indicator-specific prompt files are still required for maintainability. They are composed into one invocation.

### 10.3 Final validation prompt

The final validator is a second, independent prompt and model call. It receives only:

- Extracted candidate JSON.
- Supporting excerpts selected for those candidates.
- The output schema.
- The approved validation rules.

Its baseline responsibilities are:

- Remove unsupported candidates.
- Remove or correct unsupported field values.
- Check cross-field arithmetic and enum consistency.
- Check result-type discriminator consistency.
- Detect duplicate candidates within the same request.
- Preserve valid candidates unchanged where possible.
- Return the same `{"results": [...]}` shape.

Detailed business validation rules will be added later. They must be maintained in `final_validation.py` with corresponding fixtures.

### 10.4 Model invocation metadata

Every model invocation should record:

- `model_id`
- input tokens
- output tokens
- stop reason
- duration

Prompt versions must be constants committed with the prompt source. Do not derive versions from timestamps at runtime.

---

## 11. Public Result Schemas

### 11.1 Discriminated union

Replace the ambiguous `Union` selection with a discriminator on `indicator` if compatible with the installed Pydantic version and current formatter.

The union must contain:

- `CapacityDevelopmentResult`
- `PolicyChangeResult`
- `InnovationDevelopmentResult`
- `InnovationUseResult`
- `OtherOutputOutcomeResult`

Knowledge Product must not be in the union.

### 11.2 Schema authority

Current classes remain the baseline for the existing three indicators. New models must be created only from canonical PRMS DTOs/catalogs. The functional names in the consolidation are not sufficient authority for field types or enum values.

### 11.3 Validation order

Use this order:

1. Parse extraction-model JSON.
2. Validate only the top-level shape and discriminator so malformed candidates do not reach the final prompt unnoticed.
3. Run final model validation.
4. Parse final JSON.
5. Validate the complete Pydantic discriminated union.
6. Map controlled fields through OpenSearch.
7. Validate again if mapping changes typed values.
8. Serialize with `exclude_none=True`.

Invalid candidates must not be silently coerced into another result type. Log candidate index, indicator, and validation error without logging the full source corpus.

---

## 12. Authentication and Security

### 12.1 Required changes

In `app/mcp/client.py`:

- Add `mis: str = Depends(validate_with_clarisa("AI Text Mining - PRMS"))` to the PRMS endpoint.
- Remove `token` and `environmentUrl` form fields.
- Remove them from endpoint documentation and MCP arguments.
- Keep the API key in the header only.

In `app/mcp/server.py`:

- Remove PRMS imports from `app.middleware.prms_auth_middleware` if no longer used.
- Remove `prms_auth_middleware` initialization if no longer used.
- Remove `authenticate_prms` if no longer used.
- Remove the PRMS authentication block from `process_document_prms`.
- Do not change STAR authentication code.

### 12.2 Logging restrictions

Never log:

- `X-API-Key`
- Full free-text context
- Audio transcripts
- Full extracted documents
- Full signed S3 URLs
- AWS credentials or bearer tokens

Logging may include:

- Request correlation ID when available
- User ID when supplied under the existing tracking policy
- Bucket name and sanitized object key where current policy permits it
- Source counts and types
- Stage durations
- Token usage
- Result counts
- Stable error codes

The existing PRMS success log currently emits the complete formatted response. The refactor must replace that with a result count and bounded, non-sensitive diagnostics.

---

## 13. Slack Notifications

Keep success and failure notifications in the MCP layer.

### Success notification

Include:

- Application: `AI-MCP Mining Service (PRMS)`
- Source count by type
- Candidate result count
- User identifier or `N/A`
- Total processing time

Do not include raw text, transcripts, API keys, signed URLs, or the complete list of object keys when it could exceed Slack limits.

### Failure notification

Include:

- Stable failure stage: validation, upload, extraction, retrieval, model extraction, final validation, mapping, or formatting
- Sanitized error summary
- Source count
- User identifier or `N/A`
- Total time elapsed when available

Slack failure must remain best-effort. A Slack outage must not replace or hide the original mining exception.

---

## 14. Interaction Tracking

Preserve `interaction_client.track_interaction` for requests with `user_id`.

Update tracking context to include:

```json
{
  "source_counts": {
    "document": 0,
    "free_text": 0,
    "audio": 0
  },
  "chunks_processed": 0,
  "results_count": 0,
  "supported_indicators": [],
  "model_used": "...",
  "extraction_input_tokens": 0,
  "extraction_output_tokens": 0,
  "validation_input_tokens": 0,
  "validation_output_tokens": 0,
  "stage_durations_seconds": {},
  "processing_steps": []
}
```

`user_input` must summarize source names/counts and must not contain the full free text or transcript. `ai_output` currently stores the full formatted response; its continued use must be reviewed against CGIAR data-retention policy. Until that decision is made, preserve compatibility but do not add source content to it.

Tracking failure remains non-fatal and must not change a successful mining response.

---

## 15. Error Handling

Define internal exceptions with stable categories:

| Exception/category | HTTP intent | Behavior |
|---|---:|---|
| `EmptySourceSetError` | 400 | Reject before upload or MCP call. |
| `SourceLimitExceededError` | 413 | Reject before model invocation. |
| `UnsupportedSourceTypeError` | 415 | Identify the rejected source safely. |
| `SourceDownloadError` | 422 or 500 | Fail the entire request. Distinguish missing object from AWS failure where possible. |
| `SourceExtractionError` | 422 | Fail the entire request. |
| `AudioTranscriptionUnavailableError` | 503 | Fail when audio was declared but provider is unavailable. |
| `ModelInvocationError` | 502 or 503 | Retry according to Bedrock policy, then fail. |
| `ModelOutputValidationError` | 502 | Do not return unvalidated model prose. |
| `FieldMappingError` | Current compatible behavior | Preserve fallback only if the resulting object still validates. |

The existing MCP tool catches errors and returns an error dictionary, which can obscure HTTP status codes. Implementation should add focused translation tests before changing that behavior. Do not broaden this task into a service-wide error-handling rewrite.

Model retries must be bounded and must not retry deterministic schema failures indefinitely. Source extraction workers must not retry unsupported formats.

---

## 16. Configuration

Add configuration through `app/utils/config/config_util.py` and environment variables rather than hardcoded limits:

| Variable | Purpose | Initial value |
|---|---|---|
| `PRMS_EXTRACTION_MAX_WORKERS` | Maximum concurrent source workers per request | To be load-tested; recommended starting value: 4 |
| `PRMS_MAX_SOURCES` | Total documents plus audio sources | Product/ops decision required |
| `PRMS_MAX_FILE_BYTES` | Per-file byte limit | Product/ops decision required |
| `PRMS_MAX_PDF_PAGES` | Per-PDF page limit | AI team decision required |
| `PRMS_MAX_TEXT_CHARS` | Free-text limit | AI team decision required |
| `PRMS_MAX_AUDIO_SECONDS` | Audio-duration limit | Provider/product decision required |
| `PRMS_FINAL_VALIDATION_ENABLED` | Feature flag for the second model stage until rules are approved | `false` before rule approval |
| `PRMS_AUDIO_TRANSCRIBER` | Configured transcription adapter | No default until selected |

Fail fast at startup for invalid numeric configuration. Do not silently convert an invalid worker count into unbounded concurrency.

---

## 17. Performance Requirements

The implementation must measure rather than assume its latency improvement.

Required stage timings:

- HTTP upload
- Source extraction total
- Slowest individual source extraction
- Chunking
- Embedding generation
- Retrieval
- Extraction model invocation
- Final validation model invocation
- Field mapping
- Total request duration

Performance rules:

- Parallelize only independent source extraction in the first implementation.
- Use bounded concurrency per request.
- Do not start the extraction prompt until all sources succeed.
- Use one extraction call and one final validation call.
- Avoid placing the complete raw corpus in both model calls; the final validator receives candidate-supporting excerpts only.
- Avoid repeated reference-file downloads by preserving the existing reference cache behavior.
- Do not cache user source content across requests.
- Keep temperature low and output token limits explicit.

No absolute latency SLA is defined yet. Before rollout, benchmark one, three, and maximum-source requests against the current single-document baseline.

---

## 18. Testing Strategy

### 18.1 Unit tests

Add tests for:

- Singular and plural request normalization.
- Duplicate key normalization.
- Empty source rejection.
- Unsupported format rejection.
- Source worker ordering despite out-of-order completion.
- Worker failure cancelling/failing the request.
- Free text normalization and formal-evidence-ineligible labeling.
- Audio adapter success, unsupported state, and provider failure.
- Prompt composition includes exactly the five supported types.
- Prompt composition excludes Knowledge Product and ToC.
- Extraction JSON parsing.
- Final validation JSON parsing.
- Discriminated Pydantic validation for every supported type.
- Empty results.
- Field mapping fallback followed by schema validation.
- Separate usage accounting for both model calls.
- Interaction tracking failure remaining non-fatal.
- Slack failure not masking mining errors.

### 18.2 API tests

Test `POST /prms/text-mining` with:

- Missing API key.
- Invalid API key.
- CLARISA unavailable.
- One legacy `key`.
- Multiple `keys`.
- Multiple direct `files`.
- Free text only, without `bucketName`.
- Audio keys only, with no multipart audio upload.
- Mixed keys, files, and free text.
- Audio with configured transcriber.
- Audio without configured transcriber.
- No sources.
- Removed `token` and `environmentUrl` fields absent from OpenAPI.
- Existing logical response shape.

Mock CLARISA, S3, Bedrock, OpenSearch mapping, Slack, and interaction tracking. Tests must not require real AWS credentials.

### 18.3 Prompt evaluation fixtures

Create sanitized fixtures for each supported type:

- One clear positive example.
- One negative/no-result example.
- One document containing multiple result types.
- Multiple complementary documents supporting one result.
- Multiple documents supporting separate results.
- Contradictory source values.
- Free text without documentary support, which may still produce a candidate.
- Audio without documentary support, which may still produce a candidate.
- Knowledge Product-only content, expected to return no result.
- Content mentioning ToC, expected not to return ToC fields.

Evaluation must compare typed fields rather than exact generated prose. Final quality thresholds are a separate prompt-evaluation decision and must be documented before production.

### 18.4 Regression tests

- STAR `process_document` continues importing from `app/llm/mining.py`.
- STAR HTTP and MCP authentication remain unchanged.
- AICCRA and bulk CapDev imports remain valid.
- Existing PRMS one-key requests work through the deprecated singular alias.
- Interaction response wrapping remains compatible.

---

## 19. Implementation Sequence

### Phase 1: Separation and authentication

1. Create the dedicated `app/llm/prms_mining/` package.
2. Move PRMS pipeline behavior without functional changes.
3. Update `app/mcp/server.py` imports.
4. Remove `process_document_prms` from `app/llm/mining.py`.
5. Add CLARISA dependency to the PRMS HTTP endpoint.
6. Remove PRMS `token` and `environmentUrl` from HTTP and MCP.
7. Add regression tests for STAR and current single-key PRMS behavior.

### Phase 2: Multisource extraction

1. Add typed source models.
2. Add plural HTTP/MCP fields and legacy singular normalization.
3. Implement bounded source extraction workers.
4. Add free-text normalization.
5. Add the audio adapter contract and disabled/unavailable behavior.
6. Assemble one source-aware corpus.
7. Add source and performance telemetry.

### Phase 3: Result coverage and prompt modularization

1. Obtain canonical PRMS MDS contracts.
2. Add Innovation Use and Other Output / Other Outcome schemas.
3. Split prompt rules into common and indicator-specific modules.
4. Compose one extraction prompt for five types.
5. Add discriminated schema validation.
6. Add prompt fixtures and quality evaluation.

### Phase 4: Final validation stage

1. Confirm the final business validation rules.
2. Implement the validator interface and prompt.
3. Return structured model usage from both invocations.
4. Add final validation fixtures and failure handling.
5. Enable `PRMS_FINAL_VALIDATION_ENABLED` in test environments.
6. Benchmark latency and cost before production activation.

### Phase 5: Hardening

1. Confirm source, page, text, and audio limits.
2. Review interaction/log retention.
3. Load-test concurrent requests and worker limits.
4. Verify temporary LanceDB cleanup on all failure paths.
5. Validate OpenAPI and local startup.

---

## 20. Acceptance Criteria

### API and authentication

- `POST /prms/text-mining` remains the public endpoint.
- A valid CLARISA `X-API-Key` is required.
- `token` and `environmentUrl` are absent from the PRMS endpoint and MCP tool.
- STAR authentication is unchanged.
- Legacy singular `key` and `file` aliases remain temporarily functional.

### Separation and maintainability

- `app/llm/mining.py` contains no PRMS pipeline function or PRMS prompt import.
- PRMS pipeline orchestration lives in its dedicated package.
- Source extraction, prompt composition, and orchestration are independently testable.
- Prompt rules are modular by result type even though runtime extraction uses one model call.

### Multisource behavior

- Documents, audio, and free text are independently optional.
- At least one non-empty source across those three groups is required.
- Document-only, audio-only, free-text-only, and mixed-source requests are accepted.
- Audio input is accepted only through `audio_keys`; multipart audio binaries are rejected and are absent from OpenAPI.
- Independent document/audio extraction runs concurrently with a bounded worker count.
- Model extraction starts only after all declared sources are successfully extracted.
- Source order and identity are preserved in the combined corpus.
- Free text and audio may identify candidates but are labeled as ineligible for formal evidence.
- A failed declared source fails the request before model invocation.

### AI extraction

- The service identifies zero, one, or multiple candidates.
- It supports the five initial result types.
- It does not return Knowledge Product, ToC, or impact area fields.
- It performs one combined extraction model call.
- Extracted candidates pass through the final validation stage once its approved rules are enabled.
- Final output passes deterministic Pydantic validation.
- Empty valid extraction returns `{"results": []}`.

### Compatibility and operations

- Existing logical response and optional interaction wrapper remain compatible.
- Slack success and failure notifications remain active.
- Interaction tracking remains active and non-fatal.
- Extraction and validation token usage are recorded separately.
- Logs do not contain API keys, raw source content, free text, or audio transcripts.
- Targeted tests pass and the MCP client starts with the updated imports.

---

## 21. Blocking Decisions

Implementation can begin with package separation, authentication, request normalization, and concurrent document extraction. The following items block full feature completion:

1. Canonical PRMS MDS contracts for Innovation Use and Other Output / Other Outcome.
2. Approved final validation-prompt rules.
3. Speech-to-text provider and accepted S3-hosted audio formats.
4. Maximum source, file, page, text, audio, and token limits.
5. Confirmation of whether XLS/XLSX/PPTX remain accepted in bilateral extraction.
6. Decision to support or reject legacy DOC permanently.
7. Prompt-evaluation quality thresholds.
8. CGIAR policy for confidential data, PII, and interaction retention.

These blockers must not be resolved by silently inventing contracts or default business rules during implementation.
