import json
import vecs
import boto3
import numpy as np
import pandas as pd
from db_conn.mysql_connection import load_data
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import BR, SUPABASE
from app.utils.prompts.prompt import PROMPT


logger = get_logger()

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=BR['aws_access_key'],
    aws_secret_access_key=BR['aws_secret_key'],
    region_name='us-east-1' 
)

SUPABASE_URL = SUPABASE['url']
SUPABASE_COLLECTION = SUPABASE['collection']


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
            "max_tokens": 3000,
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


def insert_into_supabase(df: pd.DataFrame, table_name: str):
    client = vecs.create_client(SUPABASE_URL)
    docs = client.get_or_create_collection(SUPABASE_COLLECTION, dimension=1024)

    logger.info(f"🔍 Processing table: {table_name}")

    rows = df.to_dict(orient="records")
    chunks = [
        {k: v for k, v in row.items() if pd.notnull(v)}
        for row in rows
    ]
    logger.info(f"🔢 Generating embeddings for {len(chunks)} rows...")
    text = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
    embeddings = get_bedrock_embeddings(text)

    logger.info("📄 Generating metadata...")
    all_metadata = [
        {
            "chunk": chunk,
            "source_table": table_name,
            "indicator_acronym": row.get("indicator_acronym")
        }
        for row, chunk in zip(rows, chunks)
    ]

    logger.info("📥 Inserting in Supabase...")
    docs.upsert([
        (f"{table_name}-{i}", embedding, metadata)
        for i, (embedding, metadata) in enumerate(zip(embeddings, all_metadata))
    ])

    docs.create_index(measure=vecs.IndexMeasure.cosine_distance)
    logger.info(f"✅ Vectorization completed for {len(chunks)} rows of {table_name}")

    return docs


def retrieve_context(query, indicator, top_k=100):
    embedding = get_bedrock_embeddings([query])[0]
    
    client = vecs.create_client(SUPABASE_URL)
    collection = client.get_or_create_collection(SUPABASE_COLLECTION, dimension=1024)
    collection.create_index(measure=vecs.IndexMeasure.cosine_distance)
    
    results = collection.query(
        data=embedding,
        limit=top_k,
        filters={"indicator_acronym": {"$eq": f"{indicator}"}},
        include_value=True,
        include_metadata=True
    )
    return [r[2]["chunk"] for r in results]


def run_pipeline(indicator):
    # logger.info("🔍 Loading data from MySQL...")
    # df1 = load_data("vw_ai_deliverables")
    # df2 = load_data("vw_ai_project_contribution")
    # df3 = load_data("vw_ai_questions")

    # insert_into_supabase(df1, "vw_ai_deliverables")
    # insert_into_supabase(df2, "vw_ai_project_contribution")
    # insert_into_supabase(df3, "vw_ai_questions")

    logger.info("📚 Retrieving relevant context from Supabase...")
    context = retrieve_context(PROMPT, indicator)

    logger.info("✍️  Generating report with LLM...")
    query = f"""
        Using this information:\n{context}\n\n
        Do the following:\n{PROMPT}
        """
    
    report = invoke_model(query)
    #logger.info(report)