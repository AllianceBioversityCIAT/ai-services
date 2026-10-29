# Feedback development and service-main

The integration path is `dev-feedback → main-feedback → staging → main`. This comparison records the baseline before the documentation task, not deployment status or the result of a future merge.

## Baseline inspected on 2026-10-29

| Reference | Commit |
| --- | --- |
| dev-feedback | b977cb64 |
| main-feedback | 3918ecd0 |

After refreshing origin, both local references matched their remote tips. `git diff dev-feedback main-feedback -- ai-feedback-service` was empty: all service files matched despite different commit histories. The complete repository tree comparison was also empty at that point. No production-only path, dependency, destination or environment default was identified in that baseline.

The shared behavior includes the Lambda Dockerfile/requirements install, SDK credential chain, literal ENV table suffix, /tmp/logs, DynamoDB import-time initialization, optional RabbitMQ notifications and historical inactive S3 files. Neither branch name selects an environment automatically.

## Documentation integration

This task prepares the root shared AGENTS.md from staging independently and service-specific documentation from development. It does not merge all of staging/main into development.

After the maintainer's local merge into main-feedback, compare entire service trees again. Inspect models/routes, startup/table behavior, dependencies, Docker, configuration, notifications, logs, tests and any local-only tools. Adapt service-main documentation to its resulting files; do not assume the initial equality persists.

## Pipeline boundary

`.github/workflows/jenkins-trigger-ai-feedback.yml` runs on push and pull_request targeting main-feedback plus workflow_dispatch. It invokes the feedback-service Jenkins job. Dev-feedback pushes do not match those branch filters. Documentation-only changes to the matching main branch can trigger it. Pipeline, table schema/data, broker and Lambda availability require separate live validation.
