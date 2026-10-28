# STAR Bulk Upload frontend

Next.js 15 / React 19 application for extracting Capacity Development candidates from spreadsheets, reviewing/editing them, and submitting records to STAR. It is a separate app from the Python Text Mining backend.

See the [service README](../README.md) for extraction workflows and [frontend AGENTS.md](AGENTS.md) for implementation conventions.

## Run locally

Use Node.js 20+ and the checked-in npm lockfile. Run from `text-mining-service/frontend/`:

```bash
npm ci
npm run dev
```

Create `.env.local` with development URLs and server-side keys supplied by the team. Keep it out of version control. The Python backend is started separately from its service directory.

| Variable | Used for |
| --- | --- |
| `NEXT_PUBLIC_MINING_API_BASE_URL` | Browser-visible mining base URL; also the BFF fallback |
| `MINING_API_BASE_URL` | Optional server-only mining URL override in `/api/bulk-upload` |
| `BULK_UPLOAD_API_KEY` | Server-only CLARISA key forwarded to the bulk mining endpoint |
| `NEXT_PUBLIC_STAR_API_BASE_URL` | STAR result-submission API base |
| `NEXT_PUBLIC_MANAGEMENT_API_BASE_URL` | Management API base; also used to build extraction `environmentUrl` |
| `MANAGEMENT_API_BASE_URL` | Server-only token-validation base override |
| `NEXT_PUBLIC_CLARISA_API_BASE_URL` | Public catalog base and server fallback for partner requests |
| `CLARISA_API_BASE_URL` | Server-side partner API base override |
| `CLARISA_PARTNER_REQUEST_CREATE_URL` | Optional explicit partner-create endpoint |
| `CLARISA_VALIDATE_URL` | Server-side key-validation endpoint; helper can derive it from the CLARISA base |
| `CLARISA_API_KEY` | Server-only partner-request key |

`NEXT_PUBLIC_*` variables are visible to browser code; do not put secret keys in them. The SST configuration explicitly forwards its own environment list; it does not currently list `MINING_API_BASE_URL`, so the mining BFF normally uses its public-base fallback in that deployment configuration.

## User and API flow

1. Validate the management token through `/api/validate-token`; the handler checks validity and roles 1, 9, or 10.
2. Select/upload a spreadsheet, then request extraction through `/api/bulk-upload` → Python `/star/mining-bulk-upload/capdev`.
3. Review candidate rows, edit fields, and resolve catalog/staff/partner information where applicable.
4. Submit selected rows to the STAR formalization API and record completed/failed state through mining-service Dynamo routes.

Table configuration includes primary levers/research areas and strategic objectives. Completeness indicators, risk flags, draft/approved handling, and stored submission metadata are implemented under `components/BulkUpload/`; they are not a backend guarantee that every row was extracted correctly.

| Same-origin route | Responsibility |
| --- | --- |
| `POST /api/validate-token` | Call management `authorization/validate-token` and check allowed roles |
| `POST /api/bulk-upload` | Proxy multipart extraction and attach the server-configured `X-API-Key` |
| `POST /api/partner-request` | Validate server-side CLARISA access and create a partner request |

Other browser calls, including STAR submission and status/catalog requests, are defined in the frontend hooks and constants. A successful frontend login does not itself add authentication to every backend helper route.

## Branch-dependent destinations

The development constants use the test bulk-upload S3 prefix. The reviewed service-main uses the production prefix. Generated STAR result links also use different hardcoded hosts between branches; changing environment variables alone does not update those literals.

Before promoting frontend changes, compare `components/BulkUpload/constants.ts`, `hooks/useBulkUploadApi.ts`, deployment environment values, and the [service branch comparison](../docs/BRANCH_DIFFERENCES.md). Preserve the target environment's destinations.

The legacy HTML interface under `../interface/bulk_upload/` is separate from this Next.js app and exists only in the reviewed development snapshot. Its removal from service-main does not remove the Next.js app or the Python extraction endpoint.

## Validation

```bash
npm run lint
```

Lint checks code style/static rules; it does not validate live extraction, STAR submissions, or Dynamo writes. For a deliberate live check, use development credentials and test data and exercise upload, review, draft/approved submission, and re-upload/status restoration.

Use the development server while iterating. Production builds rewrite Next/OpenNext output and can disrupt a running development session; run them only when explicitly requested.

## Deployment and code map

SST configures `sst.aws.Nextjs` with OpenNext for AWS hosting. The package defines `sst:dev`, `sst:deploy`, `sst:remove`, `build`, and `build:open-next` scripts. Deployment/removal commands change AWS resources; they are not routine validation commands.

Start in `components/BulkUpload/BulkUploadModule.tsx` for orchestration, `hooks/` for API/status behavior, `constants.ts` for table fields/destinations, `app/api/` for BFF handlers, and `sst.config.ts` for deployment configuration. Follow [AGENTS.md](AGENTS.md) before editing frontend behavior.
