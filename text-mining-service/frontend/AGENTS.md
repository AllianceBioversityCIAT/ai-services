# AGENTS.md — Bulk Upload frontend

Nested agent guide for the Next.js app under `text-mining-service/frontend`. For service-wide backend/MCP context, see the parent [`../AGENTS.md`](../AGENTS.md). The closest `AGENTS.md` wins for files in this directory.

Package name: `text-mining-bulk-upload-frontend` (`package.json`).

---

## Project overview

Next.js 15 + React 19 UI for **STAR Capacity Development bulk upload**. Users upload/select Excel sheets, review LLM-extracted CapDev records, track complete/failed status in DynamoDB (via the mining API), and submit approved rows to STAR.

Deployment target: AWS via **SST** (`sst.aws.Nextjs`) and **OpenNext**. Same-origin `/api/*` BFF routes proxy to the Python mining service.

Legacy static bulk-upload UI still exists at `../interface/bulk_upload/` (served by FastAPI). Prefer this Next.js app for new Bulk Upload work unless the task explicitly targets the legacy interface.

---

## Dev environment tips

- Always iterate with **`npm run dev`** (or `npm run sst:dev` when exercising SST). Hot reload depends on the Next.js `.next` development cache.
- **Do not run `npm run build` or `npm run build:open-next` inside an interactive agent session** unless the user explicitly asks. Production builds rewrite `.next` / OpenNext assets and break HMR.
- If the andevelopment server looks inconsistent after dependency or config changes, restart `npm run dev` rather than running a production build.
- After adding/updating dependencies, update `package-lock.json` and restart the dev server.
- Env vars for local work typically include:
  - `NEXT_PUBLIC_MINING_API_BASE_URL` — FastAPI mining base URL
  - `NEXT_PUBLIC_STAR_API_BASE_URL`
  - `NEXT_PUBLIC_MANAGEMENT_API_BASE_URL`
  - `NEXT_PUBLIC_CLARISA_API_BASE_URL`
  - Server-only: `MINING_API_BASE_URL`, `BULK_UPLOAD_API_KEY`, `MANAGEMENT_API_BASE_URL` (see `sst.config.ts` and `app/api/*`)

---

## Useful commands

| Command | Purpose |
|---|---|
| `npm install` | Install dependencies |
| `npm run dev` | Next.js dev server with HMR |
| `npm run lint` | ESLint |
| `npm run start` | Serve a previously built app |
| `npm run sst:dev` / `sst:deploy` / `sst:remove` | SST lifecycle |
| `npm run build` / `build:open-next` | Production / OpenNext — **not for agent iteration** |

---

## Codebase map

```
frontend/
├── app/
│   ├── page.tsx                 # Entry → BulkUploadModule
│   ├── preview/                 # Preview route
│   └── api/
│       ├── bulk-upload/         # BFF → POST /star/mining-bulk-upload/capdev
│       ├── validate-token/      # Token validation proxy
│       └── languages/           # Languages helper route
├── components/BulkUpload/
│   ├── BulkUploadModule.tsx     # Wizard orchestration
│   ├── components/              # Steps, tables, cells, badges
│   ├── hooks/                   # API, Dynamo, filters, pagination, navigation guard
│   ├── utils/                   # Excel/CSV, formatters, completeness
│   ├── constants.ts             # URLs, field lists, maps
│   └── types.ts
├── styles/bulk-upload.css
├── sst.config.ts
├── open-next.config.ts
└── next.config.ts               # Server mode; no basePath (Lambda Function URL root)
```

---

## Code style & conventions

- Prefer TypeScript (`.tsx` / `.ts`) for new UI and utilities.
- Keep Bulk Upload domain logic under `components/BulkUpload/` (hooks/utils/components) rather than growing `app/page.tsx`.
- Reuse patterns in existing hooks (`useBulkUploadApi`, `useDynamoDB`, `useTableFilters`, `useNavigationGuard`).
- Field allowlists and STAR submission constants live in `constants.ts` — update there when extraction/submit contracts change.
- BFF routes must send `X-API-Key` to the mining API when required; do not expose `BULK_UPLOAD_API_KEY` to client bundles (`NEXT_PUBLIC_*` only for public config).
- Do not introduce a `basePath` / `assetPrefix` unless deployment docs change — static assets are resolved for OpenNext/S3 as documented in `next.config.ts`.

---

## Testing instructions

- Run `npm run lint` after non-trivial TS/React changes.
- Manually verify the wizard flow against a running mining API (`../` → `uv run python -m app.mcp.client`).
- If you change the BFF contract, confirm `app/api/bulk-upload/route.ts` still posts multipart form data to `/star/mining-bulk-upload/capdev`.
- Fix type/lint errors you introduce before finishing.

---

## Security considerations

- Never commit `.env` / SST secrets or put API keys in `NEXT_PUBLIC_*` variables.
- Treat mining API responses as untrusted input when rendering tables/cells.
- Preserve navigation-guard behavior for unsaved edits when changing step transitions.

---

## PR / change guidelines

- Scope: `[bulk-upload-frontend]` or match repo style `feat(bulk-upload): …`.
- Always run `npm run lint` before considering frontend work done.
- Coordinate API field/status changes with `../app/mcp/client.py` Dynamo endpoints and CapDev mining prompt/pipeline when needed.
