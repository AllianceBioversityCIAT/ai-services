# Chatbot browser interface

A single static HTML/CSS/JavaScript page, served by FastAPI at `/chatbot-ui` or `/static/chatbot_interface.html`. No Node package manager or frontend build is defined. Start the API from the service directory using the [service quick start](../README.md).

## Fixed destinations on main-chatbot-service

| Constant | Current value | Purpose |
| --- | --- | --- |
| `CHATBOT_API_URL` | `https://lvurhov4wryn4pygqxf6tp54uq0jdpgs.lambda-url.us-east-1.on.aws/api/chat` | Buffered HTTP chat on Lambda |
| `AI_FEEDBACK_URL` | `https://i8s5i8c21i.execute-api.us-east-1.amazonaws.com` | External `/api/interactions` tracking/feedback |

These JavaScript constants are not read from Python `.env`. Serving the page at localhost does not rewrite either destination: chat and interaction calls still go to remote services. To test the local backend without changing the page, use the curl/Python examples in the service README. A local browser-to-local-backend setup would require explicitly editing `CHATBOT_API_URL`; that is a separate code/configuration change. Preserve these production destinations when integrating documentation.

## Flow and state

The page reads `user_email` from URL parameters or prompts for email, derives memory ID from the part before `@`, and generates a session UUID. These values are not authentication. Messages and filters are managed in JavaScript state; Export Chat downloads a `.txt` copy of local messages. A new session clears local history, resets filters and changes the session ID; it does not delete AWS memory.

Chat sends message, phase, indicator, section, session_id, memory_id and `insert_data=false`. The visible Phase label maps to the `phase` field and `All phases` sentinel. A complete JSON answer is displayed after the API finishes collecting agent chunks. The page records interactions and later feedback through separate calls to the interaction service.

## Maintaining the page

Keep request fields aligned with the [API contract](../docs/API.md). The page reads nested `detail.details` as well as flat error fields and has dedicated timeout/connection/server messages. Keep this handling aligned with the API error envelope; the API can return either error shape depending on the handler. Check exact sentinels, year-dependent indicator choices, new-session behavior and tracking independently. Never infer live availability from a fixed URL or static health response.

For offline validation, extract the inline JavaScript and run a syntax check without executing it. Use mocked fetch responses for UI behavior checks. Real browser chat/tracking calls have external effects.
