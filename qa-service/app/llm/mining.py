import time
import json
import boto3
from app.utils.config.config_util import AWS
from app.utils.prompt.prompt import build_prompt
from app.utils.logger.logger_util import get_logger
from app.utils.s3.s3_util import read_document_from_s3
from app.utils.interactions.interaction_client import interaction_client


logger = get_logger()

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=AWS['aws_access_key'],
    aws_secret_access_key=AWS['aws_secret_key'],
    region_name='us-east-1'
)


def invoke_model(prompt, max_tokens=2000):
    try:
        logger.info("🚀 Invoking the model...")
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
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
            modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        return json.loads(response['body'].read())['content'][0]['text']

    except Exception as e:
        logger.error(f"❌ Error invoking the model: {str(e)}")
        raise


def is_valid_json(text):
    """Check if the text is a valid JSON string"""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def improve_prms_result_metadata(result_metadata: dict, user_id: str = None):
    start_time = time.time()

    try:
        result_type = result_metadata["response"].get("result_type_name", "").lower()
        result_level = result_metadata["response"].get("result_level_name", "").lower()

        logger.info(f"🔍 Processing PRMS document with result type: {result_type}, result level: {result_level}")
        
        prompt = build_prompt(result_type, result_level, result_metadata)
        logger.info(f"📝 Generated prompt for LLM:\n{prompt}")

        response_text = invoke_model(prompt)

        json_content = json.loads(response_text) if is_valid_json(response_text) else {"text": response_text}

        end_time = time.time()
        elapsed_time = end_time - start_time

        interaction_id = None
        if user_id:
            try:           
                ai_output = json.dumps(json_content, indent=2, ensure_ascii=False)
                user_input = f"PRMS Result Metadata Improvement Request:\nResult Type: {result_type}\nResult Level: {result_level}"
                
                tracking_context = {
                    "prompt_used": prompt[:500] + "..." if len(prompt) > 500 else prompt,
                    "prompt_full_length": len(prompt),
                    "model_used": "claude-4-sonnet"
                }
                
                interaction_response = interaction_client.track_interaction(
                    user_id=user_id,
                    user_input=user_input,
                    ai_output=ai_output,
                    service_name="qa-ai",
                    display_name="PRMS QA Service",
                    service_description="A service that provides QA capabilities for documents.",
                    context=tracking_context,
                    response_time_seconds=elapsed_time,
                    platform="PRMS"
                )

                if interaction_response:
                    interaction_id = interaction_response.get('interaction_id')
                    logger.info(f"📊 Interaction tracked with ID: {interaction_id}")
                else:
                    logger.warning("⚠️ Failed to track interaction with interaction service")

            except Exception as tracking_error:
                logger.error(f"❌ Error tracking interaction: {str(tracking_error)}")
        
        logger.info(f"✅ Successfully generated PRMS response:\n{json.dumps(json_content, indent=2, ensure_ascii=False)}")
        logger.info(f"⏱️ PRMS Response time: {elapsed_time:.2f} seconds")

        result = {
            "time_taken": f"{elapsed_time:.2f}",
            "json_content": json_content,
        }

        if interaction_id:
            result["interaction_id"] = interaction_id
        
        return result

    except Exception as e:
        logger.error(f"❌ PRMS Error: {str(e)}")
        raise