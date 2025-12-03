import json
import boto3
from app.utils.config.config_util import BR
from app.utils.logger.logger_util import get_logger
from app.utils.prompts.prompt_1 import build_rfp_prompt

logger = get_logger()

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=BR['aws_access_key'],
    aws_secret_access_key=BR['aws_secret_key'],
    region_name='us-east-1'
)

bedrock_agent_runtime = boto3.client(
    service_name='bedrock-agent-runtime',
    aws_access_key_id=BR['aws_access_key'],
    aws_secret_access_key=BR['aws_secret_key'],
    region_name='us-east-1'
)

def invoke_model(prompt):
    try:
        logger.info("🚀 Invoking the model...")
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "temperature": 0.1,
            "top_k": 250,
            "top_p": 0.999,
            "stop_sequences": [],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{prompt}"}
                    ]
                }
            ]
        }
        response = bedrock_runtime.invoke_model(
            modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )

        logger.info("✅ Model invoked successfully.")

        return json.loads(response['body'].read())['content'][0]['text']

    except Exception as e:
        logger.error(f"❌ Error invoking the model: {str(e)}")
        raise


def return_response():
    try:
        prompt = "What is deep research by OpenAI?"
        response = invoke_model(prompt)
        logger.info(f"🔍 Claude Bedrock API response: {response}")

        return response
    except Exception as e:
        logger.error(f"❌ Error in return_response: {str(e)}")
        raise


def bedrock_agent():
    try:
        DEFAULT_RFP_PROMPT = build_rfp_prompt()
        response = bedrock_agent_runtime.retrieve_and_generate(
            input={
                'text': DEFAULT_RFP_PROMPT
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': 'GZXYCJHFSG',
                    'modelArn': 'arn:aws:bedrock:us-east-1:569113802249:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0',
                    'retrievalConfiguration': {
                        'vectorSearchConfiguration': {
                            'numberOfResults': 20
                        }
                    }
                }
            }
        )

        answer = response['output']['text']
        logger.info(f"🔍 Bedrock Agent RAG response: {answer}")

        return answer
    except Exception as e:
        logger.error(f"❌ Error in bedrock_agent: {str(e)}")
        raise


if __name__ == "__main__":
    bedrock_agent()