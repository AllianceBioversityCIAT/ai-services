# AICCRA chatbot product overview

The chatbot helps AICCRA reporting users explore indexed reporting records through natural-language questions. It offers a browser interface, Streamlit interface and HTTP API for another caller.

## User workflow

1. Open an interface and provide an email identifier, or supply session/memory IDs from an API caller.
2. Select a reporting cycle/phase, indicator and section to narrow retrieval.
3. Ask about progress, deliverables, innovations or outcome impact cases.
4. Review the answer against source evidence before reporting or external communication.
5. Provide feedback through the separate interaction service, or start a new local session.

Streamlit also exports the local conversation as text. Interface email entry personalizes identity; it does not verify email or authorize access.

## Data and limits

The UI includes AWPB, Progress and AR choices for 2021–2025 and year-dependent IPI/PDO indicator options. Data sections are Deliverables, Contributions (including questions), Innovations and OICRs. Actual coverage depends on external Knowledge Base ingestion and metadata, not UI options alone.

Generated answers may omit evidence or make mistakes. Model selection, memory retention, source freshness and ingestion schedules are external configuration. No measured latency, automatic refresh schedule or source-completeness guarantee is established here. The accepted reload flag does not execute a refresh in this code line.

New session clears local history and changes the session ID; it does not delete provider memory. Identifiers are caller-controlled and email local parts can collide. Review access controls and the handling of questions/answers in logs and remote tracking before using sensitive data.

Use the [README](../README.md) for setup, [API contract](API.md) for integration and [architecture](HIGH_LEVEL_SOFTWARE_DESIGN.md) for implementation boundaries.
