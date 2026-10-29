# Chatbot branch comparison

Baseline inspected on 2026-10-29 before documentation edits: local `dev-chatbot` at `5fe21e43` versus `origin/main-chatbot-service` at `e9cc2474`. This is an initial inventory, not a claim of post-merge parity. Re-run the comparison after the maintainer's local merge.

## Branch identity

`dev-chatbot` was explicitly selected for this work. It includes two existing local commits not yet in origin/dev-chatbot at inspection: `939f0942` (root ignored OpenNext artifacts) and `5fe21e43` (Text Mining frontend ignored build/local files). They are inherited user work and were not altered by this documentation task.

`dev-chatbot-service` exists at `209ba26f`; it is a distinct historical reference, not a synonym. Do not merge that line or all of main merely to obtain docs.

## Runtime differences to preserve/review

| Area | dev-chatbot | Inspected service-main |
| --- | --- | --- |
| Dependencies | pyproject/uv.lock; malformed comma-suffixed pip requirements | No pyproject/uv.lock; newline-separated requirements used by Docker |
| Packaging | No Dockerfile; local launcher and Mangum handler | Lambda Python 3.13 Dockerfile, installs requirements, copies `.env` and full context; review packaging without exposing credentials |
| AWS agent/S3 clients | Explicit access/secret arguments from common AWS config | Standard SDK credential chain for these clients |
| Logs | Service-local `data/logs` | `/tmp/logs` |
| HTML chat | `http://localhost:8000/api/chat` | `https://lvurhov4wryn4pygqxf6tp54uq0jdpgs.lambda-url.us-east-1.on.aws/api/chat` |
| HTML interactions | `https://clv3b6bv9d.execute-api.us-east-1.amazonaws.com` | `https://i8s5i8c21i.execute-api.us-east-1.amazonaws.com` |
| HTML labels/errors | Cycle labels, simpler errors | Phase labels, more detailed HTTP error handling |
| Local tools | Streamlit, SQL extraction, OpenAI experiment, conversion and direct KB/LLM/OpenSearch modules | Several local/auxiliary files absent |
| Existing docs | Older README, no detailed guides before this task | Existing technical, architecture and product guides; reconcile with actual code |

Main's older technical guides cover useful topics but are not proof that SQL/OpenSearch run during each request. Both inspected active agent paths use Bedrock Agents and do not execute the commented reload block.

## Complete initial service file inventory

Direction: `git diff --name-status origin/main-chatbot-service dev-chatbot -- chatbot-service`. `A` means present only in dev, `D` present only in main, `M` modified. Documentation work itself will change this inventory.

| Status | Service-relative path |
| --- | --- |
| M | `.env.example` |
| D | `Dockerfile` |
| D | `TECHNICAL_DOCUMENTATION.md` |
| M | `app/llm/agents.py` |
| A | `app/llm/invoke_llm.py` |
| A | `app/llm/knowledge_base.py` |
| A | `app/llm/vectorize_os.py` |
| M | `app/utils/logger/logger_util.py` |
| A | `app/utils/prompts/chatbot_prompt_full.py` |
| M | `app/utils/s3/upload_file_to_s3.py` |
| A | `chatbot.py` |
| A | `db_conn/sql_connection.py` |
| D | `docs/HIGH_LEVEL_SOFTWARE_DESIGN.md` |
| D | `docs/PRODUCT_OVERVIEW.md` |
| M | `interface/chatbot_interface.html` |
| A | `jsonl_to_json.py` |
| A | `openai_chatbot.py` |
| A | `pyproject.toml` |
| M | `requirements.txt` |
| A | `uv.lock` |

## After the local merge

Compare the full resulting service tree with development, including files added/removed during conflict resolution. Check actual dependency installation, client credentials, log directories, UI destinations and routes; then adapt main's README and agent guides. Keep production choices where intentional instead of forcing exact equality.

Dev's workflow snapshot has no Chatbot-specific workflow. Main's `.github/workflows/jenkins-trigger-chatbot-service-prod.yml` runs on push/PR to main-chatbot-service and manual dispatch, invoking the chatbot-service Jenkins job. Its QA-oriented display name is misleading. Review current filters again before pushing; local documentation checks do not establish deployment success.
