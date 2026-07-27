import json
import pandas as pd
from typing import Any


NON_FILTERABLE_METADATA_KEYS = ["chunk_json"]

FILTERABLE_FIELDS = (
    "source_table",
    "indicator_acronym",
    "year",
    "table_type",
    "cluster_role",
    "status",
    "phase_name",
    "has_doi",
)


def row_to_chunk(row: dict) -> dict:
    return {k: v for k, v in row.items() if pd.notnull(v) and v != ""}


def rows_to_chunks(rows: list[dict]) -> list[dict]:
    return [row_to_chunk(row) for row in rows]


def _normalize_metadata_value(value: Any) -> str | bool:
    if isinstance(value, bool):
        return value
    return str(value)


def build_filterable_metadata(row: dict, table_name: str, chunk: dict) -> dict:
    metadata = {
        "source_table": table_name,
        "year": _normalize_metadata_value(row.get("year", "")),
    }

    indicator = row.get("indicator_acronym")
    if indicator is not None and pd.notnull(indicator) and indicator != "":
        metadata["indicator_acronym"] = _normalize_metadata_value(indicator)

    for field in ("table_type", "cluster_role", "status", "phase_name"):
        value = chunk.get(field)
        if value is not None and value != "":
            metadata[field] = _normalize_metadata_value(value)

    doi = chunk.get("doi")
    if doi is not None and doi != "":
        metadata["has_doi"] = True

    return metadata


def build_vector_record(
    table_name: str,
    row_index: int,
    row: dict,
    chunk: dict,
    embedding: list[float],
) -> dict:
    if not embedding:
        raise ValueError(f"Missing embedding for vector {table_name}-{row_index}")

    metadata = build_filterable_metadata(row, table_name, chunk)
    metadata["chunk_json"] = json.dumps(chunk, ensure_ascii=False, default=str)

    return {
        "key": f"{table_name}-{row_index}",
        "data": {"float32": [float(value) for value in embedding]},
        "metadata": metadata,
    }


def chunk_from_vector_metadata(metadata: dict | None) -> dict | None:
    if not metadata:
        return None

    chunk_json = metadata.get("chunk_json")
    if not chunk_json:
        return None

    return json.loads(chunk_json)
