# PRMS Integration Guide — AI Text Mining Service

This document is for the **PRMS product team** implementing the client side of multisource AI-assisted extraction: uploading sources, calling the mining API, consuming responses, and mapping results into PRMS MDS.

It focuses on **contracts and operational rules**, not internal implementation details. A full successful response example is provided separately (`test4.json`).

---

## 1. Overview

The Text Mining Service extracts structured **PRMS bilateral MDS-shaped results** from:

| Source type | How PRMS supplies it | Formal evidence? |
|-------------|----------------------|------------------|
| **Documents** | S3 object keys (`keys`) | Yes (candidate) |
| **Audio** | S3 object keys (`audio_keys`) | No — transcript only |
| **Free text** | Inline string (`text`) | No — draft context only |

**Supported indicators (6):**

- Capacity Sharing for Development  
- Policy Change  
- Innovation Development  
- Innovation Use  
- Other Output  
- Other Outcome  

**Out of scope:** Knowledge Product, Theory of Change fields, legacy STAR-only shapes, and direct file upload on the mining endpoint.

**Authentication:** CLARISA `X-API-Key` header only (no STAR `token` / `environmentUrl`).

---

## 2. End-to-end flow

### 2.1 Recommended PRMS-side flow

```text
┌─────────────┐     upload      ┌──────────────┐
│ PRMS UI /   │ ──────────────► │ S3 bucket    │
│ backend     │   (docs/audio)  │ (shared)     │
└──────┬──────┘                 └──────┬───────┘
       │                               │
       │  POST /prms/text-mining       │ keys + audio_keys
       │  JSON body + X-API-Key        │
       ▼                               │
┌──────────────────────────────────────┴────────┐
│ AI Text Mining Service                        │
│  1. Validate auth & request                   │
│  2. Download / transcribe / read sources      │
│  3. Per-source LLM extraction (parallel)      │
│  4. Merge candidates                          │
│  5. Final validation (LLM refine + JSON)      │
│  6. Field mapping (institutions / catalogs)   │
│  7. Pydantic MDS schema validation            │
└──────────────────┬────────────────────────────┘
                   │ HTTP 200 + results[]
                   ▼
            ┌─────────────┐
            │ PRMS maps   │
            │ each result │
            │ into MDS UI │
            └─────────────┘
```

### 2.2 Internal service pipeline (informational)

For timeouts and support, the service runs these stages in order:

1. **Source descriptor build** — documents first, then audio keys, then free text (stable `source-1`, `source-2`, … ordering).
2. **Source text extraction** — S3 download, PDF/DOCX/XLSX parsing, Amazon Transcribe for audio.
3. **Per-source model extraction** — one LLM call per source (parallel, bounded workers).
4. **Candidate merge** — concatenate all `results` arrays.
5. **Final validation** — second LLM pass: deduplicate, fix indicator fit, enforce JSON shape.
6. **Field mapping** — internal institution/catalog mapping (OpenSearch / CLARISA).
7. **Schema validation** — each result validated against indicator-specific Pydantic models; invalid items are **dropped** (logged server-side).

Any failure in stages 1–5 aborts the whole request (**fail-all-or-nothing**). Stage 6 mapping failures are **non-fatal** per result (original result kept). Stage 7 may return fewer results than stage 5 without failing the HTTP request.

---

## 3. HTTP API

### 3.1 Service URLs

| Environment | Base URL |
|-------------|----------|
| **Testing** | `https://oxnrkcntlheycdgcnilexrwp4i0tucqz.lambda-url.us-east-1.on.aws` |
| **Production** | `https://xps47vud6h2wtznurbtxlgpr4i0qwxlg.lambda-url.us-east-1.on.aws` |

Full endpoint path on both environments:

```text
POST {base_url}/prms/text-mining
```

These limits and URLs are **configured on the mining service** (operations / AI team). PRMS does not set them — only needs to respect them when uploading files and building requests.

### 3.2 Endpoint contract

| Method | Path | Content-Type | Auth |
|--------|------|--------------|------|
| `POST` | `/prms/text-mining` | `application/json` | Header `X-API-Key: <CLARISA API key>` |

### 3.3 Request body (`PrmsTextMiningRequest`)

Extra JSON properties are **rejected** (`422`).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `bucketName` | `string` | Conditional | S3 bucket name. **Required** if `keys` or `audio_keys` is non-empty. |
| `keys` | `string[]` | No | Document object keys (already in S3). Send as a **JSON array**, not repeated form fields. |
| `audio_keys` | `string[]` | No | Audio object keys (already in S3). |
| `text` | `string` | No | Free-text context. Whitespace-only values are ignored. |
| `user_id` | `string` | No | User email/id for interaction tracking. When set, response may include `interaction_id`. |

**At least one** of `keys`, `audio_keys`, or non-blank `text` is required.

**Not supported on this endpoint:**

- Multipart / file upload (use S3 upload on the PRMS side first).
- STAR-style `token`, `environmentUrl`, or single `key`+`file` pattern.

#### Example request

```bash
curl -X POST "https://oxnrkcntlheycdgcnilexrwp4i0tucqz.lambda-url.us-east-1.on.aws/prms/text-mining" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_CLARISA_API_KEY" \
  -d '{
    "bucketName": "ai-services-ibd",
    "keys": [
      "prms/text-mining/files/test/report.pdf",
      "prms/text-mining/files/test/workshop.docx"
    ],
    "audio_keys": [
      "prms/text-mining/audio/field-note.m4a"
    ],
    "text": "Optional narrative context from the user.",
    "user_id": "researcher@cgiar.org"
  }'
```

Use the **production** base URL in prod deployments.

---

## 4. Success response (HTTP 200)

The HTTP layer returns the MCP tool payload. Shape depends on whether `user_id` was sent:

### 4.1 Without `user_id`

```json
{
  "results": [ /* see §5 */ ]
}
```

### 4.2 With `user_id` (interaction tracking)

```json
{
  "json_content": {
    "results": [ /* see §5 */ ]
  },
  "interaction_id": "req_<uuid>"
}
```

**PRMS integration recommendation:** Always send `user_id` if you need audit/feedback, and read results from `response.json_content.results` when `json_content` is present; otherwise use `response.results`.

### 4.3 Response properties

| Property | Always present? | Description |
|----------|-----------------|-------------|
| `results` | Yes (direct or under `json_content`) | Array of validated MDS-shaped result objects. May be empty `[]`. |
| `interaction_id` | Only with `user_id` | ID for feedback / interaction APIs. |

**Important behaviors:**

- Null and empty optional fields are **omitted** from JSON (`exclude_none=True`).
- Results that fail final Pydantic validation are **silently omitted** from `results` (HTTP still `200`). Check server logs if counts seem low.
- **Knowledge Product** results are never returned.
- Institution mapping may add or normalize `institution_id` on centers/partners when mapping succeeds.
- There is **no** guarantee that every extracted candidate appears in the final array (final validation may merge or drop items).

Refer to the separate **`test4.json`** artifact for a full real-world example with multiple indicators.

---

## 5. Result schemas by indicator

Each item in `results` includes a discriminator field **`indicator`** (exact string). All types share **common MDS fields**; type-specific data lives in one optional block.

### 5.1 Common fields (`MdsBaseResultModel`)

Present on every returned result (some optional):

| Field | Type | Required in practice | Notes |
|-------|------|----------------------|-------|
| `indicator` | `string` | Yes | One of the six supported values (exact spelling). |
| `title` | `string` | Yes | Non-empty. |
| `description` | `string` | Yes | Non-empty. |
| `geo_focus` | `object` | Yes | See §5.2. |
| `lead_center` | `object` | No | CGIAR center: `institution_id`, `acronym`, `name`. |
| `contributing_center` | `object[]` | No | Same shape as `lead_center`. |
| `contributing_partners` | `object[]` | No | `institution_id`, `acronym`, and/or `name`. |
| `evidence` | `object[]` | No | Each item requires `link` (URI); optional `description`. |

**Not returned** (legacy / out of scope): `keywords`, `geoscope_level`, `toc_mapping`, `contributing_programs`, `knowledge_product`, `main_contact_person`, `created_by`, etc.

### 5.2 `geo_focus`

| Field | Type | Notes |
|-------|------|-------|
| `scope_label` | `string` | `Global`, `Regional`, `National`, `Sub-national`, or `This is yet to be determined` |
| `scope_code` | `int` | `1` Global, `2` Regional, `4` National, `5` Sub-national, `50` TBD — synced with label |
| `regions` | `{ um49code: int }[]` | When scope is **Regional** |
| `countries` | object[] | When scope is **National** or **Sub-national** |

**Country object:**

| Field | Type | Notes |
|-------|------|-------|
| `id` | `int` | CLARISA country id (optional if ISO codes present) |
| `iso_alpha_2` | `string` | Preferred for National/Sub-national |
| `iso_alpha_3` | `string` | Optional |
| `subnational_areas` | `string[]` | ISO 3166-2 codes; **Sub-national** scope only |

Shape rules enforced server-side: Global → no regions/countries; Regional → regions only; National → countries without subnational; Sub-national → countries with `subnational_areas`.

### 5.3 Capacity Sharing for Development

**Block:** `capacity_sharing` (optional)

| Field | Type | Allowed / notes |
|-------|------|-----------------|
| `number_people_trained.women` | `int` | ≥ 0 |
| `number_people_trained.men` | `int` | ≥ 0 |
| `number_people_trained.non_binary` | `int` | ≥ 0 |
| `number_people_trained.unknown` | `int` | ≥ 0 |
| `length_training` | `string` | `Short-term` \| `Long-term` |
| `delivery_method` | `string` | `Virtual / Online` \| `In person` \| `Blended (in-person and virtual)` |

### 5.4 Policy Change

**Block:** `policy_change` (optional)

| Field | Type | Notes |
|-------|------|-------|
| `policy_type.id` / `policy_type.name` | `int` / `string` | At least one required |
| `policy_type.status_amount` | object | Only when `policy_type.id == 1` (budget/investment) |
| `policy_type.amount` | `int` | Only when `policy_type.id == 1` |
| `policy_stage.id` / `policy_stage.name` | `int` / `string` | At least one required |
| `implementing_organization[]` | objects | `institutions_id`, `institutions_acronym`, and/or `institutions_name` |

### 5.5 Innovation Development

**Block:** `innovation_development` (optional)

| Field | Type | Notes |
|-------|------|-------|
| `innovation_typology.code` / `.name` | `int` / `string` | Typology reference |
| `innovation_readiness_level.id` / `.name` | `int` / `string` | IRL reference |
| `innovation_developers` | `string` | Free-text contact/affiliation |

### 5.6 Innovation Use

**Block:** `innovation_use.current_innovation_use_numbers` (required when block present)

| Field | Type | Notes |
|-------|------|-------|
| `innov_use_to_be_determined` | `boolean` | If `true`, actors/organization/measures omitted |
| `actors[]` | objects | `actor_type_id` or `actor_type_name`; `other_actor_type` when id `5` |
| `organization[]` | objects | `institution_types_id` required; nested rules for subtypes |
| `measures[]` | objects | `unit_of_measure` required |

When `innov_use_to_be_determined` is `false`, at least one of `actors`, `organization`, or `measures` must be present.

### 5.7 Other Output / Other Outcome

Common fields only (`title`, `description`, `geo_focus`, centers, partners, evidence). **No** type-specific block.

---

## 6. Source and file rules (current service limits)

The tables below reflect the **limits currently enforced** by the deployed AI Text Mining Service. Use them for PRMS-side validation (upload UI, pre-flight checks, user messaging). If limits change in a future release, the AI team will communicate an updated version of this document.

### 6.1 Limits summary

| Limit | Value | Applies to |
|-------|-------|------------|
| **Max sources per request** | **6** total (documents + audio files + free text combined) | Whole request |
| **Max file size** | **25 MB** (25,000,000 bytes) per S3 object | Each document or audio file |
| **Max PDF pages** | **100** pages | PDF documents only |
| **Max free-text length** | **50,000** characters | `text` field |
| **Max audio duration** | **10 minutes** (600 seconds) | Each audio file (after transcription) |
| **Audio transcription** | **Amazon Transcribe** (enabled) | All audio sources |
| **Audio languages** | **Auto-detect** among `en-US`, `es-ES`, `fr-FR`, `pt-BR` | Transcription |

**Per request:** up to **6 sources** in any combination, e.g. 3 documents + 1 audio + 1 free text = 5 sources.

Counting: each document key = 1 source; each audio key = 1 source; non-empty `text` = 1 source.

**Error when source count exceeded:** `413` — *"Too many sources were provided for one request. Maximum allowed sources: 6; received: N."*

### 6.2 Documents (`keys`)

| Rule | Value |
|------|-------|
| **Supported extensions** | `pdf`, `docx`, `txt`, `xls`, `xlsx`, `pptx` |
| **Not supported** | Legacy `.doc` |
| **Max file size** | **25 MB** per file |
| **Max PDF pages** | **100** pages |
| **Upload** | Must exist in S3 before mining call; service downloads via `bucketName` + key |
| **Excel** | Rows treated as text chunks during extraction |

**Unsupported extension → `415`**

**Too large → `413`:** *"The file is too large to process. Maximum allowed size is 25.0 MB; this file is X MB."*

**Too many PDF pages → `413`:** *"The PDF '…' has too many pages… Maximum allowed pages: 100; this file has N."*

**Empty / unreadable → `422`:** *"The file '…' did not contain readable text."* / *"could not be parsed as readable text."*

**Missing S3 object → `422`:** *"One of the provided files could not be found in storage."*

### 6.3 Audio (`audio_keys`)

| Rule | Value |
|------|-------|
| **Supported extensions** | `mp3`, `wav`, `m4a`, `ogg`, `flac`, `webm` |
| **Max file size** | **25 MB** per file |
| **Max duration** | **10 minutes** (600 seconds) |
| **Transcription provider** | Amazon Transcribe |
| **Languages** | Auto language identification using **English (US), Spanish (Spain), French (France), Portuguese (Brazil)** |
| **Upload** | Audio must be in S3; **no** audio upload on the mining endpoint |

**Too long → `413`:** *"The audio file is too long to process. Maximum allowed duration: 10 min 0 sec; …"*

**Transcription failure → `422`:** messages referencing the audio file or Transcribe job.

**Transcriber unavailable → `503`:** only if the service is misconfigured (not expected in testing/production).

### 6.4 Free text (`text`)

| Rule | Value |
|------|-------|
| **Max length** | **50,000** characters |
| **Evidence** | Never treated as formal documentary evidence |
| **Empty** | Ignored if whitespace-only; if it is the only source → `400` |

**Too long → `413`:** *"The free-text input is too long to process. Maximum allowed characters: 50,000; received: N."*

### 6.5 Large documents (service behavior)

For very long documents, the service may use semantic retrieval instead of sending the full text to the model (internal threshold: ~**50,000 characters** of extracted text per source, up to **10** retrieved chunks per source). PRMS does not configure this; it is handled automatically.

If a single source is still too large after retrieval, the request may fail with **`413`**. Prefer splitting oversized reports before upload when possible.

## 7. HTTP status codes and error bodies

FastAPI error responses use:

```json
{ "detail": "<human-readable message>" }
```

For validation errors (`422` from malformed JSON body):

```json
{
  "detail": [
    { "type": "...", "loc": ["body", "field"], "msg": "...", "input": ... }
  ]
}
```

### 7.1 Status code matrix

| HTTP | When | Typical `detail` / cause |
|------|------|---------------------------|
| **200** | Mining completed | Body contains `results` (see §4). Empty `results` is still success. |
| **400** | Request validation (HTTP layer) | No usable sources: *"Please provide at least one source…"* |
| **400** | Missing bucket | *"bucketName is required when document keys or audio keys are provided"* |
| **401** | Auth failure | *"Invalid API Key"* or *"Communication error with the authentication service"* |
| **413** | Payload / limits | Too many sources; file too large; PDF too many pages; audio too long; free text too long; source too large for token budget |
| **415** | Unsupported media | Bad document or audio extension; legacy `.doc` |
| **422** | Extraction / download | S3 object not found; unreadable file; empty free text source; audio transcription errors |
| **422** | JSON schema (request) | Unknown fields in body (`extra=forbid`); type mismatches |
| **502** | Model output | Final validation could not produce parseable JSON (rare after repair pass) |
| **503** | Dependency down | CLARISA validate unreachable: *"Authentication service is temporarily unavailable"* |
| **503** | Audio unavailable | Transcriber not configured |
| **500** | Unexpected | Unhandled server error; MCP communication failure |

### 7.2 Fail-all-or-nothing

Unlike STAR bulk flows, **one bad source fails the entire request**. PRMS should validate files (type, size, duration) **before** calling mining, or be prepared to retry with a reduced source set.

### 7.3 Partial success inside HTTP 200

| Scenario | HTTP | PRMS action |
|----------|------|-------------|
| All candidates validate | `200` | Map all `results` |
| Some candidates fail Pydantic | `200` | Fewer items in `results`; check logs |
| Final validation drops outliers | `200` | Fewer items; not an error |
| Zero valid results | `200` with `"results": []` | Show empty state; user may refine sources |

---

## 8. PRMS implementation checklist

### 8.1 Upload path

1. Upload documents and audio to the **agreed S3 bucket** using PRMS storage credentials/prefixes.
2. Store returned object keys for the mining request.
3. Do **not** rely on multipart upload to `/prms/text-mining`.

### 8.2 Mining call

1. `POST {testing_or_production_base_url}/prms/text-mining` with `Content-Type: application/json`.
2. Header `X-API-Key` from CLARISA integration.
3. Pass `bucketName` whenever `keys` or `audio_keys` are used.
4. Send `keys` / `audio_keys` as JSON **arrays**.
5. Optionally pass `text` and `user_id`.

### 8.3 Consuming results

1. Normalize response shape (`results` vs `json_content.results`).
2. Branch on `indicator` discriminator for UI and MDS mapping.
3. Map `geo_focus` using `scope_label` / `scope_code` and country ISO codes.
4. Apply type-specific block to the correct PRMS form section.
5. Treat `contributing_partners` / `lead_center` institution IDs as **hints** — verify in PRMS catalog UI.
6. Do not expect `evidence` from free text or audio-only extractions unless the model linked URIs explicitly.

### 8.4 Mapping into PRMS MDS

The mining service already resolves many institution strings to IDs via its internal mapping step. PRMS should still:

- Validate required MDS fields per indicator before save.
- Allow user review/edit (AI-assisted draft, not auto-submit).
- Handle empty optional blocks gracefully.
- Not assume 1:1 mapping between uploaded files and results (one file may yield many results; many files merge in one response).

### 8.5 Timeouts and UX

Mining is **long-running** (often **2–5+ minutes** for multisource requests with several documents; audio adds Transcribe time up to **~5 minutes** per job server-side). PRMS should:

- Use async job pattern or generous client timeout.
- Show per-source progress if wrapping the API in a backend job queue.
- Surface `413` / `415` / `422` messages directly to users (they are actionable — see §6 for limit values).

---

## 9. Quick reference — indicator → type-specific block

| `indicator` | Block field |
|-------------|-------------|
| Capacity Sharing for Development | `capacity_sharing` |
| Policy Change | `policy_change` |
| Innovation Development | `innovation_development` |
| Innovation Use | `innovation_use` |
| Other Output | *(none)* |
| Other Outcome | *(none)* |

---
