# PRMS QA Service: product overview

The service helps PRMS reporting teams improve result metadata and identify quality issues before submission. It provides two separate API workflows: AI Review for metadata improvement and a traffic-light quality assessment for W3/Bilateral results.

This overview describes backend capabilities implemented in this branch. It does not certify a deployment, frontend integration, or measured improvement in reporting outcomes.

## Users and purpose

Reporting officers and research teams need clear descriptions of research results, consistent use of institutional criteria, and supporting evidence. Validation teams need to understand what was checked and which inputs need attention.

The service returns suggestions and assessments to its caller. It does not save edits to PRMS, accept a suggestion on behalf of a user, or implement the Reporting Tool's submission workflow.

## Two workflows

| Workflow | Input | Output |
| --- | --- | --- |
| AI Review: `POST /api/prms-qa` | Existing PRMS result metadata, impact-area selections, optional evidence and user ID | Suggested metadata and impact-area feedback, processing time, optional evidence metadata and interaction ID |
| Quality assessment: `POST /prms/quality-assessment` | Structured W3/Bilateral result, form sections, evidence, optional impact areas and user ID | Overall and section verdicts, scores, issues, affected inputs, evidence verdicts, coverage, and optional replacement text |

AI Review generates a short name for Innovation Development results. Knowledge Products use the impact-area review without title or description rewriting. Other result types use the metadata and impact-area prompts.

The traffic-light assessment supports Policy Change, Innovation Use, Capacity Sharing for Development, Innovation Development, Other Output, and Other Outcome. Knowledge Product is not in that endpoint's current result-type catalog.

## Reading an assessment

| Verdict | Meaning |
| --- | --- |
| Red | At least one core criterion was flagged |
| Amber | A non-core criterion was flagged, with no core flags |
| Green | No evaluated criterion was flagged |
| Grey | The section or evidence item was not evaluated |

Verdicts describe quality findings. `status`, `degraded_reason`, and `coverage` describe execution and must also be read. A green verdict alone does not establish that every applicable check completed.

Scores are derived by the service: red maps to 0–49, amber to 50–99, and green to 100. A score is null when nothing was evaluated. It is not a probability or an independently validated measure of research impact.

Each section identifies issues and the corresponding Reporting Tool inputs in `fields`. General Information can also include a replacement title or description when its verdict is amber or red. Suggestions are optional, are validated before being returned, and do not alter the submitted data.

## Evidence and coverage

The shared scraper attempts to retrieve content from CGSpace, DOI pages, SharePoint/OneDrive links, general web pages, PDFs, and Excel files. Retrieval depends on source access and extractable content; support for a source does not guarantee every link will be readable.

For the assessment workflow, private evidence or items without a usable link are not scraped. Their individual verdict is grey. Retrieval failures are reported separately from quality findings. Some criteria cannot be verified without additional data sources and are left unverified rather than guessed.

An assessment may return HTTP 200 with partial coverage. Failures of both assessment model calls produce HTTP 503. Other startup, authentication, input, and processing errors also have explicit error responses; the caller must decide how these affect its own submission flow.

## Access and integrations

- The assessment endpoint validates `X-API-Key` with CLARISA for `AI Traffic Light - PRMS`.
- The AI Review route currently has no active application authentication dependency. Any infrastructure controls must be checked separately.
- Both workflows invoke Claude Sonnet 4.6 through AWS Bedrock in `us-east-1`.
- Providing `user_id` enables an attempt to record the interaction with the external analytics service.
- Slack notifications are attempted when a webhook is configured.

The code includes an AWS Lambda container and a local FastAPI server. Confirm deployed URLs, frontend behavior, credentials, and access with the environment owner.

## Expected value and validation limits

The intended benefits are less repetitive editing, more consistent review, and clearer feedback about evidence and missing information. This repository does not establish a measured time saving, rejection-rate reduction, or accuracy guarantee.

For integration examples, see the [API guide](API_GUIDE.md). For component flows and operational limits, see the [high-level design](HIGH_LEVEL_DESIGN.md). For setup, see the [service README](../README.md).
