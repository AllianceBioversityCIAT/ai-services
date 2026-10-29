# Partner Request Support API guide

Source of truth: `backend/api.py` and its current callers. This guide documents `main-partner-request-support`'s implemented request shapes and side effects, not an independently verified external CLARISA specification. Run/configure the backend using its [README](../backend/README.md).

## Route index

| Method and route | Input | Result and effects |
| --- | --- | --- |
| `GET /` | None | Service metadata |
| `GET /health` | None | `{"status":"healthy"}`; no dependency checks |
| `GET /api/download-template` | None | Excel stream from configured S3 bucket/key |
| `GET /api/sync-partner-requests` | None | Pending CLARISA snapshot in process memory; includes `batch_size: 10` |
| `POST /api/process-api-partners` | Bare integer array or null/omitted | Synchronize catalog, match pending requests, read/write cache |
| `POST /api/process-partners` | Multipart upload and user fields | Synchronize catalog, optionally create upstream requests, match/cache results |
| `POST /api/respond-partner-request` | JSON object | Submit human accept/reject to CLARISA |
| `POST /api/manual-web-search` | JSON object | Paid web/model research; no request response |
| `POST /api/auto-partner-request` | `AutoPartnerRequest` object | Automated evaluation; optional upstream creation/response; possible notifications |
| `POST /api/sync-clarisa-institutions` | Bare boolean, default true | Update embeddings/catalog and optionally delete obsolete entries; may clear cache |
| `POST /api/clear-cache` | None | Delete contents of the branch-selected cache table |

There is no general FastAPI authentication dependency on these routes. Tokens in processing/response bodies are forwarded to relevant upstream CLARISA calls. Browser login and CORS do not establish backend authorization. Verify infrastructure controls and external authentication separately.

## Pending-request processing

`GET /api/sync-partner-requests` fetches all requests, filters `requestStatus == "Pending"`, and returns `success`, `count`, `total_requests`, `batch_size`, and `pending_requests`. It refreshes a process-local snapshot, not a shared durable queue.

`POST /api/process-api-partners` fetches pending requests when its process-local snapshot is empty; an existing snapshot is reused until explicitly refreshed. With omitted/null/empty IDs it sorts by `(created_at or "", id or 0)` and selects the first ten. Missing dates sort first. An explicit nonempty array selects matching pending IDs; it does not use the default ten-item selection.

Example request body for explicit IDs (fictional):

```json
[1001, 1002]
```

Do not wrap the array as `{"partner_ids": [...]}`. A successful processing response includes `partners`, `stats`, `cache_info`, and `sync_info`. Matching results carry quality, candidates/scores, source metadata, and optional web research; inspect current frontend types for the complete consumed structure. Cache reuse means response order need not equal input order.

## Spreadsheet processing

Multipart fields for `/api/process-partners`:

| Field | Requirement |
| --- | --- |
| `file` | Excel upload |
| `user_email`, `user_name`, `auth_token` | Required form fields |
| `create_requests` | Boolean, defaults true; frontend sends true |

Use the downloadable template. Code reads positional columns: ID, institution name, acronym, website, institution type, headquarters country, followed by optional category columns. Header text alone does not remap an arbitrary workbook. Country/type names are mapped through CLARISA catalogs when creating requests.

`create_requests=false` disables the creation step, but still allows catalog synchronization, cache writes, and model/web calls. The response includes `partners`, `stats`, `creation_info`, `cache_info`, and `sync_info`. Inspect creation metadata as well as HTTP status; batch work can have per-row errors or partial upstream effects.

## Human response and manual research

`POST /api/respond-partner-request` accepts:

```json
{
  "request_id": 1001,
  "user_id": 42,
  "accept": false,
  "auth_token": "YOUR_ACCESS_TOKEN",
  "reject_justification": "Fictional example: duplicate institution."
}
```

The backend looks up the request, preserves MIS/requester metadata, and sends the upstream response with a Bearer token. The external payload uses `requestId` and `userId`; these are different from the local snake-case body. Success returns `success`, `action`, `request_id`, and `message`. A local response action changes CLARISA data and is not a validation probe.

`POST /api/manual-web-search` accepts:

```json
{
  "partner_name": "Example Research Institute",
  "country": "Kenya",
  "website": "https://example.org"
}
```

It returns research and a formatted summary on success. A handled search failure can return HTTP 200 with `success:false` and `error`; clients must inspect the body. This route does not submit an accept/reject decision.

## Automated evaluation

`POST /api/auto-partner-request` requires `partner_name`; other model fields are optional unless a selected operation adds requirements.

```json
{
  "partner_name": "Example Research Institute",
  "country": "Kenya",
  "website": "https://example.org",
  "acronym": "ERI",
  "institution_type": "Research institution",
  "institution_subtype": "Example subtype",
  "auto_respond": false,
  "create_in_clarisa": false
}
```

This example avoids upstream creation/response flags, but it can still use paid services and send configured MANUAL_REVIEW notifications. It is not a universal dry run.

| Hybrid best-match score | Automatic tier | Next step |
| --- | --- | --- |
| `> 0.95` | excellent | REJECT as duplicate, without extra duplicate/web verification |
| `0.85–0.95` inclusive | very_good | Same-institution model check |
| `0.70–<0.85` | good | Same-institution model check |
| `0.60–<0.70` | fair | Web/rules review |
| No accepted best match (`<0.60`) | no_match | Web/rules review |

A successful positive same-institution check produces REJECT. If a duplicate is not confirmed, processing proceeds to web/rules review. That review produces ACCEPT when `success` and `approved` are truthy, otherwise MANUAL_REVIEW; it does not directly produce REJECT.

Completeness metadata checks name, type, subtype, country, and website; acronym is optional. In the current web/rules path, missing fields do not independently block ACCEPT. Duplicate-only paths can leave completeness metadata null. Do not replace executable behavior with the older helper docstring or business reference.

Additional fields and effects:

| Option/field | Current behavior |
| --- | --- |
| `auto_respond=true` | For ACCEPT/REJECT, submit a response for `request_id` using `auth_token` and `user_id` |
| `create_in_clarisa=true` | Create first, then evaluate; ACCEPT/REJECT can be submitted even if `auto_respond=false` |
| Creation requirements | Country, institution type, token, user ID, requester email/name must be present |
| `external_user_mail`, `external_user_name`, `external_user_comments` | Requester metadata used for creation and/or manual-review notifications |
| `mis_acronym` | Creation source, defaults `CLARISA` |
| MANUAL_REVIEW | Leave pending; do not submit accept/reject; attempt configured requester/admin notifications |

Creation maps country name to `hqCountryIso` (`isoAlpha2`) and type name to `institutionTypeCode` (`code`). The current external create payload contains `name`, `acronym`, `websiteLink`, `hqCountryIso`, `institutionTypeCode`, `externalUserMail`, `externalUserName`, `externalUserComments`, and `misAcronym`. Local `user_id`, `auto_respond`, `request_id`, and `create_in_clarisa` are orchestration fields, not fields in that create payload. Confirm catalog names, accepted values, required fields, and authentication with the target CLARISA environment.

Responses include `decision`, `confidence`, `reason`, `match_quality`, `clarisa_match`, `web_search_performed`, `web_search_result`, `duplicate_check_performed`, `duplicate_check_result`, `fields_complete`, `missing_fields`, `auto_responded_to_clarisa`, `clarisa_response`, and `notifications` as applicable. A classification does not imply upstream submission: inspect `auto_responded_to_clarisa` and `clarisa_response`.

Creation, evaluation, upstream response, and notification are separate operations without a shared transaction or documented idempotency key. A later error may follow an already-created request. Confirm upstream state before retrying a failed creation flow. A queued notification is not proof of email delivery.

## Maintenance body shapes and errors

`POST /api/sync-clarisa-institutions` takes a bare JSON boolean, for example:

```json
false
```

This disables obsolete-row deletion for that call; it still synchronizes records/embeddings and may affect cache. Sending `{"delete_obsolete":false}` does not match the current parameter shape. Processing routes use deletion-enabled synchronization independently of this example.

FastAPI validation failures generally return 422; route-specific validation, unavailable resources, provider/network errors, and unexpected errors can produce 400/404/500/502. Some operations return body-level failure information. See the implementation for each route rather than treating all 2xx responses as a completed business action. Generated Swagger descriptions include older examples; parameter schemas and source code determine the request shape described here.
