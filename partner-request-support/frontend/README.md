# Partner Request Support frontend

Next.js 16.1.6 / React 19.2.3 client application for reviewing institution matches from spreadsheets or pending CLARISA requests. It calls the Python backend directly and is configured for static export to S3/CloudFront.

## Local setup

Use a Node.js version compatible with the pinned Next.js 16 package; check its engine requirement in `package-lock.json`. Run from `partner-request-support/frontend/`:

```bash
npm ci
npm run dev
```

Create `.env.local` with the intended backend URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

The URL is public browser configuration. Login in this service-main branch is separate and uses the hardcoded production base `https://api.clarisa.cgiar.org/auth` in `app/services/authService.ts`; the header displays Production Environment. The development branch uses the CLARISA test host. Running this branch locally retains its production login destination. Changing `NEXT_PUBLIC_API_URL` alone does not change the login destination or the hardcoded environment badge.

## User and API flow

1. Sign in through the CLARISA auth endpoint. The token and user information are stored in React state; this does not add a backend-wide authentication dependency.
2. Upload the Excel template or fetch pending CLARISA requests.
3. Run matching, inspect candidate scores, and optionally request manual web research.
4. Accept/reject selected existing requests through the backend using the user's token and identifier.

Spreadsheet upload explicitly sends `create_requests=true`, so it can create requests in CLARISA before matching. It is not a local preview-only operation. Pending API processing sends no selected-ID body; the backend chooses the ten oldest requests and returns batch-size metadata.

The UI represents the manual-review matching flow. The separate `/api/auto-partner-request` backend endpoint has different decision tiers and is not a replacement for the existing frontend review labels.

## Code map

| Location under `app/` | Purpose |
| --- | --- |
| `page.tsx` | Workflow composition |
| `hooks/useAuth.ts` | Login/logout state |
| `hooks/useApiSync.ts` | Pending queue and backend batch size |
| `hooks/usePartnerProcessing.ts` | Processing state/results |
| `services/authService.ts` | CLARISA login URL/payload and error messages |
| `services/partnerService.ts` | Backend calls, multipart upload, responses, web research, cache clear |
| `components/PartnerTable.tsx`, `PartnerRow.tsx` | Candidate review/actions |
| `types/` | API/result/auth types |
| `utils/qualityHelpers.tsx` | Manual quality presentation |

## Validation and hosting

```bash
npm run lint
```

Lint does not validate live logins, CLARISA changes, model quality, or infrastructure. Use deliberate development fixtures and external mocks for offline checks. Do not invoke real accept/reject, cache-clear, or upload/create actions merely to validate documentation.

`next.config.ts` uses `output: export`. A production build writes static output under `out/`; there is no Next.js BFF/SSR server in the deployed static app. `template.yaml` defines S3/CloudFront hosting; publishing assets changes that environment and is separate from local development.

See the [frontend agent guide](AGENTS.md) before editing code, the [service API guide](../docs/API_GUIDE.md) for actual body/side-effect contracts, and [branch differences](../docs/BRANCH_DIFFERENCES.md) before service-main integration.
