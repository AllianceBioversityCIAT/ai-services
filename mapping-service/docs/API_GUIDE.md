# Mapping API guide

This describes `main-mapping` and its implemented request/result semantics. Start with the [README](../README.md) for setup. The only application route is `POST /map/fields`; generated Swagger/ReDoc/OpenAPI endpoints are also available. There is no GET root or health operation.

## Request

```json
{
  "entries": [
    {"value": "Example Person", "type": "staff"},
    {"value": "Example Research Institute", "type": "institution"}
  ],
  "environment": "test"
}
```

| Field | Schema and behavior |
| --- | --- |
| `entries` | Required array of entry objects; empty array accepted |
| `entries[].value` | Required string; no nonempty or length constraint |
| `entries[].type` | Required literal `staff` or `institution` |
| `environment` | Optional literal `test` or `prod`, default **prod** |

The environment selects CLARISA's institution test/prod index. Staff always uses STAR's configured base index. It does not select different hosts, credentials, LLM endpoints, or deployment settings. Invalid body fields generally produce HTTP 422 before any entry is processed; there is no partial acceptance of a structurally invalid batch.

An empty array returns `{"results":[]}` without external requests. Nonempty entries invoke configured services sequentially; no authentication/rate-limit dependency is defined on the public route.

## Results

HTTP 200 returns an ordered `results` array. Duplicate inputs remain separate entries. An illustrative mapped item:

```json
{
  "results": [
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

`mapped_id` is the staff `carnet` or a string form of the institution `code` when present/truthy. Staff does not populate an acronym. Mapped ID/name/acronym and score are nullable in the response model. Current no-match/error paths explicitly assign null mapped fields and score 0:

```json
{
  "results": [
    {
      "original_value": "Example unmatched name",
      "type": "staff",
      "mapped_id": null,
      "mapped_name": null,
      "mapped_acronym": null,
      "score": 0
    }
  ]
}
```

## Selection and scores

The code requests three OpenSearch hits and passes candidate positions/metadata to the LLM API. It accepts direct JSON results or a Fast Response-style envelope containing a JSON string in `output` with `status: "success"`; it also attempts best-effort extraction/cleanup of a `json`-labelled fenced block.

Expected LLM selection shape (this is an internal provider result, not the public mapping response):

```json
{
  "selected_candidate": 2,
  "confidence_score": 92,
  "reasoning": "Fictional example: candidate two matches the supplied name."
}
```

The selection is a **1-based position**, not a staff/institution ID. It is parsed as JSON without a dedicated selection schema. The following table describes current branches; malformed values can fall into the per-entry exception handler.

| Condition | Public result |
| --- | --- |
| Valid selected integer position | Selected candidate with the LLM's `confidence_score`, which can be null or outside 0–100 |
| Integer position outside the available list | First OpenSearch candidate, fixed score 90 |
| LLM request failure, unparseable text, unsuccessful envelope, or falsey result such as an empty object | First OpenSearch candidate, fixed score 90 |
| Truthy parsed object with `selected_candidate:null` or that key absent | Null mapped fields, score 0 |
| No OpenSearch hits | Null mapped fields, score 0; LLM not called |
| OpenSearch error or caught per-entry processing/validation exception | Null mapped fields, score 0; later entries still attempted |

A malformed selection type (for example, a string instead of an integer) can produce null/0 through the entry exception handler rather than first-hit fallback. The prompts request rejecting matches below 60, but the implementation does not separately enforce that threshold when a candidate is selected.

Returned `score` is not the OpenSearch `_score`: it is either model confidence, fixed fallback 90, or 0 in the unmapped paths above. There is no calibrated-probability guarantee. The response omits the candidate list, reasoning, chosen source, fallback flag, and error details. A client cannot distinguish no results, deliberate rejection, and entry-level errors from null/0 alone.

## Errors and side effects

FastAPI body-validation failures normally return HTTP 422 with a `detail` list. There is no custom error envelope in this service. Most search/LLM/mapping failures are handled inside the per-entry loop or LLM parser, so HTTP 200 does not establish that every external operation succeeded. Unexpected exceptions outside those handlers can still produce a server error.

Search uses HTTP POST to OpenSearch `/_search` with Basic auth and no explicit request timeout. LLM validation sends `{prompt, input_text}` to `LLM_API_URL` with a 300-second timeout and no added authentication header. It includes candidate staff email/center or institution acronym/website when present.

No catalog create/update endpoint is implemented here. Nonempty batches can nevertheless invoke paid model infrastructure and write logs. The async route performs synchronous HTTP calls directly; large batches and a search without an explicit timeout have no documented total-time bound.

See [design](HIGH_LEVEL_DESIGN.md) for query construction and [branch differences](BRANCH_DIFFERENCES.md) for packaging/logging before promotion.
