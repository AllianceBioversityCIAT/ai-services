import json
import boto3
from app.utils.config.config_util import BR
from app.utils.logger.logger_util import get_logger

logger = get_logger()

if not BR.get('aws_access_key'):
    raise ValueError("AWS_ACCESS_KEY_ID_BR environment variable is required. Please configure it in Lambda environment variables.")
if not BR.get('aws_secret_key'):
    raise ValueError("AWS_SECRET_ACCESS_KEY_BR environment variable is required. Please configure it in Lambda environment variables.")


bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=BR['aws_access_key'],
    aws_secret_access_key=BR['aws_secret_key'],
    region_name=BR.get('region', 'us-east-1')
)


def get_bedrock_embeddings(texts):
    embeddings = []
    for text in texts:
        try:
            response = bedrock_runtime.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                body=json.dumps({"inputText": text}),
                contentType="application/json",
                accept="application/json"
            )
            result = json.loads(response["body"].read())
            embeddings.append(result["embedding"])
        except Exception as e:
            logger.error(f"❌ Error generating embedding for text: {e}")
            embeddings.append([])
    return embeddings


def invoke_model(prompt):
    try:
        logger.info("✍️  Generating report with LLM...")
        logger.info("🚀 Invoking the model...")
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 8000,
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
        response_stream = bedrock_runtime.invoke_model_with_response_stream(
            modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )

        full_response = ""
        for event in response_stream["body"]:
            chunk = event.get("chunk")
            if chunk and "bytes" in chunk:
                bytes_data = chunk["bytes"]
                parsed = json.loads(bytes_data.decode("utf-8"))
                part = parsed.get("delta", {}).get("text", "")
                if part:
                    full_response += part         

        return full_response     

    except Exception as e:
        logger.error(f"❌ Error invoking the model: {str(e)}")
        raise