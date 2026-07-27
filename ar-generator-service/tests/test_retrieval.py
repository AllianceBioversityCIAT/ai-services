import pytest

from app.retrieval.context_merger import merge_knn_and_doi
from app.retrieval.post_filters import (
    filter_annual_knn_chunks,
    filter_midyear_chunks,
    filter_questions_chunks,
)


def test_filter_midyear_chunks_excludes_shared():
    chunks = [
        {"table_type": "deliverables", "cluster_role": "Shared"},
        {"table_type": "deliverables", "cluster_role": "Owner"},
        {"table_type": "innovations", "cluster_role": "Shared"},
        {"table_type": "contributions", "cluster_role": "Shared"},
    ]

    filtered = filter_midyear_chunks(chunks)

    assert filtered == [
        {"table_type": "deliverables", "cluster_role": "Owner"},
        {"table_type": "contributions", "cluster_role": "Shared"},
    ]


def test_filter_annual_knn_chunks_excludes_cancelled_and_awpb():
    chunks = [
        {"table_type": "deliverables", "cluster_role": "Owner", "status": "Cancelled"},
        {"table_type": "contributions", "phase_name": "AWPB"},
        {"table_type": "contributions", "phase_name": "AR"},
    ]

    filtered = filter_annual_knn_chunks(chunks)

    assert filtered == [{"table_type": "contributions", "phase_name": "AR"}]


def test_filter_questions_chunks_excludes_pdo_prefix():
    chunks = [
        {
            "table_type": "questions",
            "phase_name": "AR",
            "indicator_acronym": "PDO Indicator 1",
            "question": "2.0 Something",
        },
        {
            "table_type": "questions",
            "phase_name": "AR",
            "indicator_acronym": "PDO Indicator 1",
            "question": "1.0 Something",
        },
    ]

    filtered = filter_questions_chunks(chunks)

    assert filtered == [
        {
            "table_type": "questions",
            "phase_name": "AR",
            "indicator_acronym": "PDO Indicator 1",
            "question": "1.0 Something",
        }
    ]


def test_merge_knn_and_doi_deduplicates_doi():
    knn_chunks = [
        {"doi": "https://example.org/1", "cluster_acronym": "WA", "indicator_acronym": "IPI 1.3"},
        {"table_type": "contributions"},
    ]
    doi_chunks = [
        {"doi": "https://example.org/1", "cluster_acronym": "WA", "indicator_acronym": "IPI 1.3"},
    ]

    merged = merge_knn_and_doi(knn_chunks, doi_chunks)

    assert len(merged) == 2
    assert merged[0]["doi"] == "https://example.org/1"
    assert merged[1]["table_type"] == "contributions"
