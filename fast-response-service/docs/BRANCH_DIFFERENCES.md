# Development and service-main differences

Initial comparison: development `edbb4b80` (`dev-fast-response`) and service-main `3431d9a3` (`main-fast-response`). Refresh references before the maintainer's local integration and repeat the comparison against the resulting tree.

## Current service comparison

The tracked service file paths are identical. The only content difference is `app/utils/logger/logger_util.py`:

| Area | Development | Service-main |
| --- | --- | --- |
| Log directory | Service-relative `data/logs` | `/tmp/logs` |
| Log file | `data/logs/app.log` under the service | `/tmp/logs/app.log` |

Preserve the service-main path for its writable temporary filesystem. The development path is based on the source file's location, not the shell's current directory. Both variants initialize the directory/file at import, emit to stdout, rotate at 5 MiB with five backups, and use logger level DEBUG.

At this comparison, API routes, schemas, model ID/settings, region, dependency declarations/lockfile, Dockerfile, and local/Lambda entry points match. The rest of the monorepo can differ between branches; those snapshot differences do not authorize bringing unrelated services into a documentation change.

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
