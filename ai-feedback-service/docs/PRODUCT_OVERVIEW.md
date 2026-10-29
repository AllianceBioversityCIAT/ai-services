# Interaction tracking product overview

AI-service owners use this backend to record usage, collect optional feedback and inspect service-level counts, satisfaction and response times. Callers include service backends and interfaces; there is no feedback dashboard or model-generation UI in this service.

## Main workflow

1. A caller records an interaction after an AI response and retains the generated ID.
2. A user can submit positive/negative feedback immediately or later through the same endpoint in update mode.
3. Negative feedback attempts an email notification through RabbitMQ and an external worker.
4. Maintainers inspect search results and aggregate summaries, with their documented filtering/read limits.

Feedback is optional: interaction volume and feedback volume are different measures. Satisfaction is positive feedback divided by records marked as having feedback, not an assessment of every response. Service display metadata can be supplied by callers and is not verified identity.

## Current boundaries

Active storage is DynamoDB with a literal environment-specific table suffix. Service registry metadata is process-local. S3 is historical code, and a manual registration endpoint is not implemented. No live dashboard, AI quality evaluator, durable notification retry system or benchmarked latency target is established here.

Search has an ignored has_feedback field, summaries can hide read failures as zero results, and recent records are not guaranteed globally newest. Notification/API success is not a delivery receipt. Updates have no ownership/existence guard or complete audit history. Infrastructure backup, encryption, authorization and retention policies must be verified separately.

Use fictional data for integration examples and validate what may be stored and emailed. See the [README](../README.md), [API contract](API.md) and [architecture](HIGH_LEVEL_SOFTWARE_DESIGN.md).
