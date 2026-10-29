# Fast Response API guide

This documents the implementation on `main-fast-response`. Start/configure the service through its [README](../README.md). The API has three application routes plus FastAPI's generated documentation endpoints.

## Routes

| Method/path | Request | Response/effects |
| --- | --- | --- |
| `GET /` | No body | Service/version/docs/endpoints metadata |
| `GET /health` | No body | Process health metadata; no Bedrock call |
| `POST /api/fast-response` | JSON `prompt`, `input_text` | Synchronous Bedrock invocation and JSON generation result |

No token/API-key dependency or rate limit is defined on these routes. CORS allows all origins, methods, and headers with credentials enabled; CORS is browser policy, not authorization. Deployed access controls are outside this code review.

## Generation request

Both fields are required strings. There is no local nonempty/minimum/maximum-length constraint. Empty strings pass Pydantic validation; that does not establish provider acceptance.

```json
{
  "prompt": "Summarize in one sentence",
  "input_text": "Example farmers rotate crops and conserve water."
}
```

The generation code builds exactly `prompt + ": " + input_text` and sends it as one user text block. It does not use a separate system message, chat history, retrieval context, or prompt template store.

The current Bedrock request uses `us.anthropic.claude-sonnet-4-6` in `us-east-1`, with 4,000 output tokens, temperature 0.1, and Anthropic messages version `bedrock-2023-05-31`. These are code constants, not documented environment overrides.

## Success

HTTP 200 returns `FastResponse` with the original input values, generated output, and `status: "success"`:

```json
{
  "prompt": "Summarize in one sentence",
  "input_text": "Example farmers rotate crops and conserve water.",
  "output": "The example describes crop rotation and water conservation.",
  "status": "success"
}
```

The output above is illustrative, not an expected literal model response. Parsing reads only `content[0].text` from the provider body; it does not concatenate every block. `stop_reason` and token usage are logged but omitted from the API response. A non-`end_turn` result, including possible truncation, can still produce HTTP 200.

The endpoint returns one complete JSON result. It has no streaming response, asynchronous job ID, conversation persistence, or provider usage fields.

## Errors

Missing fields, wrong JSON field types, or malformed JSON generally produce FastAPI validation HTTP 422, with a `detail` list. For example, the relevant portion for a missing field is:

```json
{
  "detail": [
    {
      "loc": ["body", "prompt"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

This is an abbreviated shape; validation details can also include the submitted input and vary with installed Pydantic/FastAPI versions.

Exceptions caught by the generation route are wrapped by FastAPI under `detail`:

| Condition | HTTP status | Inner `error` |
| --- | --- | --- |
| `ValueError` while generating/parsing | 400 | `Invalid parameters` |
| Other caught generation exception | 500 | `Internal error` |

Illustrative route error:

```json
{
  "detail": {
    "error": "Internal error",
    "details": "Fictional provider failure",
    "status": "error"
  }
}
```

The separate global exception handler returns a flat `error`, `status`, and generic `details` object for otherwise unhandled exceptions. It is not the normal wrapper used by the route's caught exceptions. Provider exception strings can appear in caught-route `details`; avoid sharing real error bodies containing sensitive information.

The declared `ErrorResponse` in OpenAPI describes inner fields but does not show the actual `HTTPException.detail` wrapper. Integrations must handle the implemented envelope. There is no explicit mapping of AWS failures to separate 401/403/429/502 statuses in this route.

## Runtime and operational limits

The async route directly calls synchronous boto3 generation. Its client uses 60-second connect timeout, 300-second read timeout, and adaptive retries configured with `max_attempts=3`; these settings do not establish a total response-time bound. Caller, gateway, and Lambda timeouts may differ. A timed-out caller does not prove the model invocation did not occur.

Health only returns static process metadata. A reachable health endpoint does not validate Bedrock access, model output, or end-to-end generation. Real generation calls invoke a paid external provider and log the full supplied prompt. Use fictional data for examples and block network during offline tests.

See [design](HIGH_LEVEL_DESIGN.md) for components and [branch differences](BRANCH_DIFFERENCES.md) for log destinations before promotion.
