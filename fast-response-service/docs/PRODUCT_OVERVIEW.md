# Fast Response Service workflows

Fast Response applies an instruction to text supplied by another application. It can support summarizing a fictional report excerpt, improving phrasing, translating a paragraph, or drafting a reply. These are caller-defined uses of one operation, not separate implemented task pipelines.

## Caller workflow

1. Send `prompt` and `input_text` to `POST /api/fast-response`.
2. The service combines them into one user message and invokes the configured Bedrock model.
3. Read the generated `output` from the JSON response, or handle validation/generation errors.

A successful response echoes the original inputs and labels the result `success`. It does not assess factual accuracy, enforce an instruction-specific output schema, or guarantee that output is complete when the model stops early. Applications remain responsible for their own use-specific review.

## Scope and integration

The service has no dedicated frontend, retrieval database, file ingestion, persistent conversation, streaming output, or asynchronous job lifecycle. Callers provide their text directly. There is no route-level token/API-key dependency or rate limiter in the reviewed code; confirm deployed access controls separately.

`GET /health` verifies process responsiveness without invoking the model. Real generation invokes AWS Bedrock and may incur charges. The service logs prompts and provider metadata; examples should contain fictional data.

Use the [README](../README.md) for local setup, [API guide](API_GUIDE.md) for body/error contracts, and [design](HIGH_LEVEL_DESIGN.md) for component responsibilities. Preserve the intentional development/service-main log-path difference described in the [branch guide](BRANCH_DIFFERENCES.md) during integration.
