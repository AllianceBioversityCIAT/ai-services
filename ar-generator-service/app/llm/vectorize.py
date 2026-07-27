"""Main pipeline for generating Mid-Year Progress Reports using S3 Vectors and LLMs."""

import json

from app.utils.logger.logger_util import get_logger
from app.utils.prompts.report_prompt import generate_report_prompt
from app.llm.invoke_llm import invoke_model
from app.s3_vectors.client import get_vector_store_client
from app.s3_vectors.ingestion import MIDYEAR_INGEST_TABLES, ingest_tables
from app.retrieval.semantic_search import semantic_search
from app.retrieval.sql_retrieval import fetch_doi_chunks
from app.retrieval.context_merger import merge_knn_and_doi
from app.retrieval.post_filters import filter_midyear_chunks
from db_conn.sql_connection import load_data

logger = get_logger()


def get_vector_store_client_compat():
    """Backward-compatible accessor for the vector store client."""
    return get_vector_store_client()


def retrieve_context(query, indicator, year, top_k=10000):
    try:
        knn_chunks = semantic_search(query, indicator, year, top_k=top_k)
        doi_chunks = fetch_doi_chunks(indicator, year)
        combined_chunks = merge_knn_and_doi(knn_chunks, doi_chunks)
        return filter_midyear_chunks(combined_chunks)
    except Exception as error:
        logger.error(f"❌ Error retrieving context: {error}")
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
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(context, file, indent=2, ensure_ascii=False)
        logger.info(f"📝 Context saved to {output_path}")
    except Exception as error:
        logger.error(f"❌ Error saving context to file: {error}")


def _filter_chunks_for_contingency(chunks, level):
    """Apply contingency filters to reduce chunk size when input is too long."""
    if level == 0:
        return chunks

    filtered = [
        chunk for chunk in chunks
        if not (
            chunk.get("table_type") == "deliverables" and (
                chunk.get("already_disseminated") == "No"
                or not chunk.get("dissemination_URL")
                or chunk.get("status") != "Completed"
            )
        )
    ]

    if level >= 2:
        deliverables = [chunk for chunk in filtered if chunk.get("table_type") == "deliverables"][:200]
        contributions = [chunk for chunk in filtered if chunk.get("table_type") == "contributions"][:1000]
        filtered = deliverables + contributions

    return filtered


def run_pipeline(indicator, year, insert_data=False):
    try:
        if insert_data:
            client = get_vector_store_client()
            client.recreate_index()
            ingest_tables(MIDYEAR_INGEST_TABLES, client=client)
            logger.info("✅ Data insertion completed successfully.")

        total_expected, total_achieved, progress = calculate_summary(indicator, year)
        prompt = generate_report_prompt(indicator, year, total_expected, total_achieved, progress)
        context = retrieve_context(prompt, indicator, year)

        try:
            query = f"""
                Using this information:\n{context}\n\n
                Do the following:\n{prompt}
                """
            final_report = invoke_model(query)
        except Exception as error:
            if "Input is too long" in str(error):
                logger.warning(f"⚠️ Input is too long for {indicator}. Applying Level 1 contingency...")
                try:
                    filtered_context = _filter_chunks_for_contingency(context, level=1)
                    query = f"""
                        Using this information:\n{filtered_context}\n\n
                        Do the following:\n{prompt}
                        """
                    final_report = invoke_model(query)
                    logger.info(f"✅ Report generated for {indicator} with Level 1 contingency.")
                except Exception as error_level_1:
                    if "Input is too long" in str(error_level_1):
                        logger.warning(f"⚠️ Still too long for {indicator}. Applying Level 2 contingency...")
                        filtered_context = _filter_chunks_for_contingency(context, level=2)
                        query = f"""
                            Using this information:\n{filtered_context}\n\n
                            Do the following:\n{prompt}
                            """
                        final_report = invoke_model(query)
                        logger.info(f"✅ Report generated for {indicator} with Level 2 contingency.")
                    else:
                        raise error_level_1
            else:
                raise

        logger.info("✅ Report generation completed successfully.")
        return final_report

    except Exception as error:
        logger.error(f"❌ Error in pipeline execution: {error}")

        if "Input is too long" in str(error):
            logger.error("❌ Input is still too long even after applying contingency filters.")
            return (
                f"# Report Generation Error\n\nThe input context for indicator {indicator} "
                f"in year {year} is too long for the model, even after applying data reduction filters."
            )

        return None
