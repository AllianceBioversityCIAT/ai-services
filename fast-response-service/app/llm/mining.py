import json
import boto3
from app.utils.config.config_util import BR
from app.utils.logger.logger_util import get_logger
from botocore.exceptions import NoCredentialsError, ClientError, BotoCoreError

logger = get_logger()


def get_bedrock_client():
    """Initialize Bedrock client with proper error handling."""
    try:
        logger.info("🔧 Initializing Bedrock client...")
        
        # Validate credentials
        if not BR.get('aws_access_key') or not BR.get('aws_secret_key'):
            raise ValueError("AWS credentials not found in environment variables")
        
        if not BR['aws_access_key'].startswith('AKIA'):
            raise ValueError("Invalid AWS access key format")
        
        # Create client
        client = boto3.client(
            service_name='bedrock-runtime',
            aws_access_key_id=BR['aws_access_key'],
            aws_secret_access_key=BR['aws_secret_key'],
            region_name=BR['aws_region']
        )
        
        logger.info("✅ Bedrock client initialized successfully")
        return client
        
    except ValueError as ve:
        logger.error(f"❌ Configuration error: {str(ve)}")
        raise
    except NoCredentialsError:
        logger.error("❌ AWS credentials not found or invalid")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to initialize Bedrock client: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        raise

# Initialize client globally (will raise exception if configuration is wrong)
try:
    bedrock_runtime = get_bedrock_client()
except Exception as e:
    logger.error(f"❌ Failed to initialize Bedrock client on startup: {str(e)}")
    bedrock_runtime = None


def invoke_model(prompt):
    try:
        if bedrock_runtime is None:
            raise RuntimeError("Bedrock client not initialized. Check AWS configuration.")
        
        logger.info("🚀 Invoking the model...")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        
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
        
        response_body = json.loads(response['body'].read())
        logger.info("✅ Model invocation successful")
        
        return response_body['content'][0]['text']

    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"❌ AWS Client Error: {error_code} - {str(e)}")
        if error_code == 'UnauthorizedOperation':
            raise RuntimeError("AWS credentials invalid or insufficient permissions")
        elif error_code == 'ValidationException':
            raise RuntimeError("Invalid model ID or request format")
        else:
            raise RuntimeError(f"AWS service error: {error_code}")
    except BotoCoreError as e:
        logger.error(f"❌ Boto3 Core Error: {str(e)}")
        raise RuntimeError("AWS service connection error")
    except Exception as e:
        logger.error(f"❌ Error invoking the model: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        raise


def return_response(prompt: str, text: str) -> str:
    try:
        logger.info(f"Processing request - Prompt: '{prompt[:50]}...', Text length: {len(text)}")
        
        if not prompt or not text:
            raise ValueError("Both prompt and text are required")
        
        if not prompt.strip() or not text.strip():
            raise ValueError("Prompt and text cannot be empty")
        
        full_prompt = f"{prompt}: {text}"
        response = invoke_model(full_prompt)
        
        logger.info("✅ Response generated successfully")
        return response
        
    except ValueError as ve:
        logger.error(f"❌ Validation error in return_response: {str(ve)}")
        raise
    except RuntimeError as re:
        logger.error(f"❌ Runtime error in return_response: {str(re)}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in return_response: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        raise