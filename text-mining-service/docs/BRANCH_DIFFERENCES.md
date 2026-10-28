# Text Mining: development and service-main differences

Before pushing an integration to `main-text-mining`, compare its resulting tree with development and adapt its documentation. A completed merge does not mean the two branches should have identical files or environment destinations.

This is a code comparison, not a deployment verification. Snapshot reviewed on 2026-10-28:

- Development base: `dev-text-mining` at `c6099953`.
- Service-main base: `main-text-mining` at `742e6317`.
- Comparison direction: development → service-main. These references can advance; repeat the comparison after the maintainer's local merge.

## Differences that affect documentation

| Area | Development snapshot | Service-main snapshot | Documentation action after merge |
| --- | --- | --- | --- |
| Legacy bulk UI | `GET /bulk-upload` and `interface/bulk_upload/` present | Route and three static UI files absent | Describe it as development-only; do not advertise it as available on service-main |
| AICCRA interface | Static UI uses the development backend destination | Uses a different environment destination | Verify generated links and target API without copying development settings |
| Bulk frontend S3 prefix | `star/text-mining/files/test/bulk_upload/` | `star/text-mining/files/prod/bulk_upload/` | Preserve the target environment and document the actual prefix |
| Bulk result links | Test STAR result host in `useBulkUploadApi.ts` | Production STAR host | Check hardcoded links as well as environment variables |
| Analytics | Development interaction-service URL | Different interaction-service URL | Preserve the service-main destination unless changing it is part of the request |
| Swagger server order | Test/local listed before production | Production listed first | Server lists are metadata, not proof of deployed availability |
| Alternate modules | Supabase mining/vectorization and older CLARISA connection modules present | Those modules absent | Mark alternate paths as development-only; do not recommend missing imports |
| Dynamo internal docs | Four documents under `app/utils/dynamo/docs/` | Those documents absent | Keep main documentation self-contained or link to files actually present |
| Product-specific docs | Four STAR/AICCRA overview/design documents absent | Those documents present under `docs/` | Preserve main-only documentation and review it against active implementation |
| Project metadata | `name = text-mining-service` | `name = mining-microservice` | Use service-directory names for navigation; verify package commands in target branch |
| Dependency lockfile | Development `uv.lock` | Different lockfile | Do not assume identical resolved environments |

Main-only product documents in this snapshot:

- `docs/AICCRA_TEXT_MINING_DOCUMENTATION.md`
- `docs/AICCRA_Text_Mining_SDD.md`
- `docs/STAR_Text_Mining_Product_Overview.md`
- `docs/STAR_Text_Mining_SDD.md`

The main-only documents above are listed as paths, not links, because they are absent from this development tree. The new overview/API/design guides cover the shared active workflows without depending on those files.

## Workflows and configuration

Development has a backend workflow targeting pushes to `dev-text-mining`. It also contains an older backend workflow targeting `dev-lambda`. The reviewed service-main backend workflow targets `main-text-mining` on pushes and pull requests and lacks the development-specific backend workflow file.

Separate Bulk Upload frontend workflows target `dev-text-mining` and `main-text-mining` on pushes. Check the workflow contents in the branch being pushed. Documentation-only updates are not excluded by the reviewed triggers.

`AUTH_TOKEN_STAR` appears in development configuration but is absent from service-main configuration. Active STAR mining takes its token from the request; do not treat this development configuration entry as a universal authentication mechanism.

The complete repository diff also includes changes outside Text Mining. This guide does not authorize synchronizing those services. Inspect the full merge diff and keep service-main's existing unrelated changes intact.

## Review after the local merge

1. Verify the current branch and working tree, then inspect all incoming commits and changed files.
2. Compare the updated service-main with the development branch: file presence, route declarations, static interfaces, manifests/lockfile, and environment-dependent destinations.
3. Confirm the four mining workflows still have their expected HTTP and MCP entry points. Verify helper routes and UI availability separately.
4. Adapt `README.md`, `AGENTS.md`, frontend documentation, and any affected API/design guide to the actual service-main tree. Do not restore a deliberately removed interface merely to satisfy a documentation link.
5. Check documentation links and examples. Distinguish code comparison, offline tests, and live checks in the handoff.
6. Leave the push and pipeline timing to the maintainer's instructions. Continue through `staging` and `main` after the service-main step is complete.
