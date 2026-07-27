"""Main pipeline for generating Annual Reports using S3 Vectors and LLMs."""

import json
import pandas as pd
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from db_conn.mysql_connection import load_data
from app.utils.logger.logger_util import get_logger
from app.llm.invoke_llm import invoke_model
from app.s3_vectors.client import get_vector_store_client
from app.s3_vectors.ingestion import ANNUAL_INGEST_TABLES, ingest_tables
from app.retrieval.semantic_search import semantic_search
from app.retrieval.sql_retrieval import fetch_challenges_chunks, fetch_questions_chunks
from app.retrieval.post_filters import filter_annual_knn_chunks, filter_questions_chunks
from app.utils.prompts.diss_targets_prompt import generate_target_prompt
from app.utils.prompts.annual_report_prompt import (
    generate_search_prompt,
    generate_summary_prompt,
    generate_cluster_prompt,
    generate_cluster_editorial_prompt,
)
from app.utils.prompts.challenges_prompt import generate_challenges_prompt

logger = get_logger()


def get_vector_store_client_compat():
    """Backward-compatible accessor for the vector store client."""
    return get_vector_store_client()


def retrieve_context(query, indicator, year, top_k=10000):
    """Retrieve context from S3 Vectors and SQL for the given indicator and year."""
    try:
        knn_chunks = semantic_search(query, indicator, year, top_k=top_k)
        questions_chunks = fetch_questions_chunks(indicator, year)

        filtered_knn_chunks = filter_annual_knn_chunks(knn_chunks)
        filtered_questions_chunks = filter_questions_chunks(questions_chunks)
        return filtered_knn_chunks, filtered_questions_chunks
    except Exception as error:
        logger.error(f"❌ Error retrieving context: {error}")
        return [], []


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


def save_context_to_file(context, filename, indicator, year):
    try:
        output_path = f"{filename}_{indicator}_{year}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)
        logger.info(f"📝 Context saved to {output_path}")
    except Exception as e:
        logger.error(f"❌ Error saving context to file: {e}")


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


def _generate_single_cluster_narrative(cluster_acronym, cluster_chunks, indicator, year):
    """Generate the narrative paragraph for a single cluster."""
    try:
        cluster_prompt = generate_cluster_prompt(indicator, year, cluster_acronym)

        try:
            query = f"Using this information:\n{cluster_chunks}\n\nDo the following:\n{cluster_prompt}"
            narrative = invoke_model(query)
            logger.info(f"✅ Narrative generated for cluster: {cluster_acronym}")
        except Exception as error:
            if "Input is too long" in str(error):
                logger.warning(f"⚠️ Input is too long for cluster {cluster_acronym}. Applying Level 1 contingency...")
                try:
                    filtered_chunks = _filter_chunks_for_contingency(cluster_chunks, level=1)
                    query = f"Using this information:\n{filtered_chunks}\n\nDo the following:\n{cluster_prompt}"
                    narrative = invoke_model(query)
                    logger.info(f"✅ Narrative generated for cluster {cluster_acronym} with Level 1 contingency.")
                except Exception as error_level_1:
                    if "Input is too long" in str(error_level_1):
                        logger.warning(
                            f"⚠️ Still too long for cluster {cluster_acronym}. Applying Level 2 contingency..."
                        )
                        filtered_chunks = _filter_chunks_for_contingency(cluster_chunks, level=2)
                        query = f"Using this information:\n{filtered_chunks}\n\nDo the following:\n{cluster_prompt}"
                        narrative = invoke_model(query)
                        logger.info(
                            f"✅ Narrative generated for cluster {cluster_acronym} with Level 2 contingency."
                        )
                    else:
                        raise error_level_1
            else:
                raise

        logger.info(f"✍️  Rewriting narrative for cluster: {cluster_acronym}...")
        editorial_prompt = generate_cluster_editorial_prompt(indicator, year, cluster_acronym)
        editorial_query = f"Raw evidence draft:\n{narrative}\n\nDo the following:\n{editorial_prompt}"
        final_narrative = invoke_model(editorial_query)
        logger.info(f"✅ Editorial pass completed for cluster: {cluster_acronym}")

        return cluster_acronym, final_narrative
    except Exception as error:
        logger.error(f"❌ Error generating narrative for cluster {cluster_acronym}: {error}")
        return cluster_acronym, f"*Narrative generation failed for {cluster_acronym}: {str(error)}*"


def generate_challenges_report(year):
    """Generate a Challenges and Lessons Learned report."""
    try:
        logger.info(f"🎯 Starting Challenges and Lessons Learned report generation for {year}...")

        challenges_chunks = fetch_challenges_chunks()

        if not challenges_chunks:
            logger.warning(f"⚠️ No challenges data found for year {year}")
            return (
                f"# Challenges and Lessons Learned - {year}\n\n"
                f"No challenges and lessons learned data available for {year}."
            )

        challenges_prompt = generate_challenges_prompt(year)
        query = f"""
            Using this information:\n{challenges_chunks}\n\n
            Do the following:\n{challenges_prompt}
        """

        logger.info("🔄 Generating Challenges and Lessons Learned report...")
        challenges_report = invoke_model(query)

        logger.info("✅ Challenges and Lessons Learned report generation completed successfully.")
        return challenges_report

    except Exception as error:
        logger.error(f"❌ Error generating Challenges and Lessons Learned report: {error}")
        return f"# Challenges and Lessons Learned - {year}\n\nError generating report: {str(error)}"


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
        "IPI 3.x": df[df["indicator_acronym"].str.startswith("IPI 3.")],
    }

    tables = {}

    for group_name, group_df in groups.items():
        indicators = sorted(group_df["indicator_acronym"].unique())
        table_rows = []
        for indicator in indicators:
            ind_df = group_df[group_df["indicator_acronym"] == indicator]
            indicator_title = (
                ind_df["indicator_title"].iloc[0]
                if not ind_df["indicator_title"].isnull().all()
                else indicator
            )

            percent_indicators = ["IPI 2.2", "IPI 3.3"]

            if indicator in percent_indicators:
                end_year_target = ind_df["Milestone expected value"].mean()
                achieved = ind_df["Milestone reported value"].mean()
            else:
                end_year_target = ind_df["Milestone expected value"].sum()
                achieved = ind_df["Milestone reported value"].sum()

            cluster_narratives = ind_df.groupby("cluster_acronym")["Milestone achieved narrative"].apply(
                lambda values: " ".join(values.dropna())
            )
            formatted_narratives = "\n".join(
                [
                    f"{cluster}: {narrative}"
                    for cluster, narrative in cluster_narratives.items()
                    if narrative.strip()
                ]
            )

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
                "Brief overviews": brief_overview,
            })
        tables[group_name] = pd.DataFrame(table_rows)

    return tables


def run_pipeline(indicator, year, insert_data=False):
    try:
        if insert_data:
            client = get_vector_store_client()
            client.recreate_index()
            ingest_tables(ANNUAL_INGEST_TABLES, client=client)
            logger.info("✅ Data insertion completed successfully.")

        total_expected, total_achieved, progress = calculate_summary(indicator, year)
        search_query = generate_search_prompt(indicator, year)

        context, questions = retrieve_context(search_query, indicator, year)
        save_context_to_file(context, "context", indicator, year)

        grouped_context = group_context_by_cluster(context)
        clusters = sorted(grouped_context.keys())

        indicator_title = _get_indicator_title(context, indicator)
        summary_prompt = generate_summary_prompt(
            indicator,
            indicator_title,
            year,
            total_expected,
            total_achieved,
            progress,
        )

        logger.info(f"🚀 Starting parallel generation for {len(clusters)} clusters...")

        def _run_summary():
            return invoke_model(summary_prompt)

        with ThreadPoolExecutor(max_workers=len(clusters) + 1) as executor:
            summary_future = executor.submit(_run_summary)
            cluster_futures = {
                executor.submit(
                    _generate_single_cluster_narrative,
                    cluster,
                    grouped_context[cluster],
                    indicator,
                    year,
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

        accepted_indicators = ["PDO Indicator 1", "PDO Indicator 2", "PDO Indicator 3", "IPI 2.3"]
        if indicator in accepted_indicators:
            target_prompt = generate_target_prompt(indicator)
            query_questions = f"""
                Using this information:\n{questions}\n\n
                Do the following:\n{target_prompt}
                """

            logger.info("☑️  Starting disaggregated targets report generation...")
            targets_report = invoke_model(query_questions)
            generated_report += "\n\n## Disaggregated targets\n" + targets_report

        logger.info("✅ Report generation completed successfully.")
        return generated_report

    except Exception as error:
        logger.error(f"❌ Error in pipeline execution: {error}")

        if "Input is too long" in str(error):
            logger.error("❌ Input is still too long even after applying contingency filters.")
            return (
                f"# Report Generation Error\n\nThe input context for indicator {indicator} "
                f"in year {year} is too long for the model, even after applying data reduction filters."
            )

        return None
