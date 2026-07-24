from unittest.mock import patch

import pytest

from app.text_mining.prms_mining.models import (
    AudioTranscriptionUnavailableError,
    ExtractedPrmsSource,
    PrmsSource,
    PrmsSourceType,
    SourceExtractionError,
)
from app.text_mining.prms_mining.source_extraction import (
    build_sources_from_request,
    extract_free_text_source,
    extract_sources,
)


def test_build_sources_order():
    sources = build_sources_from_request(
        bucket="b",
        keys=["a.pdf", "b.docx"],
        audio_keys=["clip.m4a"],
        text="notes",
    )
    assert [s.source_type for s in sources] == [
        PrmsSourceType.DOCUMENT,
        PrmsSourceType.DOCUMENT,
        PrmsSourceType.AUDIO,
        PrmsSourceType.FREE_TEXT,
    ]
    assert [s.source_index for s in sources] == [0, 1, 2, 3]


def test_free_text_not_formal_evidence():
    source = PrmsSource(
        source_id="source-1",
        source_index=0,
        source_type=PrmsSourceType.FREE_TEXT,
        text="Focus on 2026 outcomes",
    )
    extracted = extract_free_text_source(source)
    assert extracted.eligible_as_formal_evidence is False
    assert extracted.content == "Focus on 2026 outcomes"


def test_worker_ordering_despite_out_of_order_completion():
    def fake_document(source: PrmsSource) -> ExtractedPrmsSource:
        return ExtractedPrmsSource(
            source_id=source.source_id,
            source_index=source.source_index,
            source_type=PrmsSourceType.DOCUMENT,
            content=f"content-{source.source_index}",
            segments=[f"content-{source.source_index}"],
            character_count=10,
            extraction_seconds=0.01 * (3 - source.source_index),
            eligible_as_formal_evidence=True,
        )

    sources = [
        PrmsSource(
            source_id=f"source-{i+1}",
            source_index=i,
            source_type=PrmsSourceType.DOCUMENT,
            bucket_name="b",
            object_key=f"k{i}.pdf",
        )
        for i in range(3)
    ]

    with patch(
        "app.text_mining.prms_mining.source_extraction.extract_document_source",
        side_effect=fake_document,
    ):
        results = extract_sources(sources, max_workers=3)

    assert [r.source_index for r in results] == [0, 1, 2]
    assert [r.content for r in results] == ["content-0", "content-1", "content-2"]


def test_worker_failure_fails_request():
    sources = [
        PrmsSource(
            source_id="source-1",
            source_index=0,
            source_type=PrmsSourceType.DOCUMENT,
            bucket_name="b",
            object_key="ok.pdf",
        ),
        PrmsSource(
            source_id="source-2",
            source_index=1,
            source_type=PrmsSourceType.DOCUMENT,
            bucket_name="b",
            object_key="bad.pdf",
        ),
    ]

    def boom(source: PrmsSource):
        if source.source_index == 1:
            raise SourceExtractionError("parse failed", source_id=source.source_id)
        return ExtractedPrmsSource(
            source_id=source.source_id,
            source_index=source.source_index,
            source_type=PrmsSourceType.DOCUMENT,
            content="ok",
            segments=["ok"],
            character_count=2,
            extraction_seconds=0.01,
            eligible_as_formal_evidence=True,
        )

    with patch(
        "app.text_mining.prms_mining.source_extraction.extract_document_source",
        side_effect=boom,
    ):
        with pytest.raises(SourceExtractionError):
            extract_sources(sources, max_workers=2)


def test_audio_unavailable():
    from app.text_mining.prms_mining.audio_transcriber import UnavailableAudioTranscriber

    with pytest.raises(AudioTranscriptionUnavailableError):
        UnavailableAudioTranscriber().transcribe(b"abc", file_name="a.m4a")
