import re
import json
import boto3
import numpy as np
import pandas as pd
from requests_aws4auth import AWS4Auth
from db_conn.mysql_connection import load_data
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import BR, OPENSEARCH
from opensearchpy import OpenSearch, RequestsHttpConnection
from app.utils.prompts.kb_generation_prompt import DEFAULT_PROMPT
from app.utils.prompts.report_generation_prompt import generate_report_prompt


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
            modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            # modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
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


def create_index_if_not_exists(dimension=1024):
    try:
        # opensearch.indices.delete(index=INDEX_NAME)
        if not opensearch.indices.exists(index=INDEX_NAME):
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
                        "indicator_acronym": {"type": "keyword"},
                        "year": {"type": "keyword"}
                    }
                }
            }
            opensearch.indices.create(index=INDEX_NAME, body=index_body)
            return True
        
        logger.info(f"📦 Index {INDEX_NAME} already exists. Skipping creation.")
        return False

    except Exception as e:
        logger.error(f"❌ Error creating index: {e}")
        return False


def insert_into_opensearch(table_name: str):
    try:
        ## Comment out the next 4 lines if you are going to insert data into the index for the first time
        created = create_index_if_not_exists()
        if not created:
            logger.info(f"⚠️  Skipping insertion for {table_name} since index already exists.")
            return

        ## Uncomment out the next line if you are going to insert data into the index for the first time
        # create_index_if_not_exists()

        logger.info(f"🔍 Processing table: {table_name}")

        df = load_data(table_name)
        rows = df.to_dict(orient="records")

        date_fields = ["last_updated_altmetric", "last_sync_almetric"]

        chunks = []
        for row in rows:
            chunk = {
                k: v for k, v in row.items()
                if (k not in date_fields or v != "") and pd.notnull(v) and v != ""
            }
            chunks.append(chunk)

        logger.info(f"🔢 Generating embeddings for {len(chunks)} rows...")
        texts = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
        embeddings = get_bedrock_embeddings(texts)

        logger.info("📥 Indexing documents in OpenSearch...")
        for i, (row, embedding, chunk) in enumerate(zip(rows, embeddings, chunks)):
            doc = {
                "embedding": embedding,
                "chunk": chunk,
                "source_table": table_name,
                "indicator_acronym": row.get("indicator_acronym"),
                "year": row.get("year")
            }
            opensearch.index(index=INDEX_NAME, id=f"{table_name}-{i}", body=doc)

        logger.info(f"✅ Vectorization completed for {len(chunks)} rows of {table_name}")
    
    except Exception as e:
        logger.error(f"❌ Error inserting into OpenSearch for {table_name}: {e}")


def retrieve_context(query, indicator, year, top_k=10000):
    try:
        logger.info("📚 Retrieving relevant context from OpenSearch...")
        embedding = get_bedrock_embeddings([query])[0]
        
        knn_query = {
            "size": top_k,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"indicator_acronym": indicator}},
                        {"term": {"year": year}},
                        {
                            "bool": {
                                "should": [
                                    {"term": {"source_table": "vw_ai_deliverables"}},
                                    {"term": {"source_table": "vw_ai_project_contribution"}}
                                ],
                                "minimum_should_match": 1
                            }
                        }
                    ],
                    "must": [
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

        knn_response = opensearch.search(index=INDEX_NAME, body=knn_query)
        knn_chunks = [hit["_source"]["chunk"] for hit in knn_response["hits"]["hits"]]

        doi_query = {
            "size": 10000,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"indicator_acronym": indicator}},
                        {"term": {"year": year}},
                        {"exists": {"field": "chunk.doi"}},
                        {"term": {"source_table": "vw_ai_deliverables"}}
                    ]
                }
            }
        }

        doi_response = opensearch.search(index=INDEX_NAME, body=doi_query)
        doi_chunks = [hit["_source"]["chunk"] for hit in doi_response["hits"]["hits"]]

        seen_keys = set()
        combined_chunks = []

        for chunk in knn_chunks + doi_chunks:
            doi = chunk.get("doi")
            cluster = chunk.get("cluster_acronym")
            indicator_code = chunk.get("indicator_acronym")

            if doi:
                key = (doi, cluster, indicator_code)
                if key not in seen_keys:
                    seen_keys.add(key)
                    combined_chunks.append(chunk)
            else:
                combined_chunks.append(chunk)

        return combined_chunks
    
    except Exception as e:
        logger.error(f"❌ Error retrieving context: {e}")
        return []


def calculate_summary(indicator, year):
            df_contributions = load_data("vw_ai_project_contribution")
            df_filtered = df_contributions[
                (df_contributions["indicator_acronym"] == indicator) &
                (df_contributions["year"] == year)
            ]
            total_expected = df_filtered["Milestone expected value"].sum()
            total_achieved = df_filtered["Milestone reported value"].sum()
            progress = round((total_achieved / total_expected) * 100, 2) if total_expected > 0 else 0

            def clean_number(n):
                return int(n) if float(n).is_integer() else round(n, 2)

            return clean_number(total_expected), clean_number(total_achieved), clean_number(progress)


def extract_dois_from_text(text):
    pattern = r"https?://\S+"
    return {match.rstrip(".,)];") for match in re.findall(pattern, text)}


def run_pipeline(indicator, year):
    try:
        insert_into_opensearch("vw_ai_deliverables")
        insert_into_opensearch("vw_ai_project_contribution")
        insert_into_opensearch("vw_ai_questions")
        
        total_expected, total_achieved, progress = calculate_summary(indicator, year)

        PROMPT = generate_report_prompt(indicator, year, total_expected, total_achieved, progress)
        context = retrieve_context(PROMPT, indicator, year)

        output_path = f"context_{indicator}_{year}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)
        logger.info(f"📝 Context saved to {output_path}")

        query = f"""
            Using this information:\n{context}\n\n
            Do the following:\n{PROMPT}
            """

        generated_report = invoke_model(query)

        logger.info("📍 Adding missed links to the report...")
        context_dois = {chunk.get("doi") for chunk in context if "doi" in chunk and chunk["doi"]}
        used_dois = extract_dois_from_text(generated_report)
        missed_dois = context_dois - used_dois

        if missed_dois:
            missed_section = "\n\n## Missed links\nThe following references were part of the context but not explicitly included:\n"
            doi_to_cluster = {chunk["doi"]: chunk.get("cluster_acronym", "N/A") for chunk in context if "doi" in chunk and chunk["doi"]}
            missed_section += "\n".join(f"- {doi} (Cluster: {doi_to_cluster.get(doi, 'N/A')})" for doi in sorted(missed_dois))
            generated_report += missed_section

        logger.info("✅ Report generation completed successfully.")
        return generated_report

    except Exception as e:
        logger.error(f"❌ Error in pipeline execution: {e}")