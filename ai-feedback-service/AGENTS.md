# Feedback service: agent guide

Read [root instructions](../AGENTS.md), [README](README.md), [API contract](docs/API.md) and the relevant implementation. This guide describes dev-feedback; verify branch/tree and preserve local user files before editing.

## Scope and workflow

Use a focused task branch from dev-feedback when appropriate. Integration is task branch → dev-feedback → main-feedback → staging → main. The maintainer handles release merges unless delegated. After a local merge into main-feedback, compare full trees and adapt docs for actual runtime/config differences. Commit and push are separate requests. Preserve shared guide updates separately from service changes in commits/review.

## Implementation map

- Local entry: api_server.py → app.api.main:app, default port 8001. Lambda entry: main.handler; Docker installs requirements.txt on Python 3.13.
- Contract: app/api/models.py and routes.py. Active persistence: app/utils/feedback/feedback_util.py (AIInteractionService).
- Global service construction happens on import: AWS clients/table load and possible table creation happen before FastAPI lifespan.
- Configuration: BR, ENV and RABBITMQ in config_util.py. Active DynamoDB clients use SDK credentials; ENV literally selects the table suffix.
- Email: app/utils/microservices/send_email.py; read [nested instructions](app/utils/microservices/AGENTS.md) before changing notifications.
- feedback_util_s3.py and S3 upload helper are historical, with stale model/config imports. Do not wire them into active startup as a documentation fix.

## Constraints

Use requirements.txt for the Docker-compatible install; pyproject has the same direct dependencies and no lock is tracked. Run from the service directory. Logs always use /tmp/logs despite ENV-related commented code.

Coordinate caller payloads, models/routes and docs for changes. Preserve DynamoDB composite keys, ENV behavior and request metadata precedence unless explicitly changing behavior. Prompt/content templates, notification recipients/auth, IAM/access, filtering, identity and scoring/rates are behavior changes.

Document current limits honestly: has_feedback is ignored in search; update_mode without ID creates; update has no ownership/existence condition and comment-only calls can fail SDK validation; scan errors can appear empty; recent summaries and registry are not authoritative global views. Health is not a dependency probe. Negative notifications are best effort and may contain full content; do not send real messages during docs validation.

## Safe validation

No dedicated service tests are tracked. For offline checks, block network and replace boto3 before importing app/service, as ordinary import can create a table. Replace logger and notification transport to avoid generated files and email. Exercise actual models/service methods with fictional records and in-memory tables; validate links and example syntax. A fake pika transport checks payload shape only.

Do not install into another service environment or change code/manifests/deployment just to make docs checks pass. Do not commit .env, logs, exports, databases or real reporting content. Report checks/limits and branch/commit/push state; do not claim live AWS, RabbitMQ delivery, backup/retention or Jenkins validation from stubs.
