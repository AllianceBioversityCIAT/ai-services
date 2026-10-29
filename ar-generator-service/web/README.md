# AICCRA Report Generator Web UI

Static HTML/CSS/JavaScript interface for generating and reviewing mid-year/annual indicator narratives, grouped summary tables, and challenges/lessons reports. The API serves it from `/web`; this directory has no npm build or separate frontend server.

## Serve the production UI

The Lambda image copies this directory, and FastAPI serves it at /web. For optional local diagnostics from an ODBC-capable production checkout with requirements installed:

```bash
python dev_server.py --host 127.0.0.1 --reload
```

Open [the local page](http://localhost:8000/web). Static assets are mounted at `/static`; the HTML references `static/app.js`, so use the documented `/web` URL. This only serves the page locally; it does not switch the JavaScript API destination.

## Destinations and local testing

`app.js` currently has separate hardcoded constants:

| Constant | Current production checkout |
| --- | --- |
| `API_BASE_URL` | Production Lambda base `https://qg53uhgrn7bpofn5eawcuvl62y0akymf.lambda-url.us-east-1.on.aws` |
| `AI_FEEDBACK_URL` | `https://i8s5i8c21i.execute-api.us-east-1.amazonaws.com` |

There is **no automatic local/production URL detection**. The commented localhost assignment does not execute. For deliberate local UI testing, change the API constant to the intended local server and review analytics routing as a separate choice; changing backend `.env` values or the page's host does not change either constant. No JavaScript destinations are changed by this documentation task.

Development uses the same production API base but the separate clv3b6bv9d analytics host; preserve that intentional [branch difference](../docs/BRANCH_DIFFERENCES.md). This branch has no uv project/lockfile; pyodbc-free local UI/backend work belongs to dev-ar-generator. The maintainer uses local testing and a production Lambda, with no separate test Lambda assumed.

A generation action also attempts interaction tracking. Payloads can include URL-provided `user_email`/`user`, request parameters, generated output, response time, and success/error metadata. These values do not authenticate a backend request. Tracking failures are logged and handled without intentionally failing the report action. Use fictional data and inspect/stub both destinations for offline browser work.

## Workflows

1. Choose a narrative type, table group workflow, or challenges tab.
2. Select an indicator/year as required by the UI, then generate.
3. Review narrative/table content and source evidence before using it externally.
4. Download a narrative as DOCX or a table group as CSV for Excel compatibility.

The main report controls select mid-year or annual endpoints. Tables/challenges send a placeholder indicator because all routes share `ChatRequest`, even though those operations use the year rather than that indicator. UI requests send `insert_data:false`; there is no normal rebuild button here.

The visible year selectors offer 2025/2026; the API model accepts 2021–2026. Generated text is AI output, not a verified official report. An HTTP 200 response can carry an error status or error text; the current UI HTTP check alone does not establish a successful business result. See [API semantics](../docs/API_GUIDE.md#responses-and-failure-semantics).

## Downloads and external assets

| Output | Implementation |
| --- | --- |
| Narrative/challenges DOCX | Browser-side `html-docx-js`, including headings and presentation metadata |
| Group table download | CSV blob with `.csv` filename; not a native XLSX workbook |
| Display formatting | HTML/CSS and JavaScript helpers in this directory |

`index.html` loads Font Awesome, Google Fonts (Inter), and `html-docx-js` from external hosts. Serving the local page can fetch those assets; there is no bundled offline guarantee. Report/table data remains in browser globals for downloads, while interaction tracking can send selected data to its configured service.

The “Data updated on” badge calculates the previous Sunday using the browser clock. It is not an observed ingestion timestamp, a scheduler-status query, or proof that production data was refreshed.

## Files and styling

```text
web/
├── index.html   # Layout, controls, inline styles and external assets
├── app.js       # API/tracking calls, state, rendering and downloads
├── README.md    # Current UI setup and behavior
└── AGENTS.md    # Frontend continuation rules
```

The existing design uses Inter, blue/white layouts, CGIAR yellow accents, and responsive tabs/cards. Match its current CSS conventions when editing; there is no framework migration required to maintain it.

## Validation and troubleshooting

- Check `app.js` syntax with Node when available; a syntax check does not execute API calls or verify rendering.
- For browser tests, stub generation, analytics, and external assets as appropriate. Do not click production-backed controls just to validate docs.
- For connection errors, inspect the actual browser request URL, backend process, and CORS response before changing URLs blindly.
- For downloads, verify generated content exists and the external DOCX library loaded. Tables are CSV even though the UI refers to Excel.
- For unexpected results, inspect response `status` and `content` as well as HTTP status; backend details can be nested under `detail`.
- Static source edits are served directly, subject to browser caching. A deployed Lambda still requires its own packaging/release flow.

Use the [service README](../README.md), [API guide](../docs/API_GUIDE.md), and [web agent guide](AGENTS.md) for continuing work. Production links in source are configuration evidence, not a live availability check.
