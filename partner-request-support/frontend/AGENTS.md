# Partner Request Support frontend: agent guide

Read [service instructions](../AGENTS.md) and [frontend README](README.md). This is a Next.js 16 / React 19 browser app with static export, not a server-side API gateway.

- Preserve the current hooks/services/components structure. `app/page.tsx` composes the workflow; hooks own state; `app/services/partnerService.ts` calls the Python API.
- `NEXT_PUBLIC_API_URL` configures backend calls at build time. The login host in `authService.ts` and badge in `Header.tsx` are separate hardcoded branch differences; preserve production values during integration.
- `useAuth.ts` keeps token/user in React state. Do not infer backend access control from the login screen or add token persistence as an incidental refactor.
- Spreadsheet upload sends `create_requests=true`. API processing sends a null body so the backend selects ten oldest pending requests. Changes to these values affect external behavior.
- Keep types, request builders, hooks, components, and backend schemas consistent. See [API guide](../docs/API_GUIDE.md); body tokens are used by the backend for upstream CLARISA operations.
- UI quality labels belong to manual matching. Do not substitute automatic endpoint thresholds.
- Use `npm ci`, `npm run dev`, and `npm run lint` from this directory. Inspect existing dependencies before installing. A static build writes `out/`; do not deploy it or commit generated output as a documentation check.
- Do not exercise real upload/create, accept/reject, or cache-clear controls for routine checks. Stub API/auth responses for browser tests. Report lint/build limits and distinguish them from live integration validation.

The [refactoring note](docs/REFACTORING.md) is historical context; verify current files before following it.
