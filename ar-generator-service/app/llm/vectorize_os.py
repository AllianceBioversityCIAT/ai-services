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
from app.utils.prompts.report_prompt import generate_report_prompt
from app.llm.invoke_llm import invoke_model, get_bedrock_embeddings
from app.utils.prompts.chatbot_prompt import generate_chatbot_prompt
from app.utils.prompts.diss_targets_prompt import generate_target_prompt

logger = get_logger()

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
INDEX_NAME_CHATBOT = OPENSEARCH['index_chatbot']


def create_index_if_not_exists(dimension=1024):
    try:
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


def insert_into_opensearch(table_name: str, mode: str):
    try:
        logger.info(f"🔍 Processing table: {table_name}")

        if mode == "generator":
            df = load_data(table_name)
        # else:
        #     df = load_full_data(table_name)
        
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
        
        ## VECTOR SEARCH
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
                                    {"term": {"source_table": "vw_ai_project_contribution"}},
                                    {"term": {"source_table": "vw_ai_oicrs"}},
                                    {"term": {"source_table": "vw_ai_innovations"}}
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

        ## DOI SEARCH
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

        ## COMBINE KNN AND DOI CHUNKS
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

        ## FILTER KNN CHUNKS
        filtered_knn_chunks = [
            chunk for chunk in combined_chunks
            if not (
                (chunk.get("table_type") == "deliverables" and chunk.get("cluster_role") == "Shared")
                or
                (chunk.get("table_type") == "innovations" and chunk.get("cluster_role") == "Shared")
            )
        ]

        return filtered_knn_chunks
    
    except Exception as e:
        logger.error(f"❌ Error retrieving context: {e}")
        return []


def retrieve_context_chatbot(query, phase=None, indicator=None, section=None):
    """
    Retrieve context for the chatbot dynamically filtering by phase, indicator, and section (source_table).
    - phase: e.g., "Progress 2025", "AWPB 2025", "AR 2025", or "All phases"
    - indicator: e.g., "PDO Indicator 1", or "All indicators"
    - section: e.g., "Deliverables", "OICRs", "Innovations", "Contributions", or "All sections"
    """
    try:
        logger.info("📚 Retrieving relevant context from OpenSearch with dynamic filters...")

        selected_filters_count = 0
        if phase and phase != "All phases":
            selected_filters_count += 1
        if indicator and indicator != "All indicators":
            selected_filters_count += 1
        if section and section != "All sections":
            selected_filters_count += 1

        # Adjust top_k based on filters
        if selected_filters_count >= 2:
            top_k = 10000
        else:
            top_k = 100

        embedding = get_bedrock_embeddings([query])[0]

        selected_year = None
        selected_phase_type = None
        if phase and phase != "All phases":
            parts = phase.split()
            for p in parts:
                if p.isdigit():
                    selected_year = p
            if "Progress" in phase:
                selected_phase_type = "Progress"
            elif "AWPB" in phase:
                selected_phase_type = "AWPB"
            elif "AR" in phase:
                selected_phase_type = "AR"

        filter_conditions = []

        if selected_year:
            filter_conditions.append({"term": {"year": selected_year}})

        if indicator and indicator != "All indicators":
            filter_conditions.append({"term": {"indicator_acronym": indicator}})

        allowed_tables = []
        if section and section != "All sections":
            section_map = {
                "Deliverables": ["vw_ai_deliverables"],
                "OICRs": ["vw_ai_oicrs"],
                "Innovations": ["vw_ai_innovations"],
                "Contributions": ["vw_ai_project_contribution", "vw_ai_questions"],
            }
            if section in section_map:
                allowed_tables.extend(section_map[section])
        else:
            allowed_tables = [
                "vw_ai_deliverables",
                "vw_ai_project_contribution",
                "vw_ai_oicrs",
                "vw_ai_innovations",
                "vw_ai_questions"
            ]

        if allowed_tables:
            filter_conditions.append({
                "bool": {
                    "should": [{"term": {"source_table": tbl}} for tbl in allowed_tables],
                    "minimum_should_match": 1
                }
            })
        
        ## VECTOR SEARCH
        knn_query = {
            "size": top_k,
            "query": {
                "bool": {
                    "filter": filter_conditions,
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

        knn_response = opensearch.search(index=INDEX_NAME_CHATBOT, body=knn_query)
        knn_chunks = [hit["_source"]["chunk"] for hit in knn_response["hits"]["hits"]]

        if selected_phase_type:
            filtered_chunks = []
            for chunk in knn_chunks:
                table_type = chunk.get("table_type")
                chunk_phase = chunk.get("phase_name")
                if table_type in ["questions", "contributions"]:
                    if chunk_phase and selected_phase_type not in chunk_phase:
                        continue
                filtered_chunks.append(chunk)
        else:   
            filtered_chunks = knn_chunks

        ## FILTER KNN CHUNKS
        filtered_knn_chunks = [
            chunk for chunk in filtered_chunks
            if not (
                (chunk.get("table_type") == "deliverables" and chunk.get("cluster_role") == "Shared")
                or
                (chunk.get("table_type") == "innovations" and chunk.get("cluster_role") == "Shared")
            )
        ]

        return filtered_knn_chunks
    
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


def save_context_to_file(context, filename, indicator, year):
    try:
        output_path = f"{filename}_{indicator}_{year}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)
        logger.info(f"📝 Context saved to {output_path}")
    except Exception as e:
        logger.error(f"❌ Error saving context to file: {e}")


def run_pipeline(indicator, year, insert_data=False):
    try:
        if insert_data:
            if opensearch.indices.exists(index=INDEX_NAME):
                logger.info(f"🗑️ Deleting existing index: {INDEX_NAME}")
                opensearch.indices.delete(index=INDEX_NAME)
            create_index_if_not_exists()
            insert_into_opensearch("vw_ai_deliverables", mode="generator")
            insert_into_opensearch("vw_ai_project_contribution", mode="generator")
            insert_into_opensearch("vw_ai_questions", mode="generator")
            insert_into_opensearch("vw_ai_oicrs", mode="generator")
            insert_into_opensearch("vw_ai_innovations", mode="generator")

        total_expected, total_achieved, progress = calculate_summary(indicator, year)

        PROMPT = generate_report_prompt(indicator, year, total_expected, total_achieved, progress)
        
        context = retrieve_context(PROMPT, indicator, year)
        save_context_to_file(context, "context", indicator, year)

        query = f"""
            Using this information:\n{context}\n\n
            Do the following:\n{PROMPT}
            """

        final_report = invoke_model(query, mode="generator")

        logger.info("✅ Report generation completed successfully.")
        return final_report

    except Exception as e:
        logger.error(f"❌ Error in pipeline execution: {e}")


def run_chatbot(user_input, phase=None, indicator=None, section=None, insert_data=False):
    try:
        if insert_data:
            if opensearch.indices.exists(index=INDEX_NAME_CHATBOT):
                logger.info(f"🗑️ Deleting existing index: {INDEX_NAME_CHATBOT}")
                opensearch.indices.delete(index=INDEX_NAME_CHATBOT)
            create_index_if_not_exists()
            insert_into_opensearch("vw_ai_deliverables", mode="chatbot")
            insert_into_opensearch("vw_ai_project_contribution", mode="chatbot")
            insert_into_opensearch("vw_ai_questions", mode="chatbot")
            insert_into_opensearch("vw_ai_oicrs", mode="chatbot")
            insert_into_opensearch("vw_ai_innovations", mode="chatbot")

        context = retrieve_context_chatbot(user_input, phase=phase, indicator=indicator, section=section)
        # save_context_to_file(context, "context", indicator, phase)

        CHATBOT_PROMPT = generate_chatbot_prompt(phase, indicator, section)
        
        query = f"""
You are an AI assistant specialized in AICCRA. Follow these instructions carefully:

{CHATBOT_PROMPT}

---

The user asked the following question:
\"\"\"{user_input}\"\"\"

Use ONLY the following retrieved context to answer the question. 
If the context does not have enough information, clearly say so and suggest a broader search.

Retrieved context:
{context}

Now, provide the best possible answer.      
"""

        final_response = invoke_model(query, mode="chatbot")

        logger.info("✅ Chatbot response generated successfully.")
        return final_response

    except Exception as e:
        logger.error(f"❌ Error in chatbot execution: {e}")
        return f"⚠️ An error occurred: {e}"