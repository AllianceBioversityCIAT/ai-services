# AICCRA Report Generator workflows

The service assists reporting officers, program/M&E teams, and reviewers preparing AICCRA indicator reports. It assembles structured targets/achievements and retrieved evidence into drafts that users review before official use. This guide describes main-ar-generator production assistance, not measured time savings or guaranteed reporting compliance.

## Inputs and report types

API callers supply an indicator, year, and optional rebuild flag. The browser provides report/year controls and uses the same JSON endpoints. The API accepts years 2021–2026 and a free-text indicator; actual data coverage must be checked separately.

| Report | Intended use |
| --- | --- |
| Mid-year narrative | Draft interim performance text from contribution totals and retrieved evidence |
| Annual narrative | Assemble annual summary, cluster narratives, and selected disaggregated target material |
| Indicator tables | Review target/achievement figures and generated group/cluster overviews |
| Challenges and lessons | Summarize structured cross-cluster challenge/learning rows |

Source categories include contributions, deliverables/DOIs, questions, OICRs, innovations, and challenges. This branch reads/transforms SQL Server/Fabric data and can create/alter views and export source data to S3. Development's prepared CSV/MySQL path is separate; switching this branch to CSV does not remove ODBC import requirements. The active semantic store is S3 Vectors, with separate structured retrieval and business filtering.

## User journey and outputs

A user selects a report type/year/indicator, generates, reviews content, and downloads a narrative as DOCX or a table group as CSV. The current static UI's API destination is production even when the page is served locally, so local testing requires deliberate endpoint review or API-only checks.

The date badge calculates a prior Sunday; it does not verify last refresh time. Generated content, success status, and returned quantitative text do not independently establish factual accuracy or official approval. The API can return error/no-data prose with HTTP 200 in some paths; see [failure semantics](API_GUIDE.md#responses-and-failure-semantics).

Browser analytics can send requester parameters, response data, and timing to an external feedback service. These fields do not authenticate the API. Confirm handling and intended destinations before using real reporting material in local/browser tests.

## Continuing and operating the service

Use the [README](../README.md) for startup and architecture, [technical guide](TECHNICAL_DOCUMENTATION.md) for CSV/config/operations, and [agent guide](../AGENTS.md) for implementation constraints.

The maintainer uses local development and a production Lambda rather than a separate test Lambda. The current production container dispatches HTTP and scheduled Lambda events; source exports, AR index refresh, and KB ingestion are supported operations with data effects. Development-specific dependencies, loaders, cron tools, and debug artifacts must not replace that ODBC/container/dispatcher behavior during integration. The [branch guide](BRANCH_DIFFERENCES.md) records that separation and the full initial inventory.

Index rebuilds can delete and recreate shared vector contents. Local CSV mode still calls cloud services; production source loading can create/alter views and export data. Offline schema/unit checks do not validate live permissions, data quality, model accuracy, installed schedules, or pipeline health.
