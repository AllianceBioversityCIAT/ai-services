import boto3
import os
import json
from app.utils.prompt.prompt_prms_support import DEFAULT_CHATBOT_PRMS_SUPPORT
from app.llm.setup_supabase import setup_supabase
from app.llm.generate_embeddings import get_text_embedding
from dotenv import load_dotenv
from app.utils.logger.logger_util import get_logger

logger = get_logger()
load_dotenv()

bedrock_client = boto3.client(
    service_name="bedrock-runtime",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

def get_relevant_context(query, collection, top_k=3):
    """Seach relevant context usin RAG"""
    try:
        query_embedding = get_text_embedding(query)
        if not query_embedding:
            return []
        
        results = collection.query(
            data=query_embedding,
            limit=top_k,
            include_value=True,
            include_metadata=True
        )
        
        context = []
        for result in results:
            if result[2] and 'text' in result[2]:
                context.append(result[2]['text'])
        
        return context
    except Exception as e:
        logger.error(f"Error retrieving context: {str(e)}")
        return []

def chat_with_model(prompt, use_rag=False):
    try:
        # Calling the defined prompt
        system_prompt = DEFAULT_CHATBOT_PRMS_SUPPORT
        
        # Get relevant context
        context_parts = []
        if use_rag:
            collection = setup_supabase()
            if collection:
                context = get_relevant_context(prompt, collection)
                if context:
                    context_text = "\n".join(context)
                    context_parts = [
                        {"type": "text", "text": f"Relevant context from database:\n{context_text}"}
                    ]
        
        logger.info("Generating response with LLM...")
        
        # build message with context
        message_content = [
            {"type": "text", "text": f"System prompt: {system_prompt}"},
            *context_parts,
            {"type": "text", "text": f"User question: {prompt}"}
        ]

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": 0.1,
            "top_k": 250,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": message_content
                }
            ]
        }
        
        response = bedrock_client.invoke_model(
            modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        full_response = response_body['content'][0]['text']
        
        return full_response

    except Exception as e:
        logger.error(f"Error invoking the model: {str(e)}")
        raise