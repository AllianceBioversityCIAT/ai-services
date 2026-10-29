# AICCRA static web UI: agent guide

Read [service instructions](../AGENTS.md) and the [web README](README.md). This describes main-ar-generator's production static HTML/CSS/JavaScript served by FastAPI, with no npm project or build pipeline in this directory.

- Preserve existing tabs, controls, inline styles, and helper patterns. `index.html` owns layout/styles and external assets; `app.js` owns requests, state, rendering, tracking, and downloads.
- `API_BASE_URL` is hardcoded to the production Lambda even in the development checkout. The commented localhost assignment does not execute. Page host and backend `.env` do not reconfigure it.
- `AI_FEEDBACK_URL` is independent: this branch uses https://i8s5i8c21i.execute-api.us-east-1.amazonaws.com, while development uses the clv3b6bv9d host. Preserve intentional environment destinations during integration. Tracking can include user URL parameters, generated output, timing, and request metadata; it is not authentication.
- Use `/web` locally. The HTML references relative `static/app.js`; do not assume every trailing-slash URL serves the same asset paths without checking redirects.
- Requests use insert_data:false. Tables/challenges send a placeholder indicator to satisfy the shared request schema; do not introduce a destructive rebuild action as a cosmetic edit.
- Public API responses are complete JSON, not streamed tokens. Check backend status/content semantics, not only HTTP status, when changing result handling.
- DOCX generation uses the external html-docx-js library. Table exports are CSV with .csv filenames despite Excel wording in the UI.
- The last-update badge calculates the prior Sunday in the browser; it does not query successful ingestion. Do not present it as a live status signal in docs.
- External fonts/icons/DOCX scripts can be fetched on page load. For offline browser validation, stub external assets, report calls, and analytics; avoid clicking a production-backed generation control.
- Syntax checks do not validate rendering or real downloads. Use fictional data for manual/mock tests, keep real generated reports out of commits, and distinguish local source edits from deployed Lambda releases.
