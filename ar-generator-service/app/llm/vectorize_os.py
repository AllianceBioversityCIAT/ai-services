import json
import boto3
import numpy as np
import pandas as pd
from requests_aws4auth import AWS4Auth
from db_conn.mysql_connection import load_data
from app.utils.prompts.prompt import PROMPT
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import BR, OPENSEARCH
from opensearchpy import OpenSearch, RequestsHttpConnection


logger = get_logger()

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=BR['aws_access_key'],
    aws_secret_access_key=BR['aws_secret_key'],
    region_name=BR['region']
)

credentials = boto3.Session(
    aws_access_key_id=OPENSEARCH['aws_access_key'],
    aws_secret_access_key=OPENSEARCH['aws_secret_key'],
    region_name=BR['region']
).get_credentials()

region = BR['region']
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

opensearch = OpenSearch(
    hosts=[{'host': OPENSEARCH['host'], 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

INDEX_NAME = OPENSEARCH['index']


def get_bedrock_embeddings(texts):
    embeddings = []
    for text in texts:
        response = bedrock_runtime.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=json.dumps({"inputText": text}),
            contentType="application/json",
            accept="application/json"
        )
        result = json.loads(response["body"].read())
        embeddings.append(result["embedding"])
    return embeddings


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
        # response = bedrock_runtime.invoke_model(
        response_stream = bedrock_runtime.invoke_model_with_response_stream(
            modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        # return json.loads(response['body'].read())['content'][0]['text']
        full_response = ""
        for event in response_stream["body"]:
            chunk = event.get("chunk")
            if chunk and "bytes" in chunk:
                bytes_data = chunk["bytes"]
                parsed = json.loads(bytes_data.decode("utf-8"))
                part = parsed.get("delta", {}).get("text", "")
                print(part, end="", flush=True)
                full_response += part

        return full_response

    except Exception as e:
        logger.error(f"❌ Error invoking the model: {str(e)}")
        raise


def create_index_if_not_exists(dimension=1024):
    if not opensearch.indices.exists(INDEX_NAME):
        logger.info(f"📦 Creating OpenSearch index: {INDEX_NAME}")
        index_body = {
            "settings": {
                "index": {
                    "knn": True
                }
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "chunk": {"type": "object"},
                    "source_table": {"type": "keyword"},
                    "indicator_acronym": {"type": "keyword"}
                }
            }
        }
        opensearch.indices.create(index=INDEX_NAME, body=index_body)



def insert_into_opensearch(df: pd.DataFrame, table_name: str):
    create_index_if_not_exists()

    logger.info(f"🔍 Processing table: {table_name}")

    rows = df.to_dict(orient="records")
    chunks = [
        {k: v for k, v in row.items() if pd.notnull(v)}
        for row in rows
    ]
    logger.info(f"🔢 Generating embeddings for {len(chunks)} rows...")
    texts = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
    embeddings = get_bedrock_embeddings(texts)

    logger.info("📥 Indexing documents in OpenSearch...")
    for i, (row, embedding, chunk) in enumerate(zip(rows, embeddings, chunks)):
        doc = {
            "embedding": embedding,
            "chunk": chunk,
            "source_table": table_name,
            "indicator_acronym": row.get("indicator_acronym")
        }
        opensearch.index(index=INDEX_NAME, id=f"{table_name}-{i}", body=doc)

    logger.info(f"✅ Vectorization completed for {len(chunks)} rows of {table_name}")


def retrieve_context(query, indicator, top_k=100):
    embedding = get_bedrock_embeddings([query])[0]
    
    knn_query = {
        "size": top_k,
        "query": {
            "bool": {
                "must": [
                    {"term": {"indicator_acronym": indicator}},
                    {
                        "knn": {
                            "embedding": {
                                "vector": embedding,
                                "k": top_k
                            }
                        }
                    }
                ]
            }
        }
    }
    response = opensearch.search(index=INDEX_NAME, body=knn_query)
    return [hit["_source"]["chunk"] for hit in response["hits"]["hits"]]


def run_pipeline(indicator):
    logger.info("📂 Loading data from MySQL...")
    df1 = load_data("vw_ai_deliverables")
    df2 = load_data("vw_ai_project_contribution")
    df3 = load_data("vw_ai_questions")

    # insert_into_opensearch(df1, "vw_ai_deliverables")
    # insert_into_opensearch(df2, "vw_ai_project_contribution")
    # insert_into_opensearch(df3, "vw_ai_questions")

    # logger.info("📚 Retrieving relevant context from OpenSearch...")
    # context = retrieve_context(PROMPT, indicator)

    # logger.info("✍️  Generating report with LLM...")
    # query = f"""
    #     Using this information:\n{context}\n\n
    #     Do the following:\n{PROMPT}
    #     """
    
    # report = invoke_model(query)
    # # logger.info(report)