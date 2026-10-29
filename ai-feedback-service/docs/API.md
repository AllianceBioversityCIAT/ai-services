# Interaction and feedback HTTP contract

Implemented by [models](../app/api/models.py), [routes](../app/api/routes.py) and the [DynamoDB service](../app/utils/feedback/feedback_util.py). This guide describes `main-feedback`; its models/routes match development after the reviewed local merge. Generated descriptions include historical claims that are not operational guarantees.

## Routes

| Method/path | Response |
| --- | --- |
| `POST /api/interactions` | AIInteractionResponse; creates or updates feedback |
| `GET /api/interactions/summary` | InteractionSummary; optional service_name/start_date/end_date query filters |
| `POST /api/interactions/search` | Entries, pagination, echoed filters and page-level summary |
| `GET /api/feedback/services` | services, total_count, service_names from the process registry |
| `GET /api/feedback/service/{service_name}` | Service-filtered records; limit defaults to 50, HTTP maximum 500 |
| `GET /`, `GET /health` | Metadata/registry information, not live dependency probes |
| `/docs`, `/redoc`, `/openapi.json` | Generated documentation/schema |

No feedback POST, HTTP manual service-registration, delete or user-authentication route is implemented. The `/api/feedback` prefix remains only on two GET endpoints. The service-list endpoint does not enumerate all names persisted in DynamoDB.

## Create an interaction

```json
{
  "user_id": "demo-user",
  "service_name": "chatbot",
  "session_id": "demo-session",
  "user_input": "Example question",
  "ai_output": "Example answer",
  "response_time_seconds": 2.5,
  "context": {"filters_applied": {"phase": "AR 2025"}},
  "platform": "AICCRA"
}
```

| Field | Actual validation/default |
| --- | --- |
| user_id, service_name | Required strings; no min-length, email/ownership or service catalog validation |
| session_id, user_input, ai_output | Optional nullable strings; output is not required even when creating |
| feedback_type | Optional nullable literal positive or negative |
| feedback_comment | Optional nullable string, maximum 5000 characters; no automatic whitespace trimming |
| update_mode | Optional nullable bool, defaults false |
| interaction_id | Optional nullable string, no ID-format validation |
| display_name, service_description | Optional nullable service metadata overrides |
| context | Optional nullable dictionary of arbitrary values |
| response_time_seconds | Optional nullable float; no nonnegative bound |
| platform | Optional nullable string |

New records use a generated `req_<uuid>` even if an interaction_id was supplied with update_mode false. Creates are not idempotent. Optional feedback can be attached during creation; negative feedback triggers a best-effort notification attempt after saving.

Illustrative create response:

```json
{
  "interaction_id": "req_550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "message": "AI interaction tracked successfully for AICCRA Chatbot",
  "timestamp": "2026-10-29T15:00:00Z",
  "service_name": "chatbot",
  "has_feedback": false
}
```

Service metadata resolution prioritizes request values. Supplying either override can bypass auto-registration. Without overrides, existing registry information is used, or an unknown service name is auto-registered with a generated display name. Registry state lives only in the process; record metadata is persisted separately.

## Attach or replace feedback

```json
{
  "user_id": "demo-user",
  "service_name": "chatbot",
  "interaction_id": "req_550e8400-e29b-41d4-a716-446655440000",
  "update_mode": true,
  "feedback_type": "positive",
  "feedback_comment": "Useful example answer"
}
```

An update is selected only when both update_mode and interaction_id are truthy. The response uses status `updated`, a new feedback timestamp and has_feedback true. The composite key includes service_name, so retain it with the returned ID.

Current limitations:

- update_mode true without an ID creates a new record; it is not a validation error.
- There is no existence condition or ownership check. An unknown key can create a partial DynamoDB item; supplied user_id is not compared with stored ownership and is not rewritten by this update.
- feedback_type, has_feedback, nonempty feedback_comment, has_comment and feedback_timestamp are updated. Original content, timestamp and derived metadata such as metadata.comment_length are not refreshed.
- Empty comments do not clear a stored comment. Feedback cannot be removed through this contract.
- Without a truthy feedback_type, the SDK call receives ExpressionAttributeNames=None. This can fail botocore validation, including comment-only updates. Use a feedback type and a known ID in current clients.
- Repeated negative updates can queue repeated notifications; there is no deduplication or transactional email delivery.

## Search

```json
{
  "service_name": "chatbot",
  "user_id": "demo-user",
  "feedback_type": "negative",
  "has_comment": true,
  "start_date": "2026-10-01T00:00:00Z",
  "end_date": "2026-10-31T23:59:59Z",
  "max_response_time": 30,
  "limit": 50,
  "offset": 0,
  "sort_by": "timestamp",
  "sort_order": "desc"
}
```

Search accepts nullable fields: service_name/user_id; feedback_type positive or negative; has_feedback/has_comment booleans; start/end datetimes; max_response_time float; limit default 50, range 1–1000; offset default 0, minimum 0; sort_by timestamp/feedback_type/service_name/response_time (default timestamp); sort_order asc/desc (default desc). Avoid null limit/offset: the model accepts them but pagination arithmetic cannot use them.

Reads scan all matching DynamoDB pages. Service/date conditions apply to scans, then user_id, feedback_type, has_comment and max_response_time are applied in Python, followed by sorting and slicing. **has_feedback is accepted and echoed but not applied.** Limit bounds returned entries, not the number/cost of scanned records. Prefer UTC ISO8601 dates; the implementation compares stored ISO timestamp strings and does not enforce date ordering.

The response contains:

- interaction_entries: records for the current page.
- pagination: total_count after filtering, returned_count, offset, limit, has_more.
- filters_applied: echoed service/user/feedback/comment/date selections; not proof every accepted filter was enforced.
- summary: counts, feedback_rate and satisfaction_rate for the returned page only.

The service-specific GET calls the same search implementation and includes records with no feedback. Its limit query has no HTTP lower bound, but invalid values can fail inside the service and become HTTP 500 instead of 422.

## Summary

The summary endpoint scans all matched records and returns total_interactions, interactions_with_feedback, positive_feedback, negative_feedback, feedback_rate, satisfaction_rate, average_response_time, services_breakdown, recent_interactions and time_period.

Feedback rate = records marked has_feedback / total records × 100. Satisfaction = positive feedback / records marked has_feedback × 100. Mean response time uses records with a recorded response time. The summary recognizes additional historical feedback aliases in stored records, while new HTTP requests accept only positive/negative. A zero mean is returned as null by the current truthiness check.

Recent interactions are selected as the first ten scanned records, then sorted; they are not guaranteed to be the latest ten overall. The search page summary uses exact positive/negative values, so it can differ from the summary endpoint on historical aliases.

Storage scan exceptions are logged and returned as an empty list. Search/summary can therefore return HTTP 200 with zero results when the underlying read failed. They are not reliable storage-health probes.

## Errors and access

Invalid Pydantic request bodies/query enums return HTTP 422 with FastAPI's standard validation list in detail. Route error envelopes are nested:

```json
{
  "detail": {
    "error": "Interaction tracking failed",
    "details": "Example storage failure",
    "status": "error"
  }
}
```

The create/update route maps ValueError to 400, RuntimeError to 500 and other exceptions to 500. The actual storage service wraps create/update exceptions in RuntimeError, so many storage/update failures return 500. Other route failures use 500 with operation-specific labels. The global handler has a separate flat error/status/service/details/support envelope.

Notification failure is not represented in AIInteractionResponse and does not roll back a stored record. Queue publication is not evidence that the external worker delivered an email.

HTTP routes have no authentication dependency or record-ownership check; CORS permits all origins and credentials. AWS IAM protects outbound resource access, not user authorization. Gateways, encryption, backup/replication and retention must be validated externally. `/health` reads registry state and returns a fixed historical timestamp, without probing DynamoDB or RabbitMQ.
