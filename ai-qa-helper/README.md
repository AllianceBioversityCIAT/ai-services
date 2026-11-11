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
| `app/handlers/` | Lambda handlers (`smoke.handler`; the worker handler is pending) |
| `app/utils/` | Logger and configuration, same interface as `qa-service` |
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
| `v1` | The previous helper's nine prompts, verbatim. This is the baseline. |
| `v2` | Our rewrite with the same criteria. It drops the gpt-5 framing and the hand-written JSON instructions, separates the instructions from the evidence, asks for a verbatim evidence quote, and uses structured output. |

Both versions run on the same 2025 sample. The December batch uses whichever version scores better against the final QA values. Changes to the criteria themselves are proposed after the batch, based on its data, and validated with the QA coordinator before use (February 2027 cycle).

## Status

| Done | Pending |
| --- | --- |
| Python port: contract (Pydantic + JSON Schema), signal mapping, quote verification, LLM provider port and Bedrock Mantle adapter, smoke handler, Lambda build (unit-tested, no live call yet) | Smoke test (waiting for the execution role ARN), evidence extraction (reusing `qa-service`), prompts v1 and v2, worker handler, v1 vs v2 comparison on a 2025 sample |
