import pandas as pd

from app.utils.logger.logger_util import get_logger
from app.vector_store.schemas import rows_to_chunks
from db_conn.sql_connection import load_data

logger = get_logger()


def _normalize_year(value) -> str:
    return str(value)


def _match_indicator(series: pd.Series, indicator: str) -> pd.Series:
    return series == indicator


def _match_year(series: pd.Series, year) -> pd.Series:
    return series.astype(str) == _normalize_year(year)


def _rows_to_chunks_from_df(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    return rows_to_chunks(df.to_dict(orient="records"))


def fetch_doi_chunks(indicator: str, year) -> list[dict]:
    try:
        df = load_data("vw_ai_deliverables")
        if df.empty:
            return []

        filtered = df[
            _match_indicator(df["indicator_acronym"], indicator)
            & _match_year(df["year"], year)
            & df["doi"].notna()
            & (df["doi"].astype(str).str.strip() != "")
        ]
        return _rows_to_chunks_from_df(filtered)
    except Exception as error:
        logger.error(f"❌ Error fetching DOI chunks: {error}")
        return []


def fetch_questions_chunks(indicator: str, year) -> list[dict]:
    try:
        chunks = []

        for table_name in ("vw_ai_questions", "vw_ai_project_contribution"):
            df = load_data(table_name)
            if df.empty:
                continue

            filtered = df[
                _match_indicator(df["indicator_acronym"], indicator)
                & _match_year(df["year"], year)
            ]
            chunks.extend(_rows_to_chunks_from_df(filtered))

        return chunks
    except Exception as error:
        logger.error(f"❌ Error fetching questions chunks: {error}")
        return []


def fetch_challenges_chunks() -> list[dict]:
    try:
        df = load_data("vw_ai_challenges")
        return _rows_to_chunks_from_df(df)
    except Exception as error:
        logger.error(f"❌ Error fetching challenges chunks: {error}")
        return []
