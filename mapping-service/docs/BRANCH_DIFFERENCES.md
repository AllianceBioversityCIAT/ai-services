# Development and service-main differences

Initial comparison: development `50c3093c` (`dev-mapping`) and service-main `4bf1c713` (`main-mapping`). Refresh references and inspect the full incoming diff before the maintainer's local integration.

## Files and dependencies

All development service paths are present in service-main. Service-main additionally contains `mapping-service/Dockerfile`.

| Area | Development | Service-main |
| --- | --- | --- |
| Dockerfile | Absent | Lambda Python 3.13 image, `main.handler` |
| `requirements.txt` | Does not include `mangum` | Includes `mangum` |
| `pyproject.toml` | Includes `mangum` | Same declaration as development |
| Dependency lockfile | No tracked lockfile | No tracked lockfile |
| Logger | Fixed service-relative `data/logs` | Resolver plus handler guard, described below |

API routes/schemas, query construction, normalization, prompts, environment/index selection, LLM parsing, config, and local/Lambda entry-point code match at this comparison. Differences elsewhere in the monorepo are branch snapshots, not permission to bring unrelated service changes into this update.

## Logger behavior to preserve

Development creates service-relative `data/logs` directly and installs stdout/file handlers at import. It does not read `LOGS_DIR` or provide a directory fallback.

Service-main tries directory creation in this order:

1. The value of `LOGS_DIR`, when set.
2. Service-relative `data/logs`, based on the source file's resolved location.
3. `/tmp/mapping-service/logs`.

An `OSError` during directory creation advances to the next candidate. If all candidates fail, the resolver raises a runtime error. File-handler initialization follows the choice and can still fail independently. Handlers are added only when the logger has none, unlike development's unconditional installation.

Both variants use stdout plus `app.log`, logger level DEBUG, 5 MiB rotation, and five backups. Do not simplify service-main to a fixed `/tmp/logs` path copied from another service.

## Packaging to preserve

The service-main Dockerfile installs its requirements, copies app/handler files, explicitly copies `.env`, then copies the context, and starts `main.handler`. Git ignore rules do not exclude Docker inputs. Preserve the existing packaging file and the Mangum requirement unless a separate deployment change is requested. A tree difference does not by itself establish whether a future merge will delete or retain the file; inspect the actual resulting merge.

## Promotion checklist

1. Prepare development docs, then let the maintainer merge development into service-main locally before pushing.
2. Compare the complete incoming diff and service trees. Check that the main-only Dockerfile, Mangum requirement, and logger resolver/guard remain intact.
3. Verify route/schema/prompt/config parity and any missing interfaces, examples, or dependency differences; do not assume a clean merge proves parity.
4. Adjust service-main README, architecture, API and agent documentation to its actual packaging, dependency installation, and log selection. Keep this comparison accurate for both branches. Do these authorized documentation adjustments as part of the review.
5. Run scoped offline/documentation checks and report results separately from live provider/pipeline/deployment checks.
6. The maintainer supervises pushes and promotion to staging. Completed service updates accumulate there for the agreed consolidated PR to main.

No Mapping-specific GitHub workflow was found in the reviewed checkout. This does not establish external Jenkins behavior or mean a push cannot deploy. Documentation preparation does not authorize release merges, pushes, builds, or deployments.
