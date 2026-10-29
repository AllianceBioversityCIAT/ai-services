# Feedback service-main merge review

The integration path is `dev-feedback → main-feedback → staging → main`. This guide records the local service-main merge review and the environment-dependent behavior to preserve. It does not establish pipeline or deployment success.

## Reviewed on 2026-10-29

| Reference | Commit at review |
| --- | --- |
| dev-feedback and origin/dev-feedback | 72ef337a |
| Local main-feedback merge | 7aaa26e7 |
| origin/main-feedback before push | 3918ecd0 |

After refreshing origin, all development commits were included in the local merge. Before branch-specific documentation edits, `git diff dev-feedback HEAD -- ai-feedback-service` was empty on main-feedback. The complete repository trees also matched at that point. There were no missing service files, interfaces, tests or production-only routes/configuration to reconcile.

Relative to origin/main-feedback, the incoming service changes were documentation, agent guides and the placeholder environment example. Python application files, Dockerfile, requirements and pyproject were unchanged. The merge also brought in a root AGENTS.md and an existing Text Mining frontend .gitignore; those inherited changes were preserved.

## Shared runtime behavior

| Area | Verified behavior on the resulting service-main |
| --- | --- |
| Local HTTP / Lambda | api_server.py launches app.api.main:app on port 8001; main.handler is the Mangum adapter |
| Packaging | Lambda Python 3.13 Dockerfile installs requirements and copies .env/full context |
| Dependencies | requirements.txt and pyproject.toml match; no tracked lockfile |
| AWS credentials | SDK credential chain for active DynamoDB resource/client |
| Table selection | Literal ai-requests-{ENV}; no branch-based default or validation |
| Startup | Application import loads the table and may create it |
| Logs | Console and /tmp/logs/app.log regardless of ENV |
| Notifications | Optional best-effort RabbitMQ email publication after negative-feedback persistence |
| Historical S3 files | Retained, inactive and contain stale imports; not a supported fallback |

`.env.example` keeps ENV=testing as a local example. It does not declare or select the deployed environment. Actual AWS identity, environment suffix and RabbitMQ/recipient configuration must be checked in the intended deployment. Do not change a value to prod merely because the branch is named main-feedback.

## Documentation adjustments

The service README, agent guide, API guide and technical guide describe main-feedback. Technical documentation stays in docs/TECHNICAL_DOCUMENTATION.md, with local links resolved from its current directory. The example's deployment distinction is clarified in comments; application/deployment behavior is unchanged.

For future integrations, compare complete service trees again: contracts, startup/table behavior, dependencies, packaging, credentials, environment selection, notifications, logs and any added tests/interfaces. Matching trees in this review are not a permanent guarantee of parity.

## Pipeline boundary

`.github/workflows/jenkins-trigger-ai-feedback.yml` runs on push and pull_request targeting main-feedback plus workflow_dispatch. It invokes the feedback-service Jenkins job. Documentation-only changes on the matching main branch can trigger it. Wait for the relevant pipeline before promotion to staging; local checks do not validate live table data/schema, broker delivery, deployment or Jenkins.
