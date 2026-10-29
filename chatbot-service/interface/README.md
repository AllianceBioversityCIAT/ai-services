# Chatbot browser interface

A single static HTML/CSS/JavaScript page, served by FastAPI at `/chatbot-ui` or `/static/chatbot_interface.html`. No Node package manager or frontend build is defined. Start the API from the service directory using the [service quick start](../README.md).

## Fixed destinations on dev-chatbot

| Constant | Current value | Purpose |
| --- | --- | --- |
| `CHATBOT_API_URL` | `http://localhost:8000/api/chat` | Buffered HTTP chat |
| `AI_FEEDBACK_URL` | `https://clv3b6bv9d.execute-api.us-east-1.amazonaws.com` | External `/api/interactions` tracking/feedback |

These JavaScript constants are not read from Python `.env`. Serving on another host/port does not rewrite the chat URL. Local UI use can still send content to the remote interaction service. Production has different fixed destinations; preserve intentional values when promoting.

## Flow and state

The page reads `user_email` from URL parameters or prompts for email, derives memory ID from the part before `@`, and generates a session UUID. These values are not authentication. Messages and filters are managed in JavaScript state. A new session clears local history, resets filters and changes the session ID; it does not delete AWS memory.

Chat sends message, phase, indicator, section, session_id, memory_id and `insert_data=false`. The visible Cycle label still maps to the `phase` field and `All phases` sentinel. A complete JSON answer is displayed after the API finishes collecting agent chunks. The page records interactions and later feedback through separate calls to the interaction service.

## Maintaining the page

Keep request fields aligned with the [API contract](../docs/API.md). Review error handling against the nested FastAPI `detail` envelope; this dev page has less detailed error parsing than service-main. Check exact sentinels, year-dependent indicator choices, new-session behavior and tracking independently. Never infer live availability from a fixed URL or static health response.

For offline validation, extract the inline JavaScript and run a syntax check without executing it. Use mocked fetch responses for UI behavior checks. Real browser chat/tracking calls have external effects.
