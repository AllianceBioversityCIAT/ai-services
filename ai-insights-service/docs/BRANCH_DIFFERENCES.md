# AI Insights: branch comparison and integration review

Reviewed on 2026-10-28 before documentation changes:

| Reference | Commit |
| --- | --- |
| `origin/dev-ai-insights` | `590dcc7d` |
| `origin/main-ai-insights` | `6d204599` |

The two reviewed trees have identical content. The service-main commit is a merge of the development line. No development-only interface, missing test file, route difference, or hardcoded destination difference was found between these snapshots.

This compares repository contents, not deployment configuration. Environment values, secret contents, S3 prompt/cache objects, image versions, IAM access, and running pipelines were not compared. Identical source does not imply identical saved prompts or generated overviews.

## Documentation scope

The root service README was empty. The backend referenced a local README from project metadata but that file was absent. This update supplies both, adds product/API/architecture guides and a service agent guide, and copies the shared monorepo agent guide from the current staging branch without merging other services.

The implementation has project-overview generation/retrieval/deletion operations and a Prompt Manager. It has no frontend application or checked-in automated test suite. Static API summaries retain some older document-count prose; the current guides follow the implemented zero-to-three/zero-to-two behavior.

## Review after the local service-main integration

1. Refresh and compare the development and service-main references. Check content and patch equivalence rather than assuming different commit IDs imply missing work.
2. Verify all five business routes and the health/schema routes, required configuration, prompt registry/defaults, and storage helpers.
3. Confirm Docker still installs `backend/requirements.txt` and uses `main.handler`; compare manifests and lockfile if they changed.
4. Check for branch-specific interfaces, file exclusions, destination literals, or new docs before adapting the service-main README/agent guide. Do not invent differences merely because another service has them.
5. Preserve target-environment settings. Runtime prompt configuration and project cache belong to their configured S3 locations and are not synchronized by a Git merge.
6. Verify docs, examples, and relevant checks, then leave push/pipeline timing to the maintainer. Accumulate completed service-main changes in `staging` for the agreed consolidated PR to `main`.

## Jenkins filters

The reviewed workflows target pushes to `dev-ai-insights` and `main-ai-insights`, calling `ai-insights-dev` and `ai-insights-main`, respectively. Both also expose manual dispatch. Pull-request triggers and path exclusions are not defined in these two workflow files.

Documentation-only pushes therefore match the branch triggers. The workflow files call Jenkins; they do not contain the deployment job implementation or prove pipeline results.
