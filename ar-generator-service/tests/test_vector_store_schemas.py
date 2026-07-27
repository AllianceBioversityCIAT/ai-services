import json

from app.vector_store.schemas import build_filterable_metadata, build_vector_record, chunk_from_vector_metadata


def test_build_filterable_metadata_sets_has_doi():
    row = {"indicator_acronym": "IPI 1.3", "year": 2025}
    chunk = {
        "table_type": "deliverables",
        "doi": "https://hdl.handle.net/10568/178537",
        "cluster_role": "Owner",
    }

    metadata = build_filterable_metadata(row, "vw_ai_deliverables", chunk)

    assert metadata["source_table"] == "vw_ai_deliverables"
    assert metadata["indicator_acronym"] == "IPI 1.3"
    assert metadata["year"] == "2025"
    assert metadata["has_doi"] is True


def test_build_vector_record_roundtrip():
    row = {"indicator_acronym": "IPI 1.3", "year": 2025}
    chunk = {"table_type": "contributions", "indicator_acronym": "IPI 1.3", "year": 2025}
    embedding = [0.1, 0.2, 0.3]

    record = build_vector_record("vw_ai_project_contribution", 0, row, chunk, embedding)

    assert record["key"] == "vw_ai_project_contribution-0"
    assert record["data"]["float32"] == embedding

    restored = chunk_from_vector_metadata(record["metadata"])
    assert restored == chunk
    assert json.loads(record["metadata"]["chunk_json"]) == chunk
