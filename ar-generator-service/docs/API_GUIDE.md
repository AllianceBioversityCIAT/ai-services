# AICCRA Report Generator API

This guide describes `main-ar-generator`, whose packaged entry point is `api_server.handler` and whose active structured loader is SQL Server. Development's local CSV/MySQL path differs; read [branch differences](BRANCH_DIFFERENCES.md). Parameter schemas and executable code take precedence over older generated Swagger prose.

## Application routes

| Method/path | Input and response |
| --- | --- |
| `GET /` | Metadata; some technology/year descriptions are historical |
| `GET /health` | Static process status, service, version; no provider/data checks |
| `GET /web` | HTML file response, not a separate frontend server |
| `/static/*` mount | Static assets under web/ |
| `POST /api/generate` | Mid-year narrative, `ChatResponse` |
| `POST /api/generate-annual` | Annual narrative, `ChatResponse` |
| `POST /api/generate-annual-tables` | Year, grouped table arrays, status |
| `POST /api/generate-challenges` | Year, content, status |

Swagger/ReDoc/OpenAPI are available at the standard configured paths. No `/api/update-chatbot-data` operation is implemented by these routes, despite a development cron script using that URL. Production's EventBridge job dispatch is a Lambda-event interface, not that missing HTTP route.

No general FastAPI token/API-key dependency protects the report routes. CORS allows all origins/methods/headers with credentials enabled. Verify external controls separately; IAM permissions for outbound AWS calls do not establish caller authentication.

## Shared request model

All four POST operations use `ChatRequest`:

```json
{"indicator":"IPI 1.3","year":2025,"insert_data":false}
```

| Field | Implemented validation |
| --- | --- |
| `indicator` | Required string; not a Literal/Enum of the advertised indicators |
| `year` | Required integer constrained to 2021–2026 |
| `insert_data` | Optional boolean, default false; explicit null is accepted by the nullable model |

Tables and challenges require indicator for schema validation but do not use it to select one indicator; both operate by year at route level. Their route bodies also do not forward insert_data. Challenges' current data helper loads all challenge rows without a year filter, so year in the response/prompt is not proof of filtered source data.

Missing/invalid fields normally produce FastAPI HTTP 422. Extra browser fields such as user_email/user_name are not declared in this model and do not add authentication or a requester contract here.

## Successful shapes

Narrative endpoints:

```json
{
  "indicator":"IPI 1.3",
  "year":2025,
  "content":"# Fictional example report. Review against source evidence.",
  "status":"success"
}
```

Tables return groups `PDO`, `IPI 1.x`, `IPI 2.x`, and `IPI 3.x`. Current row keys are generated from the year:

```json
{
  "year":2025,
  "tables":{
    "PDO":[{
      "Indicator statement":"Fictional example indicator",
      "End-year target 2025":100,
      "Achieved in 2025":90,
      "Brief overviews":"Fictional cluster summary."
    }],
    "IPI 1.x":[],
    "IPI 2.x":[],
    "IPI 3.x":[]
  },
  "status":"success"
}
```

Challenges response:

```json
{"year":2025,"content":"# Fictional challenges report","status":"success"}
```

All shown narratives/data are illustrative. There is no public token stream, persistent job identifier, completion polling endpoint, provider usage object, or evidence-validation result in these responses. Bedrock's stream is accumulated internally. The mid-year route iterates the pipeline's returned string, then returns a complete JSON body.

## Responses and failure semantics

| Situation | Implemented result |
| --- | --- |
| Mid-year pipeline returns None | Iteration fails; route produces HTTP 500 |
| Mid-year pipeline returns report-error text | Text can still be returned with HTTP 200/status:success |
| Annual pipeline returns None | HTTP 200/status:error with failure content |
| Annual pipeline returns text starting `# Report Generation Error` | HTTP 200/status:error with that content |
| Challenges helper returns no-data/error prose | Route can still return HTTP 200/status:success |
| Table/other provider errors propagate to route | Mapped to the applicable route exception response |

Check `status`, content, and logs rather than treating a 2xx response as proof of a usable evidence-based report. Data/retrieval/ingestion helpers sometimes log and return empty structures or zero counts instead of raising; generation can proceed with missing evidence.

Routes map caught ValueError to 400 and RuntimeError/other exceptions to 500. The two narrative routes also map PermissionError to 403; tables/challenges do not have that separate branch. Route errors use FastAPI's `detail` wrapper:

```json
{"detail":{"error":"Invalid request parameters","details":"Fictional validation failure","status":"error"}}
```

The app's separate global exception handler returns flat error/status/details/support for otherwise unhandled exceptions. Lazy import helpers still mention OpenSearch in some messages even when the active path is S3 Vectors; inspect the actual exception/log instead of assuming the named backend is current.

## Rebuild and external effects

On narrative endpoints only, insert_data:true recreates the entire configured S3 Vectors index and ingests five mid-year or six annual tables. It is not limited to the request's indicator/year. Both use the same resource configuration, with no transaction or documented lock around rebuild/query concurrency. The bucket must already exist.

Generation with insert_data:false still loads structured data, queries AWS, and invokes models. This branch's SQL loader can alter views and export source files to S3 even without rebuilding vectors. It logs under /tmp and omits development's explicit context JSON dumps. A timeout is not evidence that no effects occurred or that a durable background job completed.

The current routes call synchronous pipeline code directly. Annual code parallelizes selected model work using threads, but that does not make the HTTP request a durable asynchronous job. Offline mocks do not verify live service limits, provider timeouts, permissions, model accuracy, or deployment behavior.

## Production startup and scheduler events

The HTTP API eagerly imports the SQL loader/export stack, and the packaged hybrid handler also imports scheduled jobs and the annual pipeline. Missing pyodbc/native ODBC or import-time provider configuration can prevent startup before any health request. The process health body itself still does not query those dependencies.

Report-source SQL transformations restrict several source families to 2025/2026 even though the public model accepts 2021–2026. Acceptance of a requested year does not guarantee available source rows. The CSV override applies only to load_data; chatbot load_full_data remains a SQL/export path.

A job-only Lambda event such as `{"job":"sync_knowledge_base"}` is dispatched separately from HTTP. Recognized jobs are update_ar_data, update_chatbot_data, and sync_knowledge_base. Adding HTTP event keys routes to Mangum instead. This is not a public job-submission endpoint or a safe probe: jobs can rebuild vectors, alter/read SQL, export data, start KB ingestion, and send Slack notifications. See [operations](TECHNICAL_DOCUMENTATION.md#scheduled-operations).
