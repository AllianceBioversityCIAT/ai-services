"""Main pipeline for generating Annual Reports using OpenSearch and LLMs."""

import re
import json
import boto3
import numpy as np
import pandas as pd
from requests_aws4auth import AWS4Auth
from db_conn.sql_connection import load_data
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import BR, OPENSEARCH
from opensearchpy import OpenSearch, RequestsHttpConnection
from app.llm.invoke_llm import invoke_model, get_bedrock_embeddings
from app.utils.prompts.diss_targets_prompt import generate_target_prompt
from app.utils.prompts.annual_report_prompt import generate_report_prompt
from app.utils.prompts.challenges_prompt import generate_challenges_prompt

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


def insert_into_opensearch(table_name: str):
    try:
        logger.info(f"🔍 Processing table: {table_name}")

        df = load_data(table_name)
        rows = df.to_dict(orient="records")

        chunks = []
        for row in rows:
            chunk = {
                k: v for k, v in row.items()
                if pd.notnull(v) and v != ""
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

        ## QUESTIONS SEARCH
        questions_query = {
            "size": 10000,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"indicator_acronym": indicator}},
                        {"term": {"year": year}},
                        {
                            "bool": {
                                "should": [
                                    {"term": {"source_table": "vw_ai_questions"}},
                                    {"term": {"source_table": "vw_ai_project_contribution"}}
                                ],
                                "minimum_should_match": 1
                            }
                        }
                    ]
                }
            }
        }

        questions_response = opensearch.search(index=INDEX_NAME, body=questions_query)
        questions_chunks = [hit["_source"]["chunk"] for hit in questions_response["hits"]["hits"]]

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
                or
                (chunk.get("table_type") == "oicrs" and chunk.get("cluster_role") == "Shared")
                or
                (chunk.get("table_type") == "contributions" and chunk.get("phase_name") == "AWPB")
                or
                (chunk.get("table_type") == "contributions" and chunk.get("phase_name") == "Progress")
            )
        ]

        ## FILTER QUESTIONS CHUNKS
        filtered_questions_chunks = [
            chunk for chunk in questions_chunks
            if not (
                (chunk.get("table_type") == "questions" and chunk.get("phase_name") == "AWPB")
                or
                (chunk.get("table_type") == "questions" and chunk.get("phase_name") == "Progress")
                or
                (chunk.get("table_type") == "contributions" and chunk.get("phase_name") == "AWPB")
                or
                (chunk.get("table_type") == "contributions" and chunk.get("phase_name") == "Progress")
                or
                (chunk.get("indicator_acronym") == "PDO Indicator 1" and chunk.get("question").startswith("2.0"))
                or
                (chunk.get("indicator_acronym") == "PDO Indicator 2" and chunk.get("question").startswith("3.0"))
                or
                (chunk.get("indicator_acronym") == "PDO Indicator 3" and chunk.get("question").startswith("3.0"))
                or
                (chunk.get("indicator_acronym") == "IPI 2.3" and chunk.get("question").startswith("0"))
                or
                (chunk.get("indicator_acronym") == "IPI 2.3" and chunk.get("question").startswith("1"))
                or
                (chunk.get("indicator_acronym") == "IPI 2.3" and chunk.get("question").startswith("2"))
            )
        ]

        return filtered_knn_chunks, filtered_questions_chunks
    
    except Exception as e:
        logger.error(f"❌ Error retrieving context: {e}")
        return []


def calculate_summary(indicator, year):
    df_contributions = load_data("vw_ai_project_contribution")
    df_filtered = df_contributions[
        (df_contributions["indicator_acronym"] == indicator) &
        (df_contributions["year"] == year)
    ]

    percent_indicators = ["IPI 2.2", "IPI 3.3"]

    if indicator in percent_indicators:
        total_expected = df_filtered["Milestone expected value"].mean()
        total_achieved = df_filtered["Milestone reported value"].mean()
    else:
        total_expected = df_filtered["Milestone expected value"].sum()
        total_achieved = df_filtered["Milestone reported value"].sum()
        
    progress = round((total_achieved / total_expected) * 100, 2) if total_expected > 0 else 0

    def clean_number(n):
        return int(n) if float(n).is_integer() else round(n, 2)

    return clean_number(total_expected), clean_number(total_achieved), clean_number(progress)


def extract_dois_from_text(text):
    markdown_links = re.findall(r"\[.*?\]\((https?://[^\s)]+)\)", text)
    plain_links = re.findall(r"(?<!\()https?://[^\s\]\)]+", text)

    return set(markdown_links + plain_links)


def add_missed_links(report, context):
    logger.info("📍 Adding missed links to the report...")
    context_dois = {chunk.get("doi") for chunk in context if "doi" in chunk and chunk["doi"]}
    used_dois = extract_dois_from_text(report)
    missed_dois = context_dois - used_dois
    missed_dois = {doi for doi in missed_dois if doi and doi.strip().lower() != "confidential"}

    if missed_dois:
        missed_section = "\n\n## Missed links\nThe following references were part of the context but not explicitly included:\n"
        doi_to_cluster = {chunk["doi"]: chunk.get("cluster_acronym", "N/A") for chunk in context if "doi" in chunk and chunk["doi"]}
        missed_section += "\n".join(
            f"- [{doi}]({doi}) (Cluster: {doi_to_cluster.get(doi, 'N/A')})"
            for doi in sorted(missed_dois)
        )
        report += missed_section
    
    return report


def generate_challenges_report(year):
    """
    Generate a Challenges and Lessons Learned report.
    """
    try:
        logger.info(f"🎯 Starting Challenges and Lessons Learned report generation for {year}...")
        
        challenges_query = {
            "size": 10000,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"source_table": "vw_ai_challenges"}}
                    ]
                }
            }
        }

        challenges_response = opensearch.search(index=INDEX_NAME, body=challenges_query)
        challenges_chunks = [hit["_source"]["chunk"] for hit in challenges_response["hits"]["hits"]]
        
        if not challenges_chunks:
            logger.warning(f"⚠️ No challenges data found for year {year}")
            return f"# Challenges and Lessons Learned - {year}\n\nNo challenges and lessons learned data available for {year}."
        
        challenges_prompt = generate_challenges_prompt(year)
        
        query = f"""
            Using this information:\n{challenges_chunks}\n\n
            Do the following:\n{challenges_prompt}
        """
        
        logger.info("🔄 Generating Challenges and Lessons Learned report...")
        challenges_report = invoke_model(query)
        
        logger.info("✅ Challenges and Lessons Learned report generation completed successfully.")
        return challenges_report
        
    except Exception as e:
        logger.error(f"❌ Error generating Challenges and Lessons Learned report: {e}")
        return f"# Challenges and Lessons Learned - {year}\n\nError generating report: {str(e)}"


def generate_indicator_tables(year):
    """
    Generate tables for all PDO, IPI 1.x, IPI 2.x, IPI 3.x.
    Each table contains: Indicator statement, End-year target, Projected targets, Achieved, Brief overview.
    The 'Brief overview' field is summarized by cluster using LLM.
    """
    logger.info(f"🎯 Starting indicator tables generation for {year}...")

    df = load_data("vw_ai_project_contribution")
    df = df[df["year"] == year]

    groups = {
        "PDO": df[df["indicator_acronym"].str.startswith("PDO")],
        "IPI 1.x": df[df["indicator_acronym"].str.startswith("IPI 1.")],
        "IPI 2.x": df[df["indicator_acronym"].str.startswith("IPI 2.")],
        "IPI 3.x": df[df["indicator_acronym"].str.startswith("IPI 3.")]
    }

    tables = {}

    for group_name, group_df in groups.items():
        indicators = sorted(group_df["indicator_acronym"].unique())
        table_rows = []
        for indicator in indicators:
            ind_df = group_df[group_df["indicator_acronym"] == indicator]
            indicator_title = ind_df["indicator_title"].iloc[0] if not ind_df["indicator_title"].isnull().all() else indicator
            
            percent_indicators = ["IPI 2.2", "IPI 3.3"]

            if indicator in percent_indicators:
                end_year_target = ind_df["Milestone expected value"].mean()
                achieved = ind_df["Milestone reported value"].mean()
            else:
                end_year_target = ind_df["Milestone expected value"].sum()
                achieved = ind_df["Milestone reported value"].sum()
            
            projected = ""
            
            cluster_narratives = ind_df.groupby("cluster_acronym")["Milestone achieved narrative"].apply(lambda x: " ".join(x.dropna()))
            formatted_narratives = "\n".join([f"{cluster}: {narrative}" for cluster, narrative in cluster_narratives.items() if narrative.strip()])
            
            if formatted_narratives.strip():
                prompt = f"""
                Summarize these contribution narratives by cluster in 2-3 sentences, highlighting key achievements and 
                contributions:\n{formatted_narratives}. If a cluster has no contributions, omit it from the summary. Do
                not return a title, only the summary per cluster. And do not return the answer in markdown format.
                """
                brief_overview = invoke_model(prompt)
            else:
                brief_overview = "No narratives available."
            
            table_rows.append({
                "Indicator statement": indicator_title,
                "End-year target 2025": end_year_target,
                #"Projected targets for 2025 (Mid-year report 2025)": projected,
                "Achieved in 2025": achieved,
                "Brief overviews": brief_overview
            })
        tables[group_name] = pd.DataFrame(table_rows)
    
    return tables


def run_pipeline(indicator, year, insert_data=False):
    try:
        if insert_data:
            if opensearch.indices.exists(index=INDEX_NAME):
                logger.info(f"🗑️ Deleting existing index: {INDEX_NAME}")
                opensearch.indices.delete(index=INDEX_NAME)
            create_index_if_not_exists()
            insert_into_opensearch("vw_ai_deliverables")
            insert_into_opensearch("vw_ai_project_contribution")
            insert_into_opensearch("vw_ai_questions")
            insert_into_opensearch("vw_ai_oicrs")
            insert_into_opensearch("vw_ai_innovations")
            insert_into_opensearch("vw_ai_challenges")
        
        ## Part 1: Generate the report with deliverables, contributions, oicrs, and innovations
        total_expected, total_achieved, progress = calculate_summary(indicator, year)

        PROMPT = generate_report_prompt(indicator, year, total_expected, total_achieved, progress)
        
        context, questions = retrieve_context(PROMPT, indicator, year)

        query = f"""
            Using this information:\n{context}\n\n
            Do the following:\n{PROMPT}
            """

        generated_report = invoke_model(query)

        ## Part 2: Generate the report with dissagregated targets
        accepted_indicators = ["PDO Indicator 1", "PDO Indicator 2", "PDO Indicator 3", "IPI 2.3"]

        if indicator in accepted_indicators:
            TARGET_PROMPT = generate_target_prompt(indicator)
            
            query_questions = f"""
                Using this information:\n{questions}\n\n
                Do the following:\n{TARGET_PROMPT}
                """
            
            logger.info("☑️  Starting disaggregated targets report generation...")
            targets_report = invoke_model(query_questions)
            
            ## Combine both reports
            targets_section = "\n\n## Disaggregated targets\n" + targets_report
            generated_report += targets_section
        
        ## Part 3: Add missed links section
        final_report = add_missed_links(generated_report, context)

        logger.info("✅ Report generation completed successfully.")
        return final_report

    except Exception as e:
        logger.error(f"❌ Error in pipeline execution: {e}")