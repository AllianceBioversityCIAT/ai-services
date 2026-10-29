# Static chatbot interface: agent guide

Read [service instructions](../AGENTS.md) and the [interface guide](README.md). This directory contains a single HTML/CSS/JavaScript application, with no frontend manifest or build process.

- Preserve branch-specific `CHATBOT_API_URL` and `AI_FEEDBACK_URL` unless changing destinations is explicitly requested. Python environment variables do not override them.
- Coordinate chat fields and nested HTTP error handling with [API models/contract](../docs/API.md). Keep the Phase label aligned with the `phase` payload name and exact sentinel strings. The fixed chat endpoint is Lambda, including when the page is served locally.
- Feedback uses a separate external `/api/interactions` service; do not invent a local feedback route.
- Memory identity is an unverified email local part. New session changes the session UUID and local state, not provider memory retention.
- Keep user-entered and generated content handling in mind when editing rendering. Do not change access or content-processing behavior incidentally in docs work.
- Syntax-check extracted inline JavaScript without executing fetch. For interaction tests, mock chat and feedback separately; avoid sending real reporting content.
