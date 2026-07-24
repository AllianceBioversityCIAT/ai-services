import pytest

from app.text_mining.prms_mining.models import EmptySourceSetError, UnsupportedSourceTypeError
from app.text_mining.prms_mining.request_normalization import (
    assert_audio_extension,
    assert_document_extension,
    dedupe_preserve_order,
    normalize_prms_sources,
)


def test_dedupe_preserve_order():
    assert dedupe_preserve_order(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_normalize_keys_and_audio():
    keys, audio, text = normalize_prms_sources(
        keys=["k1", "k1", "k2"],
        audio_keys=["a1"],
        text="  hello  ",
    )
    assert keys == ["k1", "k2"]
    assert audio == ["a1"]
    assert text == "hello"


def test_normalize_json_array_form_value_from_swagger():
    """Swagger often sends list fields as one JSON string."""
    keys, audio, text = normalize_prms_sources(
        keys=['["prms/text-mining/files/test/report.pdf"]'],
        audio_keys=['["prms/text-mining/audio/note.m4a"]'],
        text=None,
    )
    assert keys == ["prms/text-mining/files/test/report.pdf"]
    assert audio == ["prms/text-mining/audio/note.m4a"]
    assert text is None
    assert_document_extension(keys[0])
    assert_audio_extension(audio[0])


def test_normalize_json_array_with_multiple_keys():
    keys, audio, _ = normalize_prms_sources(
        keys=['["a.pdf", "b.docx"]'],
    )
    assert keys == ["a.pdf", "b.docx"]
    assert audio == []


def test_normalize_empty_raises():
    with pytest.raises(EmptySourceSetError):
        normalize_prms_sources(keys=None, audio_keys=None, text="   ")


def test_free_text_only_ok():
    keys, audio, text = normalize_prms_sources(text="context only")
    assert keys == []
    assert audio == []
    assert text == "context only"


def test_document_extension_rejects_doc():
    with pytest.raises(UnsupportedSourceTypeError):
        assert_document_extension("legacy.doc")


def test_document_extension_accepts_pdf():
    assert_document_extension("report.pdf")


def test_audio_extension_reject():
    with pytest.raises(UnsupportedSourceTypeError):
        assert_audio_extension("clip.xyz")
