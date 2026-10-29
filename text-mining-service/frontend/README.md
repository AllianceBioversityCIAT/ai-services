# STAR Bulk Upload frontend

The `main-text-mining` branch contains this Next.js 16 / React 19 application for extracting Capacity Development candidates from spreadsheets, reviewing/editing them, and submitting records to STAR. It is a separate app from the Python Text Mining backend.

See the [service README](../README.md) for extraction workflows and [frontend AGENTS.md](AGENTS.md) for implementation conventions.

## Run locally

Use Node.js 22 (see `.nvmrc` and `package.json#engines`) and the checked-in npm lockfile. Keep Jenkins on a patched Node 22 release. Run from `text-mining-service/frontend/`:

```bash
nvm use
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

This branch uses `star/text-mining/files/prod/bulk_upload/` in `constants.ts` and the production STAR host for generated result links in `useBulkUploadApi.ts`. Development uses a test prefix and test result host. Changing environment variables alone does not update these literals; do not use production destinations for a local live test by assumption.

Before promoting frontend changes, compare `components/BulkUpload/constants.ts`, `hooks/useBulkUploadApi.ts`, deployment environment values, and the [service branch comparison](../docs/BRANCH_DIFFERENCES.md). Preserve the target environment's destinations.

There is no `../interface/bulk_upload/` HTML interface or Python `/bulk-upload` page in this branch. Development retains that separate legacy interface. This Next.js app and the Python extraction endpoint remain present on service-main.

## Validation

```bash
npm run lint
npm run typecheck
```

Lint checks code style/static rules; it does not validate live extraction, STAR submissions, or Dynamo writes. For a deliberate live check, use development credentials and test data and exercise upload, review, draft/approved submission, and re-upload/status restoration.

Use the development server while iterating. Production builds rewrite Next/OpenNext output and can disrupt a running development session; run them only when explicitly requested.

## Deployment and code map

SST configures `sst.aws.Nextjs` with OpenNext for AWS hosting. The package defines `sst:dev`, `sst:deploy`, `sst:remove`, `build`, and `build:open-next` scripts. Deployment/removal commands change AWS resources; they are not routine validation commands.

Start in `components/BulkUpload/BulkUploadModule.tsx` for orchestration, `hooks/` for API/status behavior, `constants.ts` for table fields/destinations, `app/api/` for BFF handlers, and `sst.config.ts` for deployment configuration. Follow [AGENTS.md](AGENTS.md) before editing frontend behavior.


## Node 22 / Next 16 deployment checks

The reviewed dependency set is Next.js 16.4.3, React/React DOM 19.3.1, and
OpenNext AWS 4.1.13. Next.js, its ESLint configuration, React, and OpenNext are
pinned; `package-lock.json` records the complete dependency selection. Run
`npm ci`, not an unversioned adapter downloaded with `npx`, in deployment jobs.

`npm run build:open-next` invokes the installed OpenNext CLI. OpenNext then runs
`npm run build` exactly once, using Next's Webpack builder explicitly. This keeps
the bundler choice stable across the Next 15 to 16 migration. The existing dummy
cache overrides and custom S3 asset resolver remain in use.

For Jenkins, use Node 22 and run these checks before packaging or deploying:

```bash
npm ci
npm run lint
npm run typecheck
npm run build:open-next
npm run test:open-next
```

`test:open-next` invokes the generated Lambda handler with fictional inputs and
local HTTP upstreams. It checks pages, a referenced static bundle, S3 binary GET/HEAD via a local endpoint, token validation,
multipart forwarding, upstream error status, and partner creation. It does not
contact AWS, Bedrock, STAR, or CLARISA.

The GitHub `Bulk Upload frontend checks` workflow runs the same checks without
AWS credentials or a deployment. It runs independently of the existing Jenkins
triggers; configure it as a required PR check in repository settings if desired.
The Jenkins pipeline definition is not tracked here, so infra must apply this
check sequence to the actual job. Neither path uses the unsupported-version flag.

Two deployment definitions exist; choose the one that owns the environment:

- CloudFormation/Function URL: the template under
  `infrastructure/cloudformation/bulk-upload-frontend-opennext.yaml` declares
  `nodejs22.x`. Continue packaging `.open-next/server-functions/default/` with
  `index.mjs` at the zip root and syncing `.open-next/assets/` under `_assets/`.
  Preserve the environment variables and permissions managed by infra.
- SST: `sst.config.ts` explicitly runs the locally installed adapter and sets
  the server and image optimizer to `nodejs22.x`. SST deployment has not been
  verified against AWS. Do not deploy SST over an environment owned by the
  CloudFormation pipeline merely to complete this migration.

Updating the Jenkins agent alone does not update a Lambda runtime. Before
promotion, infra must confirm the deployed runtime, handler, architecture, S3
prefix, environment variables, and the pipeline's actual adapter command.

After deployment to development, verify static JS/CSS/images, token validation,
Excel upload/extraction, editing, STAR submission, and status restoration using
test data. Live checks can invoke Bedrock and write STAR/DynamoDB data. Keep the
previous server artifact and matching assets available for rollback.

## Dependency maintenance

Dependency upgrades are managed manually. The Node 22 migration does not enable
scheduled dependency-update branches or pull requests. Propose additional package
upgrades only when requested, and validate them separately from this runtime update.

Update Next and `eslint-config-next` together, and React and React DOM together.
For each adapter or framework upgrade, repeat the Node 22 checks and the development
smoke test before promotion. Revisit Node's and Next's support windows regularly;
Node 22 is the current infrastructure requirement, not a permanent runtime choice.

References: [Next 16 migration](https://nextjs.org/docs/app/guides/upgrading/version-16),
[Next support policy](https://nextjs.org/support-policy),
[OpenNext releases](https://github.com/opennextjs/opennextjs-aws/releases).


### Remaining migration follow-ups

- Next 16's new `react-hooks/set-state-in-effect` diagnostics are warnings for
  existing Bulk Upload components. Rules of hooks, immutability, and manual
  memoization checks still fail lint. An existing declaration-order issue in
  `ResultsTable` was corrected without changing its effect behavior. Resolve
  the remaining warnings in focused UI changes before making this rule blocking.
- The dependency audit after compatible fixes still reports 12 affected packages
  (10 high, 2 moderate, no critical). This is not a clean security audit. Remaining
  chains include SST 3 / OpenControl / AWS SDK v2, OpenNext's minifier / glob, and
  `xlsx` 0.18.5. Runtime exposure must be assessed separately from build-tool
  findings. `xlsx` has no npm-provided fix; select a maintained spreadsheet
  version/source or replacement and test Excel import/export separately. SST 4
  is another migration and has not been applied here. Do not use `npm audit fix
  --force` to fold those behavior changes into this upgrade.
- Jenkins job definition, live Lambda configuration, IAM/S3 permissions, and the
  browser wizard against real development services remain external validation.
