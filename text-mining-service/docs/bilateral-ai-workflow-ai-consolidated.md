# PRMS Bilateral Workflow: AI Scope Consolidation

> **Source document:** [`bilateral-ai-workflow-spec.md`](bilateral-ai-workflow-spec.md)
>
> **Epic:** P2-2965 - Bilateral module for centers
>
> **Lead story:** P2-3100 - Create New Bilateral Result Form Workflow
>
> **Scope:** responsibilities of the AI team and AI service. Frontend, PRMS persistence, and orchestration are mentioned only when they define an input, output, dependency, or constraint for AI.
>
> **Status:** functional consolidation to be used as the source for implementation specifications.

---

## 1. Objective

Adapt PRMS text mining to support bilateral reporting through two distinct AI capabilities:

1. **AI-assisted extraction:** analyze one or more related sources, identify zero or more candidate results, and extract their applicable Minimum Data Standards (MDS) fields, excluding Theory of Change (ToC).
2. **AI Review:** assess an existing result against its evidence, provide field-level quality guidance, and detect inconsistencies when the evidence set changes.

The initial implementation covers AI-assisted extraction only. AI Review remains future scope.

AI reduces data-entry effort and provides quality guidance. It does not approve results, block submission, or replace human validation.

---

## 2. Responsibility Boundaries

### 2.1 AI team responsibilities

- Retrieve and process sources made available by PRMS through secure references.
- Extract content from supported documents and free text, and download audio from S3 for speech-to-text processing.
- Combine multiple documents and context sources into one analysis corpus.
- Apply source eligibility and content-quality rules for the AI route.
- Identify multiple independent candidate results in one corpus.
- Classify each candidate by result type and extract its applicable MDS fields.
- Return structured results with validation, confidence, provenance, and warnings.
- Maintain and version prompts, output schemas, and AI evaluation criteria in this service.
- Report model usage and technical telemetry required for audit and cost monitoring.
- In future scope, perform consolidated AI Review and evidence mismatch detection.

### 2.2 Responsibilities outside the AI team

- Building upload, draft-list, traffic-light, and feedback user interfaces.
- Authenticating PRMS users or deciding who can view a draft.
- Owning PRMS S3 upload policies, signed URL lifecycle, jobs, and queues.
- Creating, promoting, sharing, or deleting Draft results.
- Converting `DraftEvidence` into formal evidence.
- Sending email, WebSocket, or center webhook notifications.
- Persisting bilateral workflow state or executing result status transitions.
- Selecting primary or contributing Science Programs.
- Extracting, suggesting, or evaluating ToC.
- Approving, rejecting, or blocking submission of a result.

PRMS owns workflow orchestration and domain persistence. The AI service processes requests and returns structured analysis; it does not write directly to the PRMS database.

---

## 3. Confirmed Functional Principles

| Principle | AI rule |
|---|---|
| Advisory AI | AI output never represents a mandatory validation, submission decision, approval, or rejection. |
| MDS scope | AI extracts and eventually reviews the applicable MDS fields. Extra-MDS fields are excluded. |
| ToC excluded | ToC is not extracted, populated, scored, or flagged as missing. |
| Consolidated review | Future AI Review evaluates evidence quality, clarity, completeness, geography, and field consistency in one operation. |
| Multiple sources | Initial extraction considers all documents and context sources submitted in the same request. |
| Optional source groups | Documents, audio, and free text are independently optional. A request must contain at least one non-empty source group and may contain any combination of the three. |
| Multiple results | A corpus may support zero, one, or several candidate results. |
| No fabrication | Unsupported values are omitted or represented as not collected according to the agreed contract. |
| Public evidence only | Until an institutional policy says otherwise, the AI route accepts only public, non-confidential evidence. |
| Provenance | Every proposed or assessed value must be traceable to supporting source content. |
| Optional reanalysis | In future AI Review scope, users decide whether to accept an evidence mismatch or request reanalysis. |

### ToC conflict resolution

The source document once states that missing ToC could receive a yellow rating. Later high-confidence decisions D3 and D26 exclude ToC from both extraction and AI Review. This consolidation adopts the later decision: **AI does not process ToC in any way**.

---

## 4. Required AI Capabilities

### 4.1 Capability A: Bilateral AI-assisted extraction

#### Purpose

Convert a set of complementary sources into a structured list of bilateral result candidates.

#### Functional inputs

- A PRMS request or correlation identifier.
- Zero or more document sources, provided through secure references or direct uploads handled by the existing API surface.
- File name, MIME type, and technical metadata for every document.
- Zero or one non-empty free-text source.
- Zero or more audio sources referenced by S3 object key. Audio binary content is never sent directly to the mining endpoint.
- Project and Science Program context needed to guide extraction, without asking AI to determine ToC.
- Current catalogs required to return PRMS-compatible identifiers.
- Requested output-schema version, once contract versioning is introduced.

Documents, audio, and free text are independently optional. At least one of these three source groups must be present. All of the following are valid: documents only, audio only, free text only, or any combination of them.

Documents may use the existing S3-key or direct-upload paths. Audio must already be stored in S3 before the mining request; the endpoint receives its object key, downloads it from S3, and performs speech-to-text processing inside the AI pipeline.

#### Expected processing

1. Retrieve and validate all sources.
2. Extract source content in parallel using bounded workers.
3. Preserve provenance to the source, page, sheet, or segment where possible.
4. Normalize all extracted content into a common internal source model.
5. Allow free text and audio transcripts to support candidate identification while marking them as ineligible for formal evidence.
6. Detect candidate results and separate distinct results found in the same corpus.
7. Classify each candidate by supported result type.
8. Extract common and type-specific MDS fields.
9. Map controlled values to current catalogs.
10. Run final result validation before returning the response.
11. Return schema-valid output, warnings, provenance, and usage telemetry.

#### Minimum functional output

- Processing status and contract version.
- Prompt and model version.
- Sources processed, rejected, or only partially processed.
- `results`, which may be an empty list.
- Applicable MDS fields for every candidate.
- Candidate-level and field-level confidence where defined.
- Source provenance for extracted fields.
- Missing, unsupported, or contradictory fields.
- Quality and exclusion warnings.
- Input/output token usage and total processing duration.
- Stable error codes for recoverable and terminal failures.

PRMS must be able to consume the response without parsing model-generated prose. Exact JSON schemas belong in the extraction implementation specification.

### 4.2 Capability B: Consolidated AI Review (future scope)

AI Review will assess a bilateral result in Editing against its current formal evidence. It will cover evidence quality, MDS completeness, title and description clarity, geography plausibility, contributor consistency, type-specific consistency, and evidence mismatch detection.

It will return a `GREEN`, `YELLOW`, or `RED` rating per applicable field, an explanation, an evidence-backed suggestion where appropriate, and source provenance. It will not return a blocking `can_submit`, `approved`, or equivalent decision.

The initial implementation specifications must not include AI Review endpoints, prompts, schemas, or workflow changes. They may only preserve extension points that avoid coupling extraction to review.

---

## 5. Result-Type and Field Coverage

### 5.1 Result types in the overall consolidated scope

The source specification lists:

1. Innovation Development.
2. Capacity Sharing for Development.
3. Knowledge Product.
4. Innovation Use.
5. Policy Change.
6. Other Output / Other Outcome.

The initial AI-assisted extraction implementation explicitly excludes Knowledge Product. Therefore, its supported set is:

- Innovation Development.
- Capacity Sharing for Development.
- Innovation Use.
- Policy Change.
- Other Output / Other Outcome.

The current PRMS mining implementation supports only Capacity Sharing for Development, Policy Change, and Innovation Development. Innovation Use and Other Output / Other Outcome are required additions.

### 5.2 Field groups

| Group | Expected AI coverage |
|---|---|
| General information | Result type and level, title, short title when applicable, description, and keywords. Status, phase, and source are PRMS context rather than AI inference. |
| Project context | May be supplied to AI as context. AI does not select Reporting Project, Science Program, center ID, or source. |
| Geography | Geographic scope, regions, countries, and subnational locations supported by sources. |
| Evidence | Relevance, accessibility, age, typology, public status, and relationship to the claim. |
| Contributors | Centers and partners stated in the sources, mapped through controlled catalogs. |
| Innovation Development | Nature/type, phase or readiness level, users, and the canonical MDS fields for this type. |
| Capacity Sharing | Training type, modality, duration, dates, participant data, and associated organizations. |
| Innovation Use | Use type, adoption stage and scale, beneficiary data, and canonical type-specific MDS fields. |
| Policy Change | Policy type, stage, scope, and evidence supporting the stage or change. |
| Other Output / Outcome | Output type, outcome description, and contribution evidence. |
| Theory of Change | **Entirely out of scope.** |
| Impact area scores | **Out of scope.** Assigned by the program during consolidation. |

The source field inventory is functional rather than contractual. Before implementation, PRMS must provide the canonical DTO field names, types, required status, enumerations, and identifiers for each supported result type.

---

## 6. Sources and Evidence Rules

### 6.1 Source roles

| Source | AI use | Eligible as formal evidence |
|---|---|---|
| PDF | Extraction and future review | Yes, after explicit user selection in PRMS. |
| DOCX / DOC | Extraction and future review | Yes, after explicit user selection in PRMS. |
| TXT | Extraction and context | Product must confirm whether TXT can become formal evidence. |
| Free text | Candidate identification and extraction context | No. |
| Audio referenced from S3 / generated transcript | Candidate identification and extraction context | No. |

AI may identify a document as an evidence candidate, but it does not decide or persist formal-evidence promotion.

### 6.2 Exclusion and warning criteria

| Criterion | Expected behavior |
|---|---|
| Inaccessible or unreadable source | Do not use its content; return a structured reason and manual-review warning. |
| Evidence outside the accepted age | Warn or exclude according to the final threshold. Current guidance is 3 to 5 years with justified exceptions. |
| Unrelated to food, agriculture, or environment | Exclude it from the AI route and report the reason. |
| Insufficient content | Exclude or mark inconclusive; never invent metadata. |
| Confidential or non-public | Exclude while no CGIAR policy permits processing it. |
| Unsupported format | Reject that source with a stable error code. |
| Page, size, or token limit exceeded | Reject or partially process according to a rule still to be defined. |

Automated confidentiality detection must not be presented as a guarantee. PRMS must warn users and obtain confirmation before submission; AI may add preventive PII or sensitive-content detection once institutional policy defines it.

### 6.3 Evidence weight

- **Third-party evidence:** peer-reviewed publications, independent evaluations, and published datasets. It carries a stronger credibility signal.
- **Self-generated evidence:** internal reports, field notes, photographs, and attendance sheets. It is valid but has lower weight and may require additional context.

The exact scoring method depends on the evidence guide from Nicoletta and Maria Julia. No definitive thresholds should be hardcoded before that guide is available.

---

## 7. Confidence, Provenance, and Explainability

Each result and field should distinguish among:

- A value directly stated in a source.
- A value normalized or mapped to a catalog.
- A value inferred from sufficient evidence.
- A value contradicted by another source.
- A value not found or not sufficiently supported.

Field-level confidence and source references are preferable to a single opaque result score. Low confidence never authorizes filling an unsupported value. Contradictions must remain visible warnings rather than being resolved silently. If no valid result is identified, the service returns an empty `results` list.

The minimum threshold for retaining a suggestion remains open and should be calibrated by field and result type rather than assumed to be one global value.

---

## 8. Security and AI Governance

- PRMS and the AI service must use temporary, least-privilege access to S3 sources.
- Credentials, API keys, and secrets must never enter prompts, logs, or responses.
- Model input must be limited to content required for the requested operation.
- A PII detection or removal strategy must be defined before model invocation.
- Model, prompt, schema version, and relevant parameters must be recorded for each execution.
- Non-public evidence remains excluded until CGIAR defines an applicable policy.
- Bedrock residency, retention, and non-training behavior must be confirmed through governance rather than assumed.
- Logs must not store full documents or unrestricted model responses containing potentially sensitive information.

---

## 9. Observability and AI Metrics

The service must expose enough structured telemetry for PRMS to track:

- Input and output tokens per operation.
- Model, prompt, and schema versions.
- Total duration and relevant stage durations.
- Number of sources, pages, and segments processed.
- Number of candidates identified.
- Errors and exclusions by type.
- Confidence by candidate and field where enabled.

PRMS owns association with Center and Science Program and owns product metrics such as override, acceptance, draft conversion, feedback, and time to submission.

---

## 10. Current Service and Gaps

### 10.1 Reusable capabilities

- Existing `POST /prms/text-mining` HTTP endpoint and `process_document_prms` MCP tool.
- S3 document retrieval and direct upload handling.
- PDF, DOCX, TXT, Excel, and PPTX content extraction.
- Semantic chunking, embeddings, and LanceDB retrieval.
- Claude Sonnet invocation through AWS Bedrock.
- PRMS prompt and Pydantic models for three result types.
- Controlled field mapping through external catalogs/services.
- Interaction tracking, Slack notification, response time, and token logging.

### 10.2 Gaps

| Current gap | Required change |
|---|---|
| One document key or upload per request | Accept multiple documents plus optional free text and audio. |
| Sequential source processing | Extract independent sources concurrently with a bounded worker pool. |
| Legacy DOC is not parsed | Add a safe parser or remove DOC through an explicit product decision. |
| Three result types | Add Innovation Use and Other Output / Other Outcome; Knowledge Product stays excluded initially. |
| PRMS logic lives in shared `mining.py` | Move PRMS mining into a dedicated module and keep STAR behavior isolated. |
| PRMS token/environment authentication | Replace it with endpoint-level CLARISA `X-API-Key` validation only. |
| Extraction-only model call | Add a final validation model stage, with its detailed rules supplied separately. |
| Monolithic PRMS prompt | Compose a shared prompt from modular common and indicator-specific instructions. |
| No audio extraction adapter | Add a transcription abstraction and select its provider before implementation. |
| Output schema covers only three types | Extend the typed union and formatter for the five initial supported types. |
| Token usage is mainly logged | Return or track structured usage for extraction and validation separately. |
| No formal source limits | Define page, file, audio-duration, concurrency, timeout, and token limits. |

The current flow is a reusable foundation, not a sufficient contract for bilateral extraction.

---

## 11. External Dependencies

| Dependency | External owner | AI need |
|---|---|---|
| PRMS-to-AI API contract | PRMS backend + AI | Inputs, outputs, authentication, correlation, retries, and versioning. |
| Canonical MDS inventory | Product + PRMS backend | Names, types, required fields, enumerations, and IDs per result type. |
| Evidence-quality guide | Nicoletta + Maria Julia | Rules and examples for later AI Review and any extraction validation rules. |
| Policy Change guide | Maria Julia + Frank/Jim | Policy types, stages, and support criteria. |
| CGIAR AI policy | Angel / CGIAR governance | Confidentiality, PII, allowed models, retention, and residency. |
| Audio transcription provider | PRMS / AI / Progress Tracker | Select the speech-to-text provider used after the AI service downloads audio from S3. |
| Current catalogs | CLARISA / PRMS | Stable mapping of geography, centers, partners, and controlled values. |

---

## 12. AI-owned Acceptance Criteria

1. Documents, audio, and free text are independently optional, but at least one non-empty source is required.
2. Document-only, audio-only, free-text-only, and mixed-source requests are valid.
3. Source content extraction runs concurrently within configured resource limits.
4. A request can return zero, one, or many candidates without fabricating results.
5. The initial release supports the five agreed result types and excludes Knowledge Product.
6. Every candidate conforms to a versioned and validated JSON schema.
7. Applicable MDS fields are extracted; ToC and impact area scores are absent.
8. Free text and audio can identify candidates but remain ineligible as formal evidence.
9. Invalid, unreadable, irrelevant, insufficient, or disallowed sources return structured reasons.
10. Extracted candidates pass through a final validation stage before the response is returned.
11. Existing response semantics, Slack notifications, and interaction tracking remain available.
12. Each model stage records model, prompt version, duration, tokens, and errors separately.
13. Transient retries are idempotent and do not mix or duplicate request results.
14. Prompts and models are evaluated against representative fixtures for each supported type before production rollout.
15. Future AI Review can be added without changing the extraction domain contract unnecessarily.

---

## 13. Open Questions for Implementation Specs

### Contract blockers

1. What is the canonical JSON contract for each supported MDS result type?
2. Which existing response fields are contractually consumed by PRMS clients?
3. How should multiple document S3 keys, direct document uploads, and audio S3 keys coexist in multipart form data?
4. What idempotency or correlation identifier will PRMS provide?
5. Which provenance fields must be exposed to the end user?

### Functional blockers

6. What are the detailed rules for the final validation prompt?
7. Which confidence thresholds apply to each field?
8. What are the maximum files, pages, total bytes, extracted characters, audio duration, and tokens per request?
9. Should partial source failures produce a successful partial response or fail the entire request?
10. Is legacy DOC mandatory, and can TXT become formal evidence?
11. Is OCR required for scanned PDFs or images?
12. Which S3-hosted audio formats and speech-to-text provider are required?
13. How should evidence-age and domain-relevance rules affect extraction rather than future review?

### Security and operation

14. What CGIAR policy applies to confidential data, PII, retention, and Bedrock models?
15. What content may be stored in logs and interaction tracking, and for how long?
16. What are the latency, availability, concurrency, and cost objectives?

---

## 14. Recommended Specifications

1. **AI-assisted extraction implementation spec:** endpoint contract, module boundaries, orchestration, schemas, prompts, final validation, errors, authentication, and compatibility.
2. **Multisource processing spec:** document parsing, audio transcription, concurrency, chunking, retrieval, limits, and partial failures.
3. **Prompt and extraction evaluation spec:** common and type-specific rules, provenance, confidence, fixtures, and quality gates.
4. **Security and observability spec:** PII, confidentiality, logging, usage, cost, traces, and retention.
5. **AI Review spec:** a separate future document after extraction is implemented and review rules are approved.

These specifications must preserve the established `text-mining-service` structure while keeping PRMS extraction independent from STAR mining and from future AI Review behavior.
