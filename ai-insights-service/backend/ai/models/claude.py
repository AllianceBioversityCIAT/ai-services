import boto3
import json
from botocore.config import Config
from utils.logger.logger_util import get_logger
from utils.config.config_util import AWS


logger = get_logger()

bedrock_config = Config(
    connect_timeout=60,
    read_timeout=300,
    retries={'max_attempts': 3, 'mode': 'adaptive'}
)

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=AWS['aws_access_key'],
    aws_secret_access_key=AWS['aws_secret_key'],
    region_name='us-east-1',
    config=bedrock_config
)


def invoke_model(prompt, max_tokens=15000):
    try:
        logger.info("🚀 Invoking the model...")
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": 0.1,
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
            # modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            modelId="us.anthropic.claude-sonnet-4-6",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        
        stop_reason = response_body.get('stop_reason', 'unknown')
        usage = response_body.get('usage', {})
        input_tokens = usage.get('input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)
        
        logger.info(f"✅ Model invoked successfully - Stop reason: {stop_reason}")
        logger.info(f"📊 Token usage - Input: {input_tokens}, Output: {output_tokens}")
        
        response_text = response_body['content'][0]['text']
        logger.info(f"📄 Model response (first 500 chars): {response_text[:500]}...")
        
        if stop_reason != 'end_turn':
            logger.warning(f"⚠️ Model stopped with reason: {stop_reason} (may indicate truncation or max_tokens reached)")
        
        return response_text

    except Exception as e:
        logger.error(f"❌ Error invoking the model: {str(e)}")
        raise