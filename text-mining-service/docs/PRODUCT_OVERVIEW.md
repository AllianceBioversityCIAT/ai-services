# Text Mining: product overview

Text Mining turns documents, spreadsheets, and PRMS text/audio inputs into candidate research-result records. Four workflows share one backend deployment while retaining distinct prompts, contracts, and authentication. A Next.js application supports the STAR bulk-review and submission process.

This document describes the reviewed `main-text-mining` code. It does not certify deployed availability, extraction accuracy, or a measured time saving.

## Workflows and users

| Workflow | Intended user / purpose | Input | Output |
| --- | --- | --- | --- |
| STAR document mining | STAR reporting teams identifying results in a document | One S3 document or uploaded file | Candidate STAR results, validated/formatted with STAR-specific schemas |
| PRMS multisource extraction | PRMS bilateral reporting teams drafting MDS-shaped records | Existing S3 documents, inline text, audio keys, or a combination | Candidate results across six supported indicators, with PRMS-specific fields |
| AICCRA document mining | AICCRA teams extracting information from reports | One document and an optional custom prompt | Parsed model JSON, or a text fallback when JSON cannot be recovered |
| STAR Bulk CapDev | Teams processing spreadsheet rows in batches | Spreadsheet and optional already-submitted row IDs | Capacity Development candidates for review and submission through STAR |

PRMS supports Capacity Sharing for Development, Policy Change, Innovation Development, Innovation Use, Other Output, and Other Outcome. Knowledge Product is excluded from this extraction flow. These are six discriminator values, even though some earlier prose calls them five indicators.

PRMS extraction belongs to this service. AI Review and Quality Assessment are separate QA capabilities in `qa-service`; this backend does not implement their endpoints.

## Source processing and result review

STAR and AICCRA process one stored document; an HTTP upload first writes it to S3. Shared document readers handle PDF, DOCX, TXT, Excel, and PowerPoint. Spreadsheet rows are cleaned and treated as chunks. Extraction depends on readable content; there is no general OCR path documented here for scanned images.

PRMS accepts independent source groups. It extracts each source's text, runs bounded parallel model extraction per source, merges candidates, performs a final validation pass, maps reference fields, and applies result-specific schemas. A declared source that cannot be processed fails the request. Individual invalid candidates may instead be omitted from an otherwise successful response.

PRMS documents can supply candidate formal evidence. Free text and audio transcripts are contextual sources, not formal documentary evidence. Text-only input works without a request bucket. Audio processing must be explicitly configured.

The returned candidates require human review. Mining does not itself approve research results or establish that every source claim is factually correct. A schema-valid response is not an accuracy guarantee.

## Bulk Upload frontend

The Next.js frontend lets users select/upload a spreadsheet, run extraction, review and edit candidates, and submit records through STAR. It validates a management token and checks allowed roles. Backend-for-frontend routes forward the mining API key from server configuration.

The review table includes primary levers/research areas and strategic objectives, alongside result, participant, geography, partner, and ownership information. Fields and submission rules are maintained in `frontend/components/BulkUpload/`.

DynamoDB records submitted/failed statuses and result links so previously handled rows can be recognized. This tracking is distinct from saving the result in STAR. The frontend's STAR submission calls and the backend's mining calls have separate responsibilities.

The legacy static bulk-upload UI and `/bulk-upload` route are absent from this branch and remain development-only; the Next.js frontend is present. Use the [branch comparison](BRANCH_DIFFERENCES.md) to distinguish interface availability from the extraction API.

## Access and dependencies

- STAR and Bulk CapDev: CLARISA API key plus STAR token validation; Bulk CapDev also checks roles 1, 9, or 10.
- PRMS: CLARISA API key; no STAR token or `environmentUrl` contract.
- AICCRA: optional token fields are accepted, but the current tool does not enforce token validation.
- Supporting services: S3, Bedrock, temporary LanceDB data, optional mapping/analytics/Slack, DynamoDB for bulk tracking, and Amazon Transcribe when PRMS audio is enabled.

Confirm environment access, endpoints, and credentials with the maintainer. A user-interface login does not establish authentication on every backend helper.

## Where to continue

Use the [README](../README.md) for setup, the [API guide](API_GUIDE.md) for the four endpoint contracts and response wrappers, the [PRMS guide](prms-integration-guide.md) for MDS integration, and the [high-level design](HIGH_LEVEL_DESIGN.md) for implementation flows.
