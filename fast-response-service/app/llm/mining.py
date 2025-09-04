import json
import boto3
from app.utils.config.config_util import BR
from app.utils.logger.logger_util import get_logger

logger = get_logger()

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
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
        return json.loads(response['body'].read())['content'][0]['text']

    except Exception as e:
        logger.error(f"❌ Error invoking the model: {str(e)}")
        raise


def return_response(prompt: str, text: str) -> str:
    try:
        full_prompt = f"{prompt}: {text}"
        response = invoke_model(full_prompt)
        #logger.info("Response generated successfully: ", response)
        return response
    except Exception as e:
        logger.error(f"❌ Error in return_response: {str(e)}")
        raise