import boto3
from app.utils.prompts.kb_generation_prompt import DEFAULT_PROMPT
from app.utils.config.config_util import KNOWLEDGE_BASE_ID, OPENSEARCH, BR


model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
model_arn = f'arn:aws:bedrock:us-east-1:569113802249:inference-profile/{model_id}'


bedrock_agent_runtime = boto3.client(
    service_name='bedrock-agent-runtime',
    aws_access_key_id=OPENSEARCH['aws_access_key'],
    aws_secret_access_key=OPENSEARCH['aws_secret_key'],
    region_name=BR['region']
)


def query_knowledge_base(query, max_results=5):
    """
    Query the knowledge base and return generated text.
    
    :param query: The query string to search in the knowledge base.
    :param max_results: Maximum number of results to retrieve.
    :return: Generated text from the knowledge base.
    """
    response = bedrock_agent_runtime.retrieve_and_generate(
        input={
            'text': query
        },
        retrieveAndGenerateConfiguration={
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                'modelArn': model_arn, 
                'retrievalConfiguration': {
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results,
                        # 'overrideSearchType': 'HYBRID'|'SEMANTIC',
                    }
                },
                'generationConfiguration': {
                    'inferenceConfig': {
                        'textInferenceConfig': {
                            'maxTokens': 1000,
                            'temperature': 0.2,
                            'topP': 0.999
                        }
                    },
                    'promptTemplate': {
                        'textPromptTemplate': DEFAULT_PROMPT
                    }
                }
            }
        }
    )

    generated_text = response['output']['text']

    return generated_text