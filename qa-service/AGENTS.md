# QA Service: agent guide

This guide applies to `qa-service/`. Read the root agent guide when present and the [service README](README.md). This is one FastAPI application containing two distinct services/workflows: **AI Review** and **Quality Assessment**. Preserve their separate request contracts and processing paths.

## Branch and scope

Prepare QA changes from `dev-qa`, normally in a focused task branch. The integration path is `dev-qa` → `main-qa` → `staging` → `main`. The maintainer performs development-to-service-main merges unless explicitly delegated.

Both workflows share the QA branches and deployment package; they do not have separate branch pairs. A change to one workflow should not change the other's behavior unless requested. Before an authorized merge, review pending code and configuration differences as well as documentation.

## Where to start

| Concern | AI Review | Quality Assessment |
| --- | --- | --- |
| HTTP endpoint | `POST /api/prms-qa` | `POST /prms/quality-assessment` |
| Request / response | `PrmsRequest`, `PrmsResponse` | `QualityAssessmentRequest`, `QualityAssessmentResponse` |
| Orchestration | `app/llm/mining.py` | `app/llm/assessment.py` |
| Model invocation | `invoke_model_async()` in `mining.py` | `app/llm/bedrock_tools.py` |
| Prompts | `app/utils/prompt/main_prompt.py`, `impact_area_prompt.py` | `app/utils/prompt/assessment/` |
| Output validation | `app/llm/schemas.py` | API models, criteria catalog, finding assembly, suggestion validation |
| Main outcome | Rewritten metadata and impact-area feedback | Traffic lights, scores, issues, affected fields, evidence verdicts, coverage |

Shared entry points and utilities:

- `app/api/main.py`: FastAPI application, health and documentation routes.
- `app/api/routes.py`: both POST routes, CLARISA validation, HTTP errors, notifications.
- `app/api/models.py`: both workflows' API models.
- `app/web_scraping/`: extraction and evidence-context formatting.
- `app/utils/interactions/`, `notification/`, `logger/`, `config/`: integrations and runtime configuration.
- `api_server.py`: local Uvicorn launcher. `main.py`: Lambda `handler` through Mangum.

## Setup and local execution

Run from `qa-service/`, using Python 3.13:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
python api_server.py --reload
```

Complete the [README configuration steps](README.md#local-setup) before starting the server. `CLARISA_VALIDATE_URL` is required at import/startup even for AI Review. Use the boto3 credential chain for AWS access. Leave `SLACK_WEBHOOK_URL` unset when notifications are unnecessary.

Both Bedrock clients currently specify model `us.anthropic.claude-sonnet-4-6` and region `us-east-1` in code. `AWS_REGION` alone does not change those clients. `IS_PROD` labels notifications; it does not switch model, region, or analytics URL.

The Dockerfile installs `requirements.txt` and Chromium and starts the Lambda handler. Do not treat this image as a Uvicorn container listening on port 8000.

## AI Review constraints

- `result_metadata` is an open dictionary in the envelope, but `mining.py` directly accesses result type, result level, and five impact-area score keys. Preserve those requirements in examples.
- Innovation Development returns rewritten title, description, short name, and impact-area feedback. Knowledge Product runs impact-area review without title/description rewriting. Other types run the metadata and impact-area prompts.
- The route currently has no active CLARISA authentication dependency. Do not describe it as protected by that dependency or silently change its authentication during unrelated work.
- Readiness-level and use-level prompt modules exist, but their extra calls are commented out. Do not describe them as active processing steps.

## Quality Assessment constraints

- The route validates `X-API-Key` through CLARISA for `AI Traffic Light - PRMS`. Preserve this dependency during unrelated changes.
- Read `app/utils/assessment/contract_validation.py` and `vocabularies.py` when changing input fields. Type-specific form labels must match exactly; supported types differ from AI Review.
- Keep `impact_areas` at the top level, alongside `sections`. Contract version defaults to `0.2`; the current validator does not enforce the version string itself.
- Review criteria selection, deterministic rules, aggregation, scoring, and `payload_binding.py` together when changing findings. Prompts alone do not define assessment behavior.
- Core flags produce red; non-core flags alone produce amber; evaluated findings with no flags produce green. Scores use red 0–49, amber 50–99, and green 100; unevaluated scores can be null.
- Quality and execution coverage are separate. Preserve `status`, `degraded_reason`, and coverage counters; do not turn skipped criteria into passes or treat green as proof of a complete review.
- Keep affected Reporting Tool input names in `fields`. General Information can offer validated replacement text only when amber/red; suggestions may be absent or null.
- Preserve omission of `type_specific` from responses for Other Output and Other Outcome.
- Preserve HTTP failure semantics: both assessment model calls failing produces HTTP 503; unexpected processing failures produce HTTP 500. The schema's `unavailable` enum does not mean these paths return HTTP 200.

## Evidence, integrations, and timing

AI Review calls `enhance_prms_context()` with a default five-URL limit. Quality Assessment calls `extract_evidence_content()` directly with concurrency and per-URL/batch budgets. Do not apply one flow's limits to the other by assumption.

Extraction content limits are characters, not tokens. Preserve input order and completed results when a batch times out. Private evidence or items with no link are not fetched by assessment. A public `prms_repository` item with a link can be fetched.

An extraction failure does not by itself prove poor result quality. Retain grey/unevaluated outcomes and distinguish retrieval failures from deterministic evidence findings. Internal processing budgets are not guaranteed HTTP deadlines.

Interaction tracking is attempted only with `user_id`. Its configured URL may differ between `dev-qa` and `main-qa`; do not overwrite an intentional environment difference while moving documentation. Application logs go to `/tmp/logs/app.log` and the console and may contain metadata and extracted content.

## Validation

Run relevant existing checks from `qa-service/` with dependencies installed:

```bash
python tests/test_assessment_rules.py
python tests/test_assessment_e2e.py
```

The rules script covers deterministic behavior. The second script uses stubbed Bedrock and scraping for assessment scenarios, but imports initialize AWS clients and routes; local credentials/configuration may still be required. Neither script proves deployed model quality or external-source availability.

Do not include `tests/stress_test.py` in routine checks. It sends 100 concurrent requests to a hardcoded remote URL. Run it only as part of an explicitly requested live load test after checking its destination and input data.

For documentation-only changes, check Markdown links, request examples against the models and contract validator, and shell example syntax. Do not invoke Bedrock, send notifications, or create analytics records merely to validate prose.

## Documentation and completion

- [README](README.md): overview, setup, operations, and branch path.
- [Product overview](docs/PRODUCT_OVERVIEW.md): user purpose and capabilities of both workflows.
- [API guide](docs/API_GUIDE.md): contracts, errors, examples, and interpretation of results.
- [High-level design](docs/HIGH_LEVEL_DESIGN.md): components, execution flows, and limits.
- `docs/examples/`: fictional request payloads; the two example JSON files have explicit ignore-rule exceptions.

Update the relevant documents when behavior changes. Preserve the distinction between code inspection, stubbed checks, and live deployment verification. Report changed scope, checks and limitations, current branch, and commit/push/merge status.

QA GitHub workflows trigger Jenkins on pushes and pull requests targeting `dev-qa` and `main-qa`, including documentation-only changes. Check actual workflow filters and job targets rather than relying on their display names.
