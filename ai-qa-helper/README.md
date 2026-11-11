# AI QA Helper

AI suggestion worker for the OneCGIAR QA platform (Jira P2-3918, epic P2-3902).

For each AI-input field of a result snapshot, this service proposes a value with a supporting quote from the evidence. The QA platform shows the assessor a green, amber or red signal and a short explanation. The AI never validates a field or writes a comment.

| Item | Value |
| --- | --- |
| Development branch | `dev-ai-qa-helper` |
| Runtime | AWS Lambda, Python 3.13 (arm64), triggered by SQS |
| Model | Claude Haiku 5.5 through Claude in Amazon Bedrock (Mantle), `anthropic.claude-haiku-5-5` |
| Infrastructure | Terraform in [`infra/`](infra/) (prefix `qa-ai-`, region us-east-1) |
| Package manager | uv (`pyproject.toml`, `uv.lock`); `requirements.txt` is exported from the lock for the Lambda build |
| Claude client | `anthropic.lib.bedrock.AnthropicBedrockMantle` from `anthropic[bedrock]` (pinned) |

## Where the code lives

| Repository | Contents |
| --- | --- |
| This folder | Worker, prompts, eval, Terraform, smoke test and the **canonical contract**: Pydantic models in [`app/contract/`](app/contract/), published as JSON Schema in [`contract/schema/`](contract/schema/) with example items in [`contract/examples/`](contract/examples/) |
| `onecgiar_qa` | API endpoints, role filtering, usage table, sync hook and the review chip. It keeps a copy of the contract that is checked by a contract test. |

## Flow

1. **Enqueue.** The QA API sync enqueues one SQS message per (snapshot, AI-input field) after it stores the snapshots.
2. **Extract evidence.** The worker extracts the evidence. If no evidence is readable, it does not call the model and stores `unavailable` with the reason.
3. **Call the model.** The worker calls Claude with structured output: value, quote and explanation.
4. **Compute the signal in code.** The signal is computed deterministically ([`app/signal/`](app/signal/)):

   | Signal | When |
   | --- | --- |
   | Green | Same value as reported, with a verified quote and complete evidence |
   | Amber | Off by one, unverified quote, partial evidence, or no reported value |
   | Red | Off by two or more, with a verified quote |

5. **Store and track.** The worker stores the suggestion in the `cgiar-qa-{env}` DynamoDB table and updates the run counters. A run is complete only when every expected job is produced or marked unavailable, with none failed.

## Development

Run from `ai-qa-helper/` with Python 3.13 and [uv](https://docs.astral.sh/uv/):

```bash
uv sync                                   # creates .venv from uv.lock
uv run pytest                             # unit tests; no AWS or model calls
uv run python -m scripts.export_schemas   # regenerate contract/ after changing app/contract/
scripts/build.sh                          # dist/ai-qa-helper-lambda.zip (Linux arm64 wheels)
```

The tests use `FakeLlmProvider` and a fake Anthropic client ([`tests/fakes.py`](tests/fakes.py)). The [`BedrockMantleProvider`](app/llm/bedrock_mantle.py) calls a paid model and is exercised only through the smoke test and the eval, each run with prior approval.

`pyproject.toml` sets `[tool.uv] exclude-newer` so the lock only resolves releases at least a week old. Move the date forward deliberately when upgrading.

| Path | Contents |
| --- | --- |
| `app/contract/` | Job message, API view and event models; DynamoDB items and key builders |
| `app/signal/` | Deterministic signal and quote verification |
| `app/llm/` | `LlmProvider` port, Bedrock Mantle adapter, v1/v2 output schemas |
| `app/evidence/` | Evidence extraction copied from `qa-service` without the browser paths, plus the SSRF guard and the OCR fallback |
| `app/handlers/` | Lambda handlers: `smoke.handler`, `worker.handler` |
| `app/worker/` | One job (`process.py`), snapshot reader, DynamoDB store |
| `app/prompts/`, `prompts/` | Prompt loader and request builder; prompt texts and manifest |
| `app/utils/` | Logger and configuration, same interface as `qa-service` |
| `eval/` | v1 vs v2 comparison on the 2025 sample; data in `eval/.data/` (gitignored) |
| `contract/` | Generated JSON Schema and example items for the `onecgiar_qa` contract test |

## Contract with onecgiar_qa

The QA API reads the suggestions with ElectroDB, and this worker writes them with boto3, so both sides must produce the same items. This was checked against ElectroDB 3.9.3, the version in `onecgiar_qa/server`:

- With `template` and `casing: 'none'`, keys are written exactly as the template. The default casing lowercases them.
- ElectroDB adds `__edb_e__` (entity) and `__edb_v__` (version) to each item, and its queries silently drop items without them. The worker writes both as constants.
- The example items in `contract/examples/` are returned by an ElectroDB 3.9.3 query that uses the definitions below.

Proposed entity definitions for `onecgiar_qa` (same pattern as its `resultSnapshot` entity):

| Entity | Model | pk | sk |
| --- | --- | --- | --- |
| `aiSuggestion` | `{entity: 'aiSuggestion', version: '1', service: 'qa'}` | `RESULT#${resultCode}` | `AI#${snapKey}#${fieldKey}#${promptVersion}` |
| `aiRun` | `{entity: 'aiRun', version: '1', service: 'qa'}` | `AIRUN#${runId}` | `RUN` |

Every key uses `field: 'pk'` / `'sk'` and `casing: 'none'`. `fieldKey` and `promptVersion` never contain `#`, so a `begins_with` query on `AI#${snapKey}#` returns exactly one snapshot's suggestions. The `onecgiar_qa` contract test should load `contract/examples/*.json` through its entities and validate its API responses against `contract/schema/ai-suggestion-view.schema.json`.

## Evidence extraction

`app/evidence/scraper.py` is a copy of `qa-service/app/web_scraping/` (branch `dev-qa`, commit `4959345`), not a shared package: each service is promoted through its own branches, and this copy has to differ anyway. The module docstring lists what was kept and what changed. The main differences:

- **No Playwright.** The worker is a zip Lambda and Chromium does not fit. Web and DOI landing pages are fetched over plain HTTP, so pages that need JavaScript end up `unreadable`. The v1 vs v2 comparison measures how often this happens.
- **Guarded HTTP.** Each redirect hop passes an SSRF check (public addresses, default ports, http/https only). Downloads are capped at 25 MB and 45 s, and nothing is written to disk.
- **OCR fallback.** A PDF without a text layer is sent to the model as a `document` block when it is 10 MB or smaller.
- **Private links.** 401/403 responses and Microsoft or Google login pages count as private.

The extractor gives each link one of five statuses: `text`, `pdf_ocr`, `private`, `unreadable` or `error`. Transient errors are not cached, so a retry fetches them again. When no link is readable, the job stores `unavailable` without calling the model: the reason is `private_link` if any link was private, otherwise `no_readable_evidence`.

## Worker

Handler: `app.handlers.worker.handler` (SQS, batch size 1, partial batch failures). Each job is
one (snapshot, field, promptVersion):

1. **Already stored?** The job is skipped, with no model call. A duplicate SQS delivery never counts twice.
2. **Criteria.** A field without a prompt in that version is stored as `no_criteria_for_field`.
3. **Snapshot.** `RESULT#<code>` / `SNAP#<snapKey>`, written by `onecgiar_qa`. The worker reads the title, the description, the reported value and the evidence links ([`app/worker/snapshot.py`](app/worker/snapshot.py)). It uses the links flagged for the field (`evidence.items[].<area>_related`); if none are flagged, it uses all of the result's links, up to 5.
4. **Evidence.** Nothing readable means `unavailable` with its reason, and no model call.
5. **Model.** A truncated answer is retried once with a higher cap. A refusal is stored as `model_declined`; invalid JSON or an out-of-range value as `invalid_output`.
6. **Signal and write.** One DynamoDB transaction puts the suggestion, conditional on the key, and adds 1 to the `AiRun` counter.

Transient errors (throttling, 5xx, timeouts, a snapshot not found yet) are retried by SQS. On the
last delivery (`MAX_RECEIVE_COUNT`, the same value as the queue's redrive) the job is stored as
`unavailable/failed`, so every expected job is accounted for. A `failed` item is the only one that
can be replaced: re-enqueuing the job overwrites it and moves its count from `failed`. Only
messages that cannot be parsed or recorded reach the DLQ.

**To confirm with Reporting:** how a `single_select` value appears in `values` (bare id or
`{"value": id}`; both are accepted), and the id → level maps in `LEVEL_MAPS`. `tag_levels` is
assumed to be 1/2/3 → 0/1/2. `readiness_levels` and `innovation_use_levels` stay empty until
confirmed, so the reported IRL/IUL counts as "not reported" (amber) rather than a guess.

## Infrastructure

See [`infra/`](infra/):

- `infra/envs/test` and `infra/envs/prod` hold the environment roots.
- `infra/modules/ai-worker` holds the shared module.
- State is local and gitignored; the S3 backend is prepared but commented out.
- The Lambda execution role is created by the infrastructure team and passed in as `execution_role_arn` in `terraform.tfvars`, which is gitignored.

The maintainer runs `terraform apply`.

Both Lambda functions (`qa-ai-smoke-{env}` with handler `app.handlers.smoke.handler`, and `qa-ai-worker-{env}` with `app.handlers.worker.handler`) use the zip from `scripts/build.sh`, runtime `python3.13`, architecture `arm64`.

```bash
scripts/build.sh                               # from ai-qa-helper/
cd infra/envs/test
cp terraform.tfvars.example terraform.tfvars   # fill in the role ARN
terraform init && terraform plan
```

## December 2026 batch

| Item | Value |
| --- | --- |
| Size | About 100 results from 2026, 3 assessors |
| Dates | TEST ready by 20 Nov; operational testing with the QA coordinator from 23 Nov; PROD on 1 Dec; assessment 1–5 Dec |
| Fields | The five Impact Areas, Innovation Readiness Level and Innovation Use Level (to be confirmed by the PO) |
| Out of scope until after the batch | Incremental re-runs, quota tuning and the metrics job |

## Prompts

The scoring criteria in the previous AI QA Helper's prompts (scales, definitions and per-field rules) were validated with the QA coordinator. They do not change for the December batch.

| Version | What it is |
| --- | --- |
| `v1-1.0.0` | The previous helper's seven AI-input prompts (01–05, 07, 08), byte for byte, sent the way its code sent them (`Context: <JSON>\n\n<prompt>`, empty placeholders included). Only the mechanics differ: no temperature, structured output with its own keys plus `Evidence Quote`. This is the baseline. |
| `v2-1.0.0` | The same criteria in a common frame: the rubric is a cached system prompt, the evidence is tagged by source, the quote must be verbatim, and the explanation has at most 50 words. The input and output instructions and the contradictions of the old prompts are removed. |

Neither version sends the reported value to the model. Every prompt file is pinned by sha256 in [`prompts/manifest.json`](prompts/manifest.json), so a released version cannot change. Details of the differences: [`prompts/README.md`](prompts/README.md).

Both versions run on the same 2025 sample. The December batch uses whichever version scores better against the final QA values. Changes to the criteria themselves are proposed after the batch, based on its data, and validated with the QA coordinator before use (February 2027 cycle).

## Status

| Done | Pending |
| --- | --- |
| Python port: contract (Pydantic + JSON Schema), evidence extraction (from `qa-service`, no browser), signal mapping, quote verification, LLM provider port and Bedrock Mantle adapter, prompts v1 and v2 loaded by version, worker handler (idempotent writes, partial batch failures, run counters), v1 vs v2 comparison tooling ([`eval/`](eval/README.md): sample, estimate, budget-capped run, report), smoke handler, Lambda build (unit-tested, no live call yet) | Smoke test (waiting for the execution role ARN), control-list id maps (Reporting), running the v1 vs v2 comparison (waiting for the 2025 export and Bedrock access for the deployer) |
