# Chatbot development and service-main

The maintained integration path is `dev-chatbot-service → main-chatbot-service → staging → main`. Prepare focused tasks from the development branch and let the maintainer handle release merges unless explicitly delegated.

This comparison was inspected on 2026-10-29 against `main-chatbot-service` at `e9cc2474`. It describes the development tree after the documentation commits were brought in, before the next service-main merge. Re-run it after integration; it is not a claim of deployment success or post-merge parity.

## Runtime differences to preserve or review

| Area | dev-chatbot-service | main-chatbot-service |
| --- | --- | --- |
| Dependencies | pyproject/uv.lock; comma-suffixed pip requirements including openai | No pyproject/uv.lock; newline-separated requirements used by Docker |
| Packaging | No Dockerfile; local Uvicorn launcher and Mangum handler | Lambda Python 3.13 Dockerfile installs requirements and copies `.env` plus full context; inspect packaging without exposing credentials |
| AWS agent/S3 clients | Explicit access/secret arguments from common AWS config | Standard SDK credential chain for these clients |
| Logs | Service-local `data/logs` | `/tmp/logs` |
| HTML chat | `https://lvurhov4wryn4pygqxf6tp54uq0jdpgs.lambda-url.us-east-1.on.aws/api/chat` | Same fixed Lambda URL |
| HTML interactions | `https://clv3b6bv9d.execute-api.us-east-1.amazonaws.com` | `https://i8s5i8c21i.execute-api.us-east-1.amazonaws.com` |
| HTML labels/errors | Phase label and detailed nested/flat HTTP error handling | Same label and handling |
| Auxiliary tools | Streamlit, SQL extraction, five conversion scripts, OpenAI experiment and direct KB/LLM/OpenSearch modules | Several auxiliary/local files absent |

Both active chat paths use Bedrock Agents. Neither implements an agent data reload for `insert_data=true`; route flags/timings do not establish freshness. Opening the development HTML page locally still calls the fixed Lambda URL, not the local backend. Local API examples remain useful for testing Uvicorn independently.

## Complete service file inventory

Direction: `git diff --name-status main-chatbot-service HEAD -- chatbot-service`, run from the repository root on the development branch after bringing in documentation. `A` means present only in development, `D` present only in service-main, and `M` modified. Documentation edits and later merges can change this inventory.

| Status | Service-relative path |
| --- | --- |
| M | `.env.example` |
| A | `AGENTS.md` |
| D | `Dockerfile` |
| M | `README.md` |
| M | `TECHNICAL_DOCUMENTATION.md` |
| M | `app/llm/agents.py` |
| A | `app/llm/invoke_llm.py` |
| A | `app/llm/knowledge_base.py` |
| A | `app/llm/vectorize_os.py` |
| A | `app/utils/conversion/jsonl_to_json_contributions.py` |
| A | `app/utils/conversion/jsonl_to_json_deliverables.py` |
| A | `app/utils/conversion/jsonl_to_json_innovations.py` |
| A | `app/utils/conversion/jsonl_to_json_oicrs.py` |
| A | `app/utils/conversion/jsonl_to_json_questions.py` |
| M | `app/utils/logger/logger_util.py` |
| A | `app/utils/prompts/chatbot_prompt_full.py` |
| M | `app/utils/s3/upload_file_to_s3.py` |
| A | `chatbot.py` |
| A | `db_conn/sql_connection.py` |
| A | `docs/API.md` |
| A | `docs/BRANCH_DIFFERENCES.md` |
| M | `docs/HIGH_LEVEL_SOFTWARE_DESIGN.md` |
| M | `docs/PRODUCT_OVERVIEW.md` |
| A | `interface/AGENTS.md` |
| A | `interface/README.md` |
| M | `interface/chatbot_interface.html` |
| A | `openai_chatbot.py` |
| A | `pyproject.toml` |
| M | `requirements.txt` |
| A | `uv.lock` |

## After the local merge

Compare the entire resulting service tree with development, including missing interfaces, auxiliary files, dependency declarations and conflict resolutions. Adapt main's README and agent guides to the files actually retained, runtime credentials, log paths, UI destinations and packaging. Preserve intentional production choices instead of forcing exact equality.

The development workflow snapshot has no Chatbot-specific workflow. Main's `.github/workflows/jenkins-trigger-chatbot-service-prod.yml` runs on push/PR to main-chatbot-service and manual dispatch, invoking the chatbot-service Jenkins job. Its QA-oriented display name is misleading. Review current event filters again before pushing. Local documentation checks do not establish pipeline completion or deployment success.
