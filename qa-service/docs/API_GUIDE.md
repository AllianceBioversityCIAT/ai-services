# PRMS QA API guide

The service exposes two independent workflows. Use `/api/prms-qa` for metadata improvement and `/prms/quality-assessment` for a structured quality assessment. Run examples from `qa-service/` after completing the [local setup](../README.md#local-setup).

The examples use fictional result data. They illustrate request structure, not a measured assessment or a production deployment. Generated schemas are available at `/openapi.json` and `/docs` when the server is running.

## AI Review: improve metadata

```bash
curl --request POST http://localhost:8000/api/prms-qa \
  --header 'Content-Type: application/json' \
  --data-binary @docs/examples/metadata-request.json
```

See the [complete request](examples/metadata-request.json). The top-level body contains `result_metadata` and optional `user_id`. Omitting `user_id` skips interaction tracking.

`result_metadata` is an open dictionary in the API schema, but the processing code directly reads these fields:

| Required key | Meaning |
| --- | --- |
| `result_type_name` | Result type; normalized to lowercase for processing |
| `result_level_name` | Result level; normalized to lowercase for processing |
| `gender_tag_level_description` | Selected gender/youth/social-inclusion impact score |
| `climate_change_tag_level_description` | Selected climate impact score |
| `nutrition_tag_level_description` | Selected nutrition/health/food-security impact score |
| `environmental_biodiversity_tag_level_description` | Selected environment/biodiversity impact score |
| `poverty_tag_level_description` | Selected poverty/livelihoods/jobs impact score |

Impact score keys must be present; a null value is normalized to `Not Defined`. Include `result_name` and `result_description` for rewriting. Other metadata is passed as prompt context. Optional `evidence` is a list of objects containing `link`; an item with `is_sharepoint: 1` and `is_public_file: false` is skipped.

### Successful response

| Field | Meaning |
| --- | --- |
| `time_taken` | Processing duration as a string |
| `json_content` | Combined, schema-validated model output |
| `interaction_id` | Optional analytics ID; may be null |
| `evidence_metadata` | Optional extraction summary; may be null |
| `status` | `success` |

The shape of `json_content` depends on `result_type_name`:

- **Innovation Development:** `new_title`, `new_description`, `short_name`, and `impact_area_scores`.
- **Knowledge Product:** `impact_area_scores`, without title/description rewriting.
- **Other types:** `new_title`, `new_description`, and `impact_area_scores`.

`impact_area_scores` contains the string fields `social_inclusion`, `climate_adaptation`, `food_security`, `environmental_health`, and `poverty_reduction`. Feedback is model-generated. The output schemas validate structure; they do not independently prove factual correctness or enforce every writing instruction.

The workflow attempts up to five evidence URLs, by default, and continues without evidence context if enrichment fails. When available, `evidence_metadata` contains `count`, `total_attempted`, and `sources` with URL, title, type, and content length.

There is currently no active authentication dependency on this route. That does not establish whether infrastructure adds access controls.

### Errors

| HTTP status | Typical cause |
| --- | --- |
| 400 | Missing metadata key or invalid input detected during processing |
| 422 | Request body does not match the Pydantic envelope |
| 502 | Model returns invalid JSON or output fails schema validation |
| 429 | Processing reports model throttling |
| 408 | Processing reports a timeout |
| 500 | Other processing failure |

Route-generated errors are wrapped in `detail`, with fields such as `error`, `message`, `status`, `error_type`, and optional `debug_info`. Framework validation errors have a different structure. Some route errors include traceback details.

## Traffic-light quality assessment

```bash
curl --request POST http://localhost:8000/prms/quality-assessment \
  --header 'Content-Type: application/json' \
  --header "X-API-Key: ${QA_API_KEY}" \
  --data-binary @docs/examples/assessment-request.json
```

Set `QA_API_KEY` in your shell to an authorized key. This variable is used by the example command; the server receives the value in `X-API-Key`. CLARISA must authorize `AI Traffic Light - PRMS`.

See the [complete request](examples/assessment-request.json). Current request fields are:

| Field | Contract |
| --- | --- |
| `contract_version` | Defaults to `0.2`; send `0.2` for the documented shape |
| `request_id` | Required correlation string, echoed in the assessment response |
| `result` | Required header; includes `type` and optional reporting context |
| `sections` | Required object; section models supply defaults for omitted members |
| `impact_areas` | Optional list at the top level, alongside `sections` |
| `constraints.timeout_seconds` | Optional processing budget; default 60 seconds |
| `user_id` | Optional; enables an attempt to record the interaction |

The current validator checks result types, labels, and catalog values. It does not reject a request solely because `contract_version` differs; the version string is not a substitute for those checks.

### Result types and exact form labels

Result type matching ignores case and surrounding whitespace. Keys in `sections.type_specific.fields` must match the following labels exactly. Required keys must be present even when the form has no value; missing content is then handled by applicable criteria.

| `result.type` | Required keys in `type_specific.fields` |
| --- | --- |
| `Policy Change` | `Policy type`, `Policy stage`, `Implementing organizations`, `USD amount` |
| `Innovation Use` | `User types`, `Number of people using`, `Other quantitative measures`, `Investment (USD)` |
| `Capacity Sharing for Development` | `Number of people trained`, `Length of training`, `Delivery method`, `Implementing organizations` |
| `Innovation Development` | `Innovation typology`, `Readiness level`, `Innovation developers` |
| `Other Output` | No keys; use an empty fields object |
| `Other Outcome` | No keys; use an empty fields object |

Extra labels and near-matches are rejected. Knowledge Product is not supported by this endpoint's current catalog.

Selected closed vocabularies:

- `Delivery method`: `Virtual / Online`, `In person`, `Blended (in-person and virtual)`.
- `Length of training`: `Long-term`, `Short-term`.
- Evidence tags: `Gender`, `Youth`, `Nutrition`, `Environment & biodiversity`, `Poverty`.

The complete impact-area names, subcomponents, and other catalog definitions are in [vocabularies.py](../app/utils/assessment/vocabularies.py). Do not infer accepted form values from the older metadata-improvement payload; the two endpoints use different contracts.

### Response and verdicts

The response includes `request_id`, `criteria_version` (currently `QA-2026-v1`), `overall`, `sections`, `evidence`, `status`, `degraded_reason`, `coverage`, and optional `interaction_id`.

| Verdict | Rule | Derived score |
| --- | --- | --- |
| `red` | At least one evaluated core criterion flagged | 0–49 |
| `amber` | Non-core flags only | 50–99 |
| `green` | Evaluated criteria have no flags | 100 |
| `grey` | Not evaluated | null |

Scores exclude unevaluated criteria. They describe the evaluated findings, not completeness or a probability of correctness.

`sections` contains General Information, Contributors and Partners, Geographic Location, and Evidence. `type_specific` is also returned for result types with a dedicated form section; it is omitted entirely for Other Output and Other Outcome.

Each section contains `verdict`, `score`, `comments`, `strengths`, `issues`, `fields`, and optional `suggestions`. `fields` identifies the inputs behind the findings using the Reporting Tool's field names.

General Information may include a replacement title and/or description when its verdict is amber or red. This illustrative section fragment shows the shape, not an actual model result:

```json
{
  "verdict": "amber",
  "score": 75,
  "comments": "Clarify the title.",
  "strengths": [],
  "issues": ["The title does not identify the result clearly."],
  "fields": ["title"],
  "suggestions": {
    "title": "Drought-tolerant rice variety released for smallholder farmers",
    "description": null
  }
}
```

Suggestions must survive validation: plain text, changed from the original, at least three words, and at most 30 words for a title or 300 for a description. A discarded suggestion does not change the verdict. Either field may be null, and the entire suggestions object may be null.

### Evidence and execution coverage

Each item in the response's `evidence` list contains its input `index`, a `verdict`, and a `reason`. Items with no link or `visibility: private` are not fetched and return grey. Public repository items with a link can be fetched; `source: prms_repository` alone does not make an item private.

Individual extraction failures or unreadable sources can also return grey. If attached evidence cannot be read and there are no deterministic evidence flags, the evidence section is forced to grey. Deterministic findings can still flag issues such as an invalid evidence source.

Read these fields alongside quality verdicts:

- `status`: the current orchestration returns `completed` or `partial` in successful responses.
- `degraded_reason`: explains reported model or retrieval failures.
- `coverage.criteria_total` and `coverage.criteria_evaluated`: report how many applicable findings were evaluated.

`completed` does not imply every criterion was evaluated: private evidence, unavailable external checks, or criteria omitted by the model can still leave gaps. A green result with incomplete coverage requires the caller to consider that limitation.

`constraints.timeout_seconds` guides internal scraping and model-call budgets; it is not a guaranteed end-to-end HTTP deadline. Tracking and notifications can add time, and retries or underlying blocking work can outlive an individual wait.

### Errors

| HTTP status | Cause |
| --- | --- |
| 400 | `CONTRACT_VIOLATION`: unsupported result type, missing/extra/mismatched labels, or invalid catalog value |
| 401 | CLARISA returns a non-200 response or marks the key invalid |
| 401 or 403 | Missing API key, depending on the installed FastAPI version |
| 422 | Pydantic request validation fails |
| 503 | Authentication service cannot be reached, or both assessment model calls fail |
| 500 | Unexpected assessment failure |

Contract errors use `detail.error_type: CONTRACT_VIOLATION`, `detail.request_id`, and a `detail.problems` list with `code`, `field`, and `message`.

When both metadata and evidence model calls fail, the route returns HTTP 503 with `detail.error_type: ASSESSMENT_UNAVAILABLE`. Unexpected processing errors return HTTP 500 with the same error type. The response model includes an `unavailable` status enum, but total model-call failure follows this HTTP error path rather than returning a successful response with `status: unavailable`.

The API does not submit or block a PRMS result itself. The consuming application owns how partial results and HTTP failures affect its workflow.
