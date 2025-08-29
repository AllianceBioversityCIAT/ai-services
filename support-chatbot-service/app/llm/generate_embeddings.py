import boto3
import json
import os
from dotenv import load_dotenv
from app.utils.logger.logger_util import get_logger

logger = get_logger()

load_dotenv()

bedrock_client = boto3.client(
    service_name = 'bedrock-runtime',
    region_name=os.getenv('AWS_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

def get_text_embedding(text):
    print('entrando a get text embedding')
    try:
        request_body = json.dumps({
            "inputText": text,
            # "embeddingConfig": {"outputEmbeddingLength": 1024}
        })
                
        response = bedrock_client.invoke_model(
            body = request_body,
            modelId = "amazon.titan-embed-text-v2:0",
            accept = "application/json",
            contentType = "application/json"
        )
        response_body = json.loads(response["body"].read())
        # return response_body.get["embedding"]
        return response_body['embedding']
    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        return None
