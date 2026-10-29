# Chatbot development and service-main

The maintained integration path is `dev-chatbot-service → main-chatbot-service → staging → main`. Prepare development work from its development branch; service-main documentation must reflect the production tree that survives integration.

## Local merge review

Compared on 2026-10-29 after merge `eda96e5c`, with development at `b24399bc`. All development commits are included in the merge history, while 20 service paths differ in the resulting trees. These differences already existed on service-main; the merge did not reintroduce its absent local tools or replace its runtime settings.

The API, models, metadata filter builder, local launcher and Lambda handler match development. The resulting application code, HTML, Dockerfile and requirements also match `origin/main-chatbot-service` as inspected before push. Documentation required adaptation; runtime equality with development is neither assumed nor required.

## Runtime differences preserved

| Area | dev-chatbot-service | main-chatbot-service |
| --- | --- | --- |
| Dependencies | pyproject/uv.lock; comma-suffixed requirements | No pyproject/uv.lock; valid newline-separated requirements used by Docker |
| Packaging | No Dockerfile | Lambda Python 3.13 Dockerfile installs requirements and copies `.env` plus full context |
| AWS agent/S3 clients | Explicit access/secret arguments | Standard SDK credential chain |
| Logs | Service-local `data/logs` | `/tmp/logs` |
| HTML chat | Fixed Lambda URL | Same fixed Lambda URL |
| HTML interactions | `https://clv3b6bv9d.execute-api.us-east-1.amazonaws.com` | `https://i8s5i8c21i.execute-api.us-east-1.amazonaws.com` |
| HTML labels/errors | Phase and detailed nested/flat error parsing | Same label and handling |
| Local tools | Streamlit, SQL, five converters, OpenAI CLI, direct KB/LLM/OpenSearch modules and full chatbot prompt | These files are absent; retained S3 helpers/templates do not replace them |

Both active agent paths use Bedrock Agents and implement no reload for `insert_data=true`. Both HTML pages call the fixed Lambda chat URL even when served locally. Their interaction destinations differ intentionally. Keep packaging, credentials, logs and production destinations intact when adapting documentation.

## Complete initial tree comparison after merge

Direction: `git diff --name-status dev-chatbot-service HEAD -- chatbot-service`, run on service-main immediately after the local merge, before adapting documentation. `A` means main-only, `D` development-only, and `M` modified. Subsequent documentation edits add further differences; the following inventory records the 20 initial runtime/tooling differences.

| Status | Service-relative path |
| --- | --- |
| A | `Dockerfile` |
| M | `app/llm/agents.py` |
| D | `app/llm/invoke_llm.py` |
| D | `app/llm/knowledge_base.py` |
| D | `app/llm/vectorize_os.py` |
| D | `app/utils/conversion/jsonl_to_json_contributions.py` |
| D | `app/utils/conversion/jsonl_to_json_deliverables.py` |
| D | `app/utils/conversion/jsonl_to_json_innovations.py` |
| D | `app/utils/conversion/jsonl_to_json_oicrs.py` |
| D | `app/utils/conversion/jsonl_to_json_questions.py` |
| M | `app/utils/logger/logger_util.py` |
| D | `app/utils/prompts/chatbot_prompt_full.py` |
| M | `app/utils/s3/upload_file_to_s3.py` |
| D | `chatbot.py` |
| D | `db_conn/sql_connection.py` |
| M | `interface/chatbot_interface.html` |
| D | `openai_chatbot.py` |
| D | `pyproject.toml` |
| M | `requirements.txt` |
| D | `uv.lock` |

## Checks before promotion

Review the final documentation diff and complete repository integration scope. The merge also includes existing ignored-file commits outside Chatbot; do not treat all incoming commits as service documentation. Those inherited changes are left intact.

The workflow `.github/workflows/jenkins-trigger-chatbot-service-prod.yml` runs on push/PR to main-chatbot-service and manual dispatch, invoking the chatbot-service Jenkins job despite a misleading QA display name. Wait for the relevant pipeline before promoting to staging. Offline checks do not validate live AWS resources, feedback, image deployment or Jenkins.
