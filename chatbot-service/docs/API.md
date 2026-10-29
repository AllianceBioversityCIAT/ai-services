# HTTP API contract

Implemented by [models](../app/api/models.py), [routes](../app/api/routes.py) and the [application](../app/api/main.py) on `dev-chatbot-service`. Generated descriptions include historical reload/model claims; use the behavior below when integrating.

## Routes

| Method/path | Behavior |
| --- | --- |
| `POST /api/chat` | Buffered JSON chat response |
| `GET /` | Static service/catalog metadata, not discovery of live capabilities |
| `GET /health` | Static health/capability response; no upstream checks |
| `GET /chatbot-ui` | HTML chat interface |
| `/static/` | Mounted `interface/` files |
| `/docs`, `/redoc`, `/openapi.json` | Generated API documentation/schema |

There is no local feedback, ingestion, session deletion or authentication endpoint. Interfaces call an external `/api/interactions` API for tracking/feedback.

## Chat request

```json
{
  "message": "Summarize deliverables for AR 2025",
  "phase": "AR 2025",
  "indicator": "All indicators",
  "section": "Deliverables",
  "session_id": "baf542c1-e699-4b4e-9a61-1fe4794aa044",
  "memory_id": "demo-user",
  "insert_data": false
}
```

| Field | Validation/default |
| --- | --- |
| `message` | Required string, 1–2000 characters |
| `session_id`, `memory_id` | Required strings, minimum one character; no UUID/email/ownership validation |
| `phase` | Optional nullable string, default `All phases` |
| `indicator` | Optional nullable string, default `All indicators` |
| `section` | Optional nullable string, default `All sections` |
| `insert_data` | Optional nullable boolean, default false; active agent does not reload data |

A whitespace-only message is not stripped/rejected by the length constraint. The API does not enforce catalog membership. Prefer string filter values: accepted nulls are not safe for every filter combination. In particular, a concrete phase with `section=null` can raise an error in the filter builder.

## Retrieval filters

`filter_metadata(phase, section, indicator)` requests `numberOfResults=30` and `overrideSearchType=HYBRID`:

- `year`: first numeric phase token, retained as a string; the builder has no 2021–2025 bound.
- `phase_name`: first nonnumeric token, applied only when section is Contributions.
- `table_type`: lowercased section, except Contributions produces `contributions OR questions`.
- `indicator_acronym`: literal indicator string.
- One condition becomes a direct filter; multiple conditions use `andAll`.
- Exact `All phases`, `All sections` and `All indicators` suppress their conditions. A phase containing `None` also suppresses phase parsing.

For Deliverables with `AR 2025`, retrieval filters by year and section, not by AR phase name. Backend metadata types and HYBRID compatibility must match the externally configured Knowledge Base. Textual filters also appear in the agent input; `filters_applied` only echoes request values, not verified source provenance or access control.

## Chat response

Illustrative response; answer text depends on AWS:

```json
{
  "message": "Example answer based on indexed reporting data.",
  "session_id": "baf542c1-e699-4b4e-9a61-1fe4794aa044",
  "filters_applied": {
    "phase": "AR 2025",
    "indicator": "All indicators",
    "section": "Deliverables"
  },
  "data_reloaded": false,
  "processing_info": null,
  "status": "success"
}
```

The API consumes the agent generator completely before returning JSON. No HTTP token stream or structured citation list is exposed. An empty provider completion can produce an empty message.

With `insert_data=true`, the route reports `data_reloaded=true` and adds processing-info fields `data_reload_time`, `total_processing_time` and `tables_updated` (deliverables, contributions, innovations, oicrs, questions). These are derived from the request flag and elapsed request time. The active agent does not implement a reload: **these fields do not prove any refresh or table update**. Keep the flag false for ordinary chat.

## Errors

Pydantic request errors return HTTP 422 with the standard FastAPI validation list in `detail`. Route errors use a nested envelope:

```json
{
  "detail": {
    "error": "Invalid request parameters",
    "details": "Example validation reason",
    "status": "error"
  }
}
```

| Route exception | HTTP result |
| --- | --- |
| `ValueError` | 400 Invalid request parameters |
| `PermissionError` | 403 Access denied |
| `RuntimeError` mentioning context limit/input too long | 400 Message too complex |
| Other runtime/unexpected errors | 500; labels can mention reload when the flag is true |

The lazy-import helper constructs a configuration HTTPException, but the route's generic exception handler catches it again; do not assume the helper envelope passes through unchanged. Unhandled application-level exceptions use a separate flat 500 response with `error`, `status`, `details`, `support`.

The agent converts some timeout, context-limit and InvokeAgent/internal-server exceptions into friendly yielded text. Those can return HTTP 200 with `status=success`; status alone is not a reliable answer-quality or provider-success signal. Other exceptions are re-raised.

## Session and access boundaries

Identifiers are forwarded to Bedrock with `endSession=false`; the API does not store a local transcript or expose memory deletion. External agent memory settings determine persistence. There is no Python route authentication or identity ownership check. Both interfaces use the email local part as memory ID, which can collide across domains. Gateway access controls need separate verification.
