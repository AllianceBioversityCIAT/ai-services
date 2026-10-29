# Feedback service architecture

One FastAPI application accepts interaction records and optional later feedback. DynamoDB is active storage; RabbitMQ connects negative-feedback events to an external email worker. S3 code remains historical and is not an operational fallback.

## Request and startup boundaries

```mermaid
sequenceDiagram
    participant App as Application import
    participant DB as DynamoDB
    participant Caller as AI service / UI
    participant API as FastAPI
    participant Logic as AIInteractionService
    participant MQ as RabbitMQ
    App->>DB: Load table; create and wait if absent
    Caller->>API: POST interaction or feedback update
    API->>Logic: Validated AIInteractionRequest
    Logic->>DB: put_item or update_item
    opt Negative feedback
        Logic->>MQ: Best-effort email job publication
    end
    Logic-->>API: Interaction ID / status
    API-->>Caller: JSON (no delivery receipt)
```

Notification work is synchronous in this request path, although final delivery happens elsewhere. Failure to notify does not roll back persistence. Import itself can write infrastructure before any HTTP request.

## Ownership

| Boundary | Repository responsibility | External responsibility |
| --- | --- | --- |
| Ingress | FastAPI/Pydantic routes, CORS, error envelopes | Gateway authentication/authorization and TLS |
| Runtime | Uvicorn launcher, Mangum adapter, Lambda Dockerfile | Jenkins/image build and Lambda deployment |
| Persistence | Table naming, optional creation, record cleaning, scans, updates | AWS identity/policies, table availability, backup/encryption/retention settings |
| Registry | Process-local service metadata and request precedence | No durable registry infrastructure is implemented |
| Notifications | Email template, RabbitMQ envelope and best-effort publisher | Broker, consumer, delivery and downstream auth policy |

## Data and operational constraints

The table's composite key is interaction_id/service_name; it provisions a service/timestamp index but current reads scan. Search pagination happens after scanning and filtering in memory. The accepted has_feedback filter is ignored. Read failures can appear as empty data. Recent-summary entries do not guarantee the globally latest ten records.

The update path has no ownership/existence condition and can create partial records. No audit history, deletion API, rate limiting or retention management is implemented. The in-memory registry resets by process and can omit services that supplied metadata overrides.

Health reports process/registry state with a fixed timestamp, not storage/broker readiness. Request content and identifiers are persisted, and negative-notification messages can transfer them onward. CORS and outbound IAM do not establish caller authorization.

See the [API contract](API.md), [maintenance guide](TECHNICAL_DOCUMENTATION.md) and [branch review](BRANCH_DIFFERENCES.md) before changing contracts, storage or notifications.
