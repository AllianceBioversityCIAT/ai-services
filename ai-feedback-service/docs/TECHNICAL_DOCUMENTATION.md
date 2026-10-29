# Feedback service maintenance

This guide describes `main-feedback`. The active service tracks interactions in DynamoDB and optionally publishes negative-feedback email jobs. Use the [README](../README.md) for onboarding and [API contract](API.md) before changing callers.

## Entry points and import effects

`api_server.py` launches `app.api.main:app` on port 8001 by default. `main.py` wraps the same app as `main.handler` with Mangum. Docker uses Lambda Python 3.13 and requirements, not a local Uvicorn container entry point.

Import chain: app.api.main → routes → feedback_util → send_email/config/logger. At the end of feedback_util, `ai_interaction_service = AIInteractionService()` constructs AWS clients, loads the table and may create it. Table initialization happens before the FastAPI lifespan, so starting the app or importing the module is not read-only/offline. Email service construction loads config but connects to RabbitMQ only when sending.

## Module map

| Module | Responsibility |
| --- | --- |
| app/api/models.py | Request/response validation, nullable fields and limits |
| app/api/routes.py | Create/update, summary/search and two legacy-prefixed GET routes |
| app/api/main.py | App, lifespan logs, CORS, metadata, registry-based health, global errors |
| app/utils/feedback/feedback_util.py | Active AIInteractionService and global instance |
| app/utils/microservices/send_email.py | RabbitMQ connection, durable queue, email payload/template |
| app/utils/config/config_util.py | BR, ENV and RABBITMQ dictionaries |
| app/utils/logger/logger_util.py | DEBUG console and /tmp/logs/app.log, 5 MiB/five-backup rotation |
| app/utils/feedback/feedback_util_s3.py | Historical inactive S3 service, imports removed models |
| app/utils/s3/upload_file_to_s3.py | Historical helper, imports missing S3 config symbol |

## DynamoDB design

The literal table name is `ai-requests-{ENV}`. ENV is not validated and has no default; missing ENV produces the suffix None. The service resource/client use AWS_REGION and the SDK credential chain, not explicit keys from BR.

The table has string partition key interaction_id and sort key service_name, on-demand billing, and an ALL-projection GSI ServiceTimestampIndex keyed by service_name/timestamp. Startup calls Table.load; ResourceNotFoundException triggers create_table and wait_until_exists. Other startup client errors propagate. Existing tables are not migrated or checked for schema/index drift.

Creates generate req_UUID, build content/identity/service/context/length metadata, clean the record and call put_item. Cleaning removes None/empty strings/empty containers and converts floats to Decimal recursively through dictionary/list handling. Arbitrary nested context is not a schema or retention guarantee. Metadata flags are calculated before cleaning: an empty-string comment can leave has_comment true after its field is removed.

Updates use update_item without an existence condition, authorization check, version check or transaction. They set feedback flags/comment/timestamp, leaving content and derived metadata unchanged. An unknown key can upsert a partial record. ExpressionAttributeNames is None when feedback_type is absent and can fail SDK validation. A true update flag with no ID follows create instead. See [contract limitations](API.md).

Read helpers use table scans with optional service/date conditions and LastEvaluatedKey pagination. They do not query the GSI. Search filters/sorts/slices after loading results; has_feedback is unused. Scan errors become empty lists. Summary recent entries are the first ten scanned, then sorted. These choices affect cost, completeness and error interpretation.

## Service metadata

Each process seeds chatbot metadata in memory. Both request overrides take priority; either single override fills the other value generically and returns without registration. With no overrides, the registry is used or an unknown name auto-registers. Registry entries are not stored/rebuilt from DynamoDB. Manual register_service is a Python method, not an HTTP registration endpoint.

## Notification boundary

A saved negative record or update calls _send_negative_feedback_notification. It collects stored identity/content/context into an email data dictionary. send_negative_feedback_email connects as needed, constructs the message and publishes to the configured queue. Exceptions/false send results are best effort; persistence and notifications are not atomic. The outer service does not inspect the boolean send result before logging success, so logs/API success do not prove queueing or delivery.

RabbitMQ uses the default exchange, queue-name routing key, a durable queue, delivery_mode 2 and JSON content. The envelope is pattern=send with data.auth (MS_AUTH_USER/MS_AUTH_PASSWORD) and data.data (from/emailBody fields). Broker connection credentials are in RABBITMQ_URL, separate from the downstream auth fields. There is no publisher-confirm/delivery-receipt workflow here. Repeated negative feedback can send repeatedly.

The template includes user input (truncated to 500 characters), full AI output, comments, identity and context. It assumes some input types; an optional user_input=None on a new negative record can fail email formatting and still leave the record saved. Do not test real notifications with reporting data. The worker and final transport/delivery are external.

## Configuration and packaging

Dependencies match between pyproject.toml and requirements.txt; no lockfile is tracked. Docker actually installs requirements and copies .env plus full context. Keep secrets and artifacts out of images/commits; this documentation does not change packaging. ENV does not switch the current logger away from /tmp/logs.

The workflow jenkins-trigger-ai-feedback.yml triggers feedback-service on push/PR to main-feedback and manual dispatch. The reviewed local merge preserved the same service code, Dockerfile, dependencies and configuration as development; see the [merge comparison](BRANCH_DIFFERENCES.md). Subsequent branch-specific documentation edits do not imply runtime differences. Compare full trees again after future integrations.

## Offline checks

No dedicated test suite is tracked. Parse links/JSON/Python/shell examples and compare fields/routes with implementation. Before importing, replace boto3 resource/client, logger, and notification transport; block network. Use in-memory tables to verify creation, cleaning, updates, scans, pagination, metadata and summaries. Where pika is unavailable, a fake transport can verify payload construction but cannot validate the installed broker client or delivery.

Never use successful startup, health, empty search, fake queues or HTTP success as proof of live storage, email, backup/retention or deployment. Record those limits and the current commit/push state.
