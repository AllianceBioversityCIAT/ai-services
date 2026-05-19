"""Main pipeline for generating Annual Reports using OpenSearch and LLMs."""

import re
import json
import boto3
import numpy as np
import pandas as pd
from collections import defaultdict
from requests_aws4auth import AWS4Auth
from db_conn.sql_connection import load_data
from concurrent.futures import ThreadPoolExecutor
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import OPENSEARCH
from opensearchpy import OpenSearch, RequestsHttpConnection
from app.llm.invoke_llm import invoke_model, get_bedrock_embeddings
from app.utils.prompts.diss_targets_prompt import generate_target_prompt
from app.utils.prompts.annual_report_prompt import generate_search_prompt, generate_summary_prompt, generate_cluster_prompt, generate_cluster_editorial_prompt
from app.utils.prompts.challenges_prompt import generate_challenges_prompt

logger = get_logger()


if not OPENSEARCH.get('host'):
    raise ValueError("OPENSEARCH_HOST environment variable is required. Please configure it in Lambda environment variables.")
if not OPENSEARCH.get('index'):
    raise ValueError("OPENSEARCH_INDEX_NAME environment variable is required. Please configure it in Lambda environment variables.")
if not OPENSEARCH.get('aws_access_key'):
    raise ValueError("AWS_ACCESS_KEY_ID_OS environment variable is required. Please configure it in Lambda environment variables.")
if not OPENSEARCH.get('aws_secret_key'):
    raise ValueError("AWS_SECRET_ACCESS_KEY_OS environment variable is required. Please configure it in Lambda environment variables.")


credentials = boto3.Session(
    aws_access_key_id=OPENSEARCH['aws_access_key'],
    aws_secret_access_key=OPENSEARCH['aws_secret_key'],
    region_name=OPENSEARCH.get('region', 'us-east-1')
).get_credentials()

region = OPENSEARCH.get('region', 'us-east-1')

awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)


opensearch = OpenSearch(
    hosts=[{'host': OPENSEARCH['host'], 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

INDEX_NAME = OPENSEARCH['index']


def get_opensearch_client():
    """Get OpenSearch client (maintained for backward compatibility)."""
    return opensearch


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
    """Retrieve context from OpenSearch for the given indicator and year."""
    try:
        search_tables = [
            {"term": {"source_table": "vw_ai_deliverables"}},
            {"term": {"source_table": "vw_ai_project_contribution"}},
            {"term": {"source_table": "vw_ai_oicrs"}},
            {"term": {"source_table": "vw_ai_innovations"}}
        ]
        
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
                                "should": search_tables,
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

        def should_exclude_chunk(chunk):
            return (
                (chunk.get("table_type") == "deliverables" and chunk.get("cluster_role") == "Shared")
                or
                (chunk.get("table_type") == "deliverables" and chunk.get("status") == "Cancelled")
                or
                (chunk.get("table_type") == "innovations" and chunk.get("cluster_role") == "Shared")
                or
                (chunk.get("table_type") == "oicrs" and chunk.get("cluster_role") == "Shared")
                or
                (chunk.get("table_type") == "contributions" and chunk.get("phase_name") == "AWPB")
                or
                (chunk.get("table_type") == "contributions" and chunk.get("phase_name") == "Progress")
            )

        filtered_knn_chunks = [chunk for chunk in knn_chunks if not should_exclude_chunk(chunk)]

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
                (chunk.get("indicator_acronym") == "PDO Indicator 1" and chunk.get("question", "").startswith("2.0"))
                or
                (chunk.get("indicator_acronym") == "PDO Indicator 2" and chunk.get("question", "").startswith("3.0"))
                or
                (chunk.get("indicator_acronym") == "PDO Indicator 3" and chunk.get("question", "").startswith("3.0"))
                or
                (chunk.get("indicator_acronym") == "IPI 2.3" and chunk.get("question", "").startswith("0"))
                or
                (chunk.get("indicator_acronym") == "IPI 2.3" and chunk.get("question", "").startswith("1"))
                or
                (chunk.get("indicator_acronym") == "IPI 2.3" and chunk.get("question", "").startswith("2"))
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


def group_context_by_cluster(chunks):
    """Group context chunks by cluster_acronym. Chunks missing this field are silently excluded."""
    grouped = defaultdict(list)
    for chunk in chunks:
        cluster = chunk.get("cluster_acronym")
        if cluster:
            grouped[cluster].append(chunk)
    return dict(grouped)


def _get_indicator_title(context, indicator):
    """Extract indicator title from context chunks."""
    for chunk in context:
        title = chunk.get("indicator_title")
        if title and chunk.get("indicator_acronym") == indicator:
            return title
    return indicator


def _filter_chunks_for_contingency(chunks, level):
    """Apply contingency filters to reduce chunk size for a cluster's context."""
    if level == 0:
        return chunks

    filtered = [
        c for c in chunks
        if not (
            c.get("table_type") == "deliverables" and (
                c.get("already_disseminated") == "No"
                or not c.get("dissemination_URL")
                or c.get("status") != "Completed"
            )
        )
    ]

    if level >= 2:
        deliverables = [c for c in filtered if c.get("table_type") == "deliverables"][:200]
        contributions = [c for c in filtered if c.get("table_type") == "contributions"][:1000]
        filtered = deliverables + contributions

    return filtered


def _generate_single_cluster_narrative(cluster_acronym, cluster_chunks, indicator, year):
    """Generate the narrative paragraph for a single cluster."""
    try:
        cluster_prompt = generate_cluster_prompt(indicator, year, cluster_acronym)

        try:
            query = f"Using this information:\n{cluster_chunks}\n\nDo the following:\n{cluster_prompt}"
            narrative = invoke_model(query)
            logger.info(f"✅ Narrative generated for cluster: {cluster_acronym}")
        except Exception as e:
            if "Input is too long" in str(e):
                logger.warning(f"⚠️ Input is too long for cluster {cluster_acronym}. Applying Level 1 contingency...")
                try:
                    filtered_chunks = _filter_chunks_for_contingency(cluster_chunks, level=1)
                    query = f"Using this information:\n{filtered_chunks}\n\nDo the following:\n{cluster_prompt}"
                    narrative = invoke_model(query)
                    logger.info(f"✅ Narrative generated for cluster {cluster_acronym} with Level 1 contingency.")
                except Exception as e2:
                    if "Input is too long" in str(e2):
                        logger.warning(f"⚠️ Still too long for cluster {cluster_acronym}. Applying Level 2 contingency...")
                        filtered_chunks = _filter_chunks_for_contingency(cluster_chunks, level=2)
                        query = f"Using this information:\n{filtered_chunks}\n\nDo the following:\n{cluster_prompt}"
                        narrative = invoke_model(query)
                        logger.info(f"✅ Narrative generated for cluster {cluster_acronym} with Level 2 contingency.")
                    else:
                        raise e2
            else:
                raise

        ## Pass 2: Editorial rewrite for impact-driven narrative
        logger.info(f"✍️  Rewriting narrative for cluster: {cluster_acronym}...")
        editorial_prompt = generate_cluster_editorial_prompt(indicator, year, cluster_acronym)
        editorial_query = f"Raw evidence draft:\n{narrative}\n\nDo the following:\n{editorial_prompt}"
        final_narrative = invoke_model(editorial_query)
        logger.info(f"✅ Editorial pass completed for cluster: {cluster_acronym}")

        return cluster_acronym, final_narrative
    except Exception as e:
        logger.error(f"❌ Error generating narrative for cluster {cluster_acronym}: {e}")
        return cluster_acronym, f"*Narrative generation failed for {cluster_acronym}: {str(e)}*"


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
                f"End-year target {year}": end_year_target,
                f"Achieved in {year}": achieved,
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

            logger.info("✅ Data insertion completed successfully.")

        total_expected, total_achieved, progress = calculate_summary(indicator, year)
        SEARCH_QUERY = generate_search_prompt(indicator, year)

        context, questions = retrieve_context(SEARCH_QUERY, indicator, year)
        
        grouped_context = group_context_by_cluster(context)
        clusters = sorted(grouped_context.keys())

        indicator_title = _get_indicator_title(context, indicator)
        SUMMARY_PROMPT = generate_summary_prompt(indicator, indicator_title, year, total_expected, total_achieved, progress)

        logger.info(f"🚀 Starting parallel generation for {len(clusters)} clusters...")

        def _run_summary():
            return invoke_model(SUMMARY_PROMPT)

        with ThreadPoolExecutor(max_workers=len(clusters) + 1) as executor:
            summary_future = executor.submit(_run_summary)
            cluster_futures = {
                executor.submit(
                    _generate_single_cluster_narrative,
                    cluster,
                    grouped_context[cluster],
                    indicator,
                    year
                ): cluster
                for cluster in clusters
            }

            summary_text = summary_future.result()
            cluster_narratives = {}
            for future, cluster in cluster_futures.items():
                _, narrative = future.result()
                cluster_narratives[cluster] = narrative

        generated_report = f"# {indicator_title}\n\n"
        generated_report += summary_text + "\n\n"
        generated_report += "## Indicator Narrative\n\n"
        for cluster in clusters:
            generated_report += cluster_narratives.get(cluster, "") + "\n\n"

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
            generated_report += "\n\n## Disaggregated targets\n" + targets_report

        logger.info("✅ Report generation completed successfully.")
        return generated_report

    except Exception as e:
        logger.error(f"❌ Error in pipeline execution: {e}")

        if "Input is too long" in str(e):
            logger.error("❌ Input is still too long even after applying contingency filters.")
            return f"# Report Generation Error\n\nThe input context for indicator {indicator} in year {year} is too long for the model, even after applying data reduction filters."
        
        return None