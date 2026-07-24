from unittest.mock import patch

from app.text_mining.prms_mining.corpus import (
    build_context_excerpts,
    estimate_tokens,
    fit_blocks_to_token_budget,
)
from app.text_mining.prms_mining.models import ExtractedPrmsSource, PrmsSourceType


def _source(
    source_id: str,
    source_type: PrmsSourceType,
    content: str,
    source_index: int = 0,
) -> ExtractedPrmsSource:
    return ExtractedPrmsSource(
        source_id=source_id,
        source_index=source_index,
        source_type=source_type,
        content=content,
        segments=[content],
        character_count=len(content),
        extraction_seconds=0.01,
        file_name=f"{source_id}.txt",
        eligible_as_formal_evidence=source_type == PrmsSourceType.DOCUMENT,
    )


def test_build_context_includes_text_audio_and_small_docs_without_retrieval():
    sources = [
        _source("text", PrmsSourceType.FREE_TEXT, "user supplied evidence", 0),
        _source("audio", PrmsSourceType.AUDIO, "audio transcript evidence", 1),
        _source("doc", PrmsSourceType.DOCUMENT, "short document evidence", 2),
    ]

    with patch("app.text_mining.prms_mining.corpus.store_and_retrieve_chunks") as mock_retrieve:
        result = build_context_excerpts(sources, request_id="req", token_budget=10_000)

    assert "user supplied evidence" in result.excerpts
    assert "audio transcript evidence" in result.excerpts
    assert "short document evidence" in result.excerpts
    assert result.chunks_processed == 0
    assert result.trimmed is False
    mock_retrieve.assert_not_called()


def test_build_context_retrieves_large_documents_per_source():
    sources = [
        _source("doc-1", PrmsSourceType.DOCUMENT, "a" * 100, 0),
        _source("doc-2", PrmsSourceType.DOCUMENT, "b" * 100, 1),
    ]

    with (
        patch("app.text_mining.prms_mining.corpus.PRMS_FULL_SOURCE_MAX_CHARS", 10),
        patch(
            "app.text_mining.prms_mining.corpus.store_and_retrieve_chunks",
            side_effect=[
                (["retrieved from doc 1"], "prms-retrieval-v1"),
                (["retrieved from doc 2"], "prms-retrieval-v1"),
            ],
        ) as mock_retrieve,
    ):
        result = build_context_excerpts(
            sources,
            request_id="req",
            token_budget=10_000,
            top_k_per_source=3,
        )

    assert "retrieved from doc 1" in result.excerpts
    assert "retrieved from doc 2" in result.excerpts
    assert result.chunks_processed == 2
    assert mock_retrieve.call_count == 2
    assert all(call.kwargs["top_k"] == 3 for call in mock_retrieve.call_args_list)


def test_fit_blocks_to_token_budget_trims_conservatively():
    blocks = ["a" * 300, "b" * 300]

    trimmed_blocks, was_trimmed = fit_blocks_to_token_budget(blocks, token_budget=100)
    excerpts = "\n\n---\n\n".join(trimmed_blocks)

    assert was_trimmed is True
    assert estimate_tokens(excerpts) <= 100
    assert len(excerpts) < len("\n\n---\n\n".join(blocks))
