# AI Insights API guide

The API supports project overviews and a managed prompt registry. Examples use fictional buckets, folders, and credentials. No upload endpoint is defined: documents must already be in the request's S3 folder.

## Authentication

| Operation | Application authentication |
| --- | --- |
| `POST /api/document-overview` | CLARISA `X-API-Key` for `AI Insights Service - STAR` |
| `POST /api/prompts` | CLARISA `X-API-Key` for `AI Insights Service - STAR (Prompt Update)` |
| `GET /api/document-overview` | No CLARISA dependency on this route |
| `POST /api/document-overview/files/delete` | No CLARISA dependency on this route |
| `GET /api/prompts` | No CLARISA dependency on this route |
| `GET /`, `/health`, `/docs`, `/redoc`, `/openapi.json` | No application authentication dependency |

CLARISA receives the key, microservice name, accessed endpoint, and client IP, with a five-second timeout. Invalid keys or non-200 validation responses produce 401; transport failure produces 503. Missing keys are rejected by FastAPI's API-key dependency; the exact status depends on the installed version.

`Access-Token` is a separate optional header used for STAR metadata retrieval, not a replacement for `X-API-Key`. Its value is sent to STAR as a Bearer token. `STAR_API_TOKEN` is the configured fallback. Missing STAR credentials skip that context rather than rejecting the generation request solely for missing a STAR token.

Additional infrastructure controls must be verified separately. The included Function URL template uses `AuthType: NONE`; it does not establish CLARISA authentication on the unprotected route declarations above.

## Generate a project overview

`POST /api/document-overview` accepts JSON:

```json
{
  "bucket_name": "example-project-documents",
  "project_folder": "projects/EXAMPLE-001",
  "text": "Summarize the completed activities and identify gaps in the available evidence."
}
```

```bash
curl --request POST http://localhost:8000/api/document-overview \
  --header 'Content-Type: application/json' \
  --header 'X-API-Key: YOUR_CLARISA_API_KEY' \
  --header 'Access-Token: YOUR_STAR_ACCESS_TOKEN' \
  --data '{"bucket_name":"example-project-documents","project_folder":"projects/EXAMPLE-001"}'
```

| Field | Requirement |
| --- | --- |
| `bucket_name` | Required S3 bucket, even when no documents are present |
| `project_folder` | Required project prefix; its final path segment supplies the STAR contract ID |
| `text` | Optional free-text context, stored and returned with the response |
| `user_id` | Optional interaction-tracking identifier |

The request does not accept a file upload or an arbitrary prompt override. Generation loads the active `project-overview` prompt through the Prompt Manager implementation.

The service lists the folder, excludes `response.json`, ignores unsupported documents for generation, and rejects more than three supported files (two when `text` is truthy). It does not silently select the first files. Empty folders are allowed if STAR context or text supplies input. Without any of these sources, generation returns 400.

`text` is not stripped before source/limit decisions. Send null or an empty string to omit it; a whitespace-only string is currently truthy and reduces the document limit.

Supported extensions are `pdf`, `jpg`, `jpeg`, `png`, `tiff`, `tif`, `docx`, `txt`, `xls`, `xlsx`, and `pptx`. PDFs and images use Textract. Other files use standard readers. Extracted document text is capped at 3,000,000 combined characters; this is not a complete limit on STAR context, user text, or model tokens.

### Response

| Field | Meaning |
| --- | --- |
| `overview` | Model-generated dictionary; can include `raw_response` if the model did not return parseable JSON |
| `time_taken` | Generation-processing duration as a string; not a guaranteed HTTP deadline |
| `project_folder`, `bucket_name` | Project/storage identifiers |
| `documents_processed` | File key/name, extraction method (`textract` or `standard`), and character count |
| `text` | Received free text, defaulting to `""` |
| `interaction_id` | Optional ID when requested analytics tracking succeeds |
| `status` | Normally `success` on generation |
| `generated_at` | UTC timestamp |
| `cached` | False for the generation response |

The API validates the response envelope, not the truth of every overview claim. Parsed model JSON must still fit the dictionary response shape. A fresh generation attempts to overwrite `<project_folder>/response.json`. Cache-write failure is logged without failing an otherwise completed generation.

## Retrieve cache and available files

`GET /api/document-overview` takes query parameters:

```bash
curl --get http://localhost:8000/api/document-overview \
  --data-urlencode 'bucket_name=example-project-documents' \
  --data-urlencode 'project_folder=projects/EXAMPLE-001'
```

The response extends the overview envelope with `available_files`, containing current file keys and names. Listing excludes folder markers, zero-size objects, and `response.json`; it may include formats that generation later skips.

With a saved response, `cached` is true. Without one, the route returns HTTP 200 with an empty overview, empty document list, `text: ""`, `status: empty`, and `cached: false`. GET does not invoke Bedrock or regenerate an outdated cache.

Current files and cached processed files can differ. Deleting an input, adding an input, editing prompt sections, or changing STAR metadata does not automatically invalidate `response.json`. Call generation explicitly to refresh it.

## Delete project documents

`POST /api/document-overview/files/delete` accepts JSON:

```json
{
  "bucket_name": "example-project-documents",
  "project_folder": "projects/EXAMPLE-001",
  "file_names": ["obsolete-report.pdf"]
}
```

Supply file names, not full S3 paths. The body requires at least one name. The helper rejects blank names, names still containing `/` after leading-slash normalization, and `response.json`. It deletes each named object under the prefix and returns `deleted_files` with `status: success`.

Deletion is sequential, not a transactional batch: an invalid later name or storage failure can occur after earlier deletions. S3 deletion success does not prove the object previously existed. The saved overview is retained and is not regenerated by this operation.

## Read and replace managed prompts

`GET /api/prompts` returns `prompts`, currently containing the registered `project-overview` prompt. A record includes:

- `id`, `name`, `description`, and the ordered `sections` list.
- `variables`, describing placeholders and whether each is required.
- `default_prompt`, always derived from current code defaults.
- `user_prompt`, the saved active sections, falling back to defaults when absent or unreadable.
- `is_modified`, `created_at`, `updated_at`, and `updated_by`.

A missing record is returned from defaults without writing a new S3 object. Read failures are logged and also fall back to defaults. These behaviors can produce a successful read with null timestamps when no stored prompt was available.

`POST /api/prompts` replaces the entire `user_prompt` for a known ID. This illustrative payload is structurally valid and deliberately changes prompt behavior; it is not the shipped default:

```json
{
  "id": "project-overview",
  "user_prompt": {
    "system_role": "You summarize research projects using only supplied information.",
    "context": "Sources: {available_context_sources}\nProject: {project_information}\nResults: {project_results}\nEvidence: {uploaded_evidence}\nUser context: {user_input}",
    "user_instructions": "Write a concise overview and state important evidence limitations.",
    "expected_output_format": "Return only a JSON object with summary and limitations fields."
  },
  "updated_by": "example-editor"
}
```

Send all four non-blank sections: `system_role`, `context`, `user_instructions`, `expected_output_format`. Required variables must appear exactly once across the combined sections, but may move between sections. Missing, unknown, or duplicated variables are rejected. The current five required names are shown in the example.

An unknown prompt ID, blank section, or invalid placeholders produces 400. Missing schema fields or empty strings can instead fail Pydantic validation with 422. A storage failure during the final write produces 500. The successful response is the updated prompt record, and subsequent generation calls read the saved version.

Prompt records are stored at `PROMPTS_BUCKET_NAME/PROMPTS_PREFIX/<id>.json`. The default text is not overwritten. Resetting means submitting all current default sections again; no separate reset endpoint is defined. `updated_by` is caller-supplied metadata, not an identity derived from the API key. The current writer overwrites the object without a revision precondition or application-level version history.

## Errors and limitations

| HTTP status | Typical cause |
| --- | --- |
| 400 | Generation/input limit failure, no usable context, invalid file name, unknown prompt, or placeholder validation failure |
| 401 | CLARISA rejection/non-200 validation response |
| 422 | Pydantic input validation failure |
| 503 | CLARISA transport unavailable |
| 500 | Unexpected processing, model, storage, or extraction failure |

Route-generated errors often use `detail` with `error`, `status`, and `details`. Framework validation and the global exception handler can have different envelopes. HTTP 200 cache/prompt reads may represent empty/default data, and HTTP 200 generation may contain a raw-text fallback or lack a successfully saved cache. Handle those cases explicitly.

Use the [high-level design](HIGH_LEVEL_DESIGN.md) for timeouts, extraction, storage behavior, and validation boundaries.
