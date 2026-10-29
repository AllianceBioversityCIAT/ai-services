# Development and service-main differences

Initial comparison: development `edbb4b80` (`dev-fast-response`) and service-main `3431d9a3` (`main-fast-response`). Refresh references before the maintainer's local integration and repeat the comparison against the resulting tree.

## Current service comparison

The tracked service file paths are identical. The only implementation difference is `app/utils/logger/logger_util.py`; the guides also receive branch-specific wording during documentation promotion:

| Area | Development | Service-main |
| --- | --- | --- |
| Log directory | Service-relative `data/logs` | `/tmp/logs` |
| Log file | `data/logs/app.log` under the service | `/tmp/logs/app.log` |

Preserve the service-main path for its writable temporary filesystem. The development path is based on the source file's location, not the shell's current directory. Both variants initialize the directory/file at import, emit to stdout, rotate at 5 MiB with five backups, and use logger level DEBUG.

At this comparison, API routes, schemas, model ID/settings, region, dependency declarations/lockfile, Dockerfile, and local/Lambda entry points match. The rest of the monorepo can differ between branches; those snapshot differences do not authorize bringing unrelated services into a documentation change.

## Local service-main review

Reviewed merge `490599ca` against development `6fdaee10` and its service-main first parent `3431d9a3`:

- All development commits are included, with no missing tracked service paths.
- The merge changes only seven Markdown files relative to its service-main first parent: the shared guide and service documentation. It introduces no runtime, dependency, deployment, or other-service changes.
- Routes, schemas, model settings, AWS configuration, dependency declarations/lockfile, Dockerfile, and local/Lambda entry points match development. The intentional log-path difference remains intact.
- README, API/design guides, and agent instructions now identify `main-fast-response` and `/tmp/logs/app.log` as current. The quick start, system architecture, examples, project map, and troubleshooting remain available.

This repository comparison does not verify live AWS access, model output, a Jenkins run, or a deployment.

## Promotion checklist

1. Prepare documentation against development and let the maintainer merge development into service-main locally without pushing yet.
2. Review all incoming commits and the complete diff, including unrelated folders or automation. Compare tracked service paths, tests/interfaces, endpoint names, and manifests.
3. Preserve `/tmp/logs` in service-main. Do not replace it with development's service-relative path while resolving a documentation merge.
4. Adapt README, design, and agent-guide statements naming development's active log path to the actual service-main tree. Keep the comparison table accurate for both branches.
5. Run scoped documentation/offline checks; distinguish them from a live model call, pipeline result, or deployment validation.
6. The maintainer supervises pushes and promotion to staging. Completed service work accumulates there for the agreed consolidated PR to main.

## Workflow events

`.github/workflows/jenkins-trigger-fast-response.yml` triggers Jenkins on pushes to `main-fast-response`, pull requests whose base is `main-fast-response`, and manual dispatch. There is no documentation path exclusion.

No workflow matching `dev-fast-response` was found in the reviewed checkout. External Jenkins triggers cannot be inferred from that absence. This guide does not authorize pushing, release merges, or deployment.
