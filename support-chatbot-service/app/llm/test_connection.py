import boto3
import os
from dotenv import load_dotenv

def test_bedrock_connection():
    load_dotenv()
    
    bedrock_client = boto3.client(
        service_name= 'bedrock',
        region_name=os.getenv('AWS_REGION'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        models = bedrock_client.list_foundation_models()
        if "amazon.titan-embed-text-v2:0" in [m["modelId"] for m in models["modelSummaries"]]:
            print("✅ Conexión con Bedrock establecida correctamente")
            return True
        else:
            print("Titan Embed Model no available")
            return False
    except Exception as e:
        print(f"❌ Error conectando a Bedrock: {str(e)}")
        return False

if __name__ == "__main__":
    test_bedrock_connection()