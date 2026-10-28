# Text Mining API guide

This guide covers the four mining workflows implemented in `app/mcp/client.py` and `app/mcp/server.py`. It describes application-level behavior in the development branch. Infrastructure controls and deployed URLs must be verified separately.

Run examples from a configured development environment. They use fictional keys and placeholders; mining calls can upload to S3 and invoke external services.

## Authentication

| Endpoint | HTTP dependency | MCP-side validation |
| --- | --- | --- |
| `/star/text-mining` | CLARISA `X-API-Key` for `AI Text Mining - STAR` | STAR management token |
| `/prms/text-mining` | CLARISA `X-API-Key` for `AI Text Mining - PRMS` | No STAR token validation |
| `/star/mining-bulk-upload/capdev` | CLARISA `X-API-Key` for `AI Bulk Upload - STAR` | STAR token plus a role in 1, 9, or 10 |
| `/aiccra/text-mining` | No CLARISA dependency on this route | Token fields are accepted but not validated by the current tool |

CLARISA receives the key, service name, endpoint, and client IP, with a five-second HTTP timeout. Non-200 validation responses or invalid keys return 401; authentication transport failure returns 503. A missing header is rejected by FastAPI's API-key dependency, with status depending on the installed version.

For STAR requests, `environmentUrl` must end in `/`: the tool appends `authorization/validate-token`. It sends the provided token as `access-token` in a PATCH request. An MCP authentication failure is not necessarily converted into HTTP 401; read the tool payload as well as the HTTP status.

## STAR document mining

`POST /star/text-mining` accepts multipart form data:

| Field | Requirement |
| --- | --- |
| `bucketName` | Required S3 bucket, including for direct uploads |
| `token` | Required STAR management access token |
| `environmentUrl` | Required management base URL with trailing slash |
| `key` | Existing S3 object key, when not uploading a file |
| `file` | Uploaded document, when not supplying a key |
| `user_id` | Optional interaction-tracking identifier |

Send one of `key` or `file`. The implementation rejects a request with neither input, but does not reject both: if a file is sent it is uploaded and its generated key takes precedence. Do not rely on a conflict response.

```bash
curl --request POST http://localhost:8000/star/text-mining \
  --header 'X-API-Key: YOUR_CLARISA_API_KEY' \
  --form 'bucketName=example-mining-bucket' \
  --form 'key=star/text-mining/files/test/report.pdf' \
  --form 'token=YOUR_STAR_ACCESS_TOKEN' \
  --form 'environmentUrl=https://your-management.example/'
```

For upload, replace the `key` form field with `--form 'file=@/path/to/report.pdf'`. Uploaded STAR files use `STAR_BUCKET_KEY_NAME` as the prefix.

The STAR pipeline retrieves reference catalogs, reads/chunks the document, embeds and retrieves relevant text with LanceDB, calls Bedrock, attempts field mapping, and formats results using [STAR schemas](../app/schemas/star_mining_schemas.py). Mapping failures can retain the original candidate; result formatting can drop invalid items.

## PRMS multisource extraction

`POST /prms/text-mining` accepts JSON. Its contract is separate from the multipart STAR contract:

```json
{
  "bucketName": "example-mining-bucket",
  "keys": ["prms/text-mining/files/test/report.pdf"],
  "audio_keys": [],
  "text": "Extract the completed outputs and outcomes described in these sources."
}
```

```bash
curl --request POST http://localhost:8000/prms/text-mining \
  --header 'Content-Type: application/json' \
  --header 'X-API-Key: YOUR_CLARISA_API_KEY' \
  --data '{"text":"Researchers completed a training activity and documented its participants and outcomes."}'
```

At least one non-empty source is required. A bucket is required for `keys` or `audio_keys`, but not for text-only input. An optional `user_id` enables an attempt to record the interaction. Unknown JSON properties are ignored by the current request model; they do not supply a source or replace CLARISA authentication.

Documents and audio must already exist in S3; this endpoint does not accept file uploads. Audio requires `PRMS_AUDIO_TRANSCRIBER=amazon_transcribe`. Six result indicators are supported; Knowledge Product is excluded.

Unlike the other HTTP mining routes, PRMS unwraps the MCP response and maps error payloads into HTTP errors. Success returns the logical results object directly, or a `json_content` wrapper with an interaction ID when tracking succeeds. See the [PRMS integration guide](prms-integration-guide.md) for schemas, configurable limits, and the HTTP error matrix.

## AICCRA document mining

`POST /aiccra/text-mining` accepts multipart `bucketName`, one of `key` or `file`, and optional `prompt`, `user_id`, `token`, and `environmentUrl`. The last two fields do not activate authentication in the current MCP implementation.

```bash
curl --request POST http://localhost:8000/aiccra/text-mining \
  --form 'bucketName=example-mining-bucket' \
  --form 'key=aiccra/text-mining/files/test/report.pdf' \
  --form 'prompt=Extract the climate adaptation activities and their reported outcomes.'
```

Uploaded files use `AICCRA_BUCKET_KEY_NAME` as the prefix. The file/key precedence is the same as STAR. When `prompt` is omitted, the workflow uses `DEFAULT_PROMPT_AICCRA`, also exposed by `GET /aiccra/prompt`.

The pipeline combines selected document chunks, reference catalogs, and the selected prompt. Its output is parsed JSON when recoverable; otherwise it can return a `text` fallback. It does not apply the PRMS MDS result models.

## STAR Bulk CapDev

`POST /star/mining-bulk-upload/capdev` accepts the STAR multipart fields plus:

| Field | Purpose |
| --- | --- |
| `skip_ids` | Optional comma-separated row IDs already submitted |
| `user_id` | Optional analytics identifier |
| `user_name` | Optional display name for analytics/notifications |

```bash
curl --request POST http://localhost:8000/star/mining-bulk-upload/capdev \
  --header 'X-API-Key: YOUR_CLARISA_API_KEY' \
  --form 'bucketName=example-mining-bucket' \
  --form 'key=star/text-mining/files/test/bulk_upload/training.xlsx' \
  --form 'token=YOUR_STAR_ACCESS_TOKEN' \
  --form 'environmentUrl=https://your-management.example/' \
  --form 'skip_ids=1,2'
```

Uploaded spreadsheets use `STAR_BUCKET_KEY_NAME/bulk_upload/`. Skipping uses row IDs extracted from the spreadsheet content, not a guarantee about physical spreadsheet row numbers.

For Excel, the implementation groups rows in batches of five by default and processes groups with bounded worker pools. Batch parsing/processing failures can appear inside the returned data. The caller must inspect records rather than equating HTTP success with every row succeeding.

## MCP wrappers and errors

STAR, AICCRA, and Bulk CapDev HTTP handlers return the MCP `CallToolResult` rather than the logical tool payload directly. Its `content` contains text that must be parsed. The tool's output may itself be JSON text; normalize each layer as needed.

The logical output can contain `json_content` and `interaction_id` when tracking succeeds. Supplying `user_id` does not guarantee an interaction ID: analytics may fail. Without tracking, STAR/AICCRA generally return their content directly; Bulk CapDev's Excel path returns serialized JSON text, which may require an additional parse after extracting the MCP content.

Tool failures in these three workflows can be encoded as `status: error` inside MCP content while the HTTP request still succeeds. Other upload or MCP transport failures become HTTP 500. PRMS has a dedicated unwrapping/error-mapping path and must not be decoded using the same assumptions.

Consult the actual response and generated schemas for the installed MCP version; do not assume one universal top-level `results` envelope across all four endpoints.

## Auxiliary routes

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/ui` | AICCRA static interface |
| GET | `/bulk-upload` | Development-only legacy bulk interface; absent from reviewed service-main |
| GET | `/aiccra/prompt` | Default AICCRA prompt |
| POST | `/list-s3-objects` | JSON `bucket`, optional `prefix` / `max_items` |
| GET | `/s3/list` | Query `bucket`, optional `prefix` / `max_items` |
| GET | `/s3/download-template` | Template download selected by `language` |
| GET | `/api/auth/token` | Base64-encodes configured UI client credentials; encoding is not encryption |
| GET | `/dynamo/bulk-upload-records/{file_name}` | Read status, links, and stored record information |
| POST | `/dynamo/bulk-upload-records` | Update one record status and metadata |
| POST | `/dynamo/bulk-upload-records/batch` | Apply a group of updates to a file's status item |
| POST | `/feedback` | Send feedback through the interaction service |
| GET | `/feedback/{interaction_id}` | Read feedback/interaction information |

The Dynamo update models are in `app/mcp/client.py`. Updates use `complete` or `failed` and can include links, title, contract, submission type, and year. A file item tracks lists and maps rather than a separate Dynamo row per extracted result. Writes use conditional-update retries to handle concurrent changes.

These auxiliary routes have no CLARISA dependency in their declarations. Infrastructure access controls require separate verification. The configured Dynamo tables and S3 destinations are not selected by the HTTP URL alone.

## Further reading

See the [frontend guide](../frontend/README.md) for BFF routes and the [branch comparison](BRANCH_DIFFERENCES.md) before promoting changes. `/docs` and `/openapi.json` reflect route schemas, but static descriptions and server lists in the application can lag implementation; this guide checks the handlers and tool code as well.
