"""HTTP request normalization helpers for PRMS multisource mining."""

from __future__ import annotations

import ast
import json
from app.llm.prms_mining.models import EmptySourceSetError
from app.utils.config.config_util import PRMS_SUPPORTED_AUDIO_EXTENSIONS, PRMS_SUPPORTED_DOCUMENT_EXTENSIONS


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or not str(value).strip():
            continue
        key = str(value).strip()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1].strip()
    return value


def coerce_form_string_list(values: list[str] | None) -> list[str]:
    """
    Flatten form-data list fields.

    Swagger UI / some clients send array fields as a single JSON string, e.g.
    '["path/to/file.pdf"]', which FastAPI then treats as one list item. That
    pollutes the extension ('.pdf\\\"]') and breaks allowlists.
    """
    if not values:
        return []

    flattened: list[str] = []
    for item in values:
        if item is None:
            continue
        raw = str(item).strip()
        if not raw:
            continue

        if raw.startswith("[") and raw.endswith("]"):
            parsed = None
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(raw)
                except (SyntaxError, ValueError):
                    parsed = None
            if isinstance(parsed, list):
                for part in parsed:
                    if part is None:
                        continue
                    cleaned = _strip_wrapping_quotes(str(part).strip())
                    if cleaned:
                        flattened.append(cleaned)
                continue

        flattened.append(_strip_wrapping_quotes(raw))

    return flattened


def normalize_prms_sources(
    *,
    keys: list[str] | None = None,
    audio_keys: list[str] | None = None,
    text: str | None = None,
    file_count: int = 0,
) -> tuple[list[str], list[str], str | None]:
    """
    Normalize and dedupe PRMS source fields.
    Returns (document_keys, audio_keys, normalized_text).
    """
    document_keys = dedupe_preserve_order(coerce_form_string_list(keys))
    audio = dedupe_preserve_order(coerce_form_string_list(audio_keys))
    normalized_text = (text or "").strip() or None

    if not document_keys and file_count == 0 and not audio and not normalized_text:
        raise EmptySourceSetError(
            "Please provide at least one source to process: a document, an audio file, or free text."
        )

    return document_keys, audio, normalized_text


def extension_of(name: str) -> str:
    if not name or "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()


def assert_document_extension(filename: str) -> None:
    from app.llm.prms_mining.models import UnsupportedSourceTypeError

    ext = extension_of(filename)
    if ext == "doc":
        raise UnsupportedSourceTypeError(
            f"The file '{filename}' uses the legacy .doc format, which is not supported. "
            "Please upload a .docx, .pdf, .txt, .xls, .xlsx, or .pptx file."
        )
    if ext not in PRMS_SUPPORTED_DOCUMENT_EXTENSIONS:
        raise UnsupportedSourceTypeError(
            f"The file '{filename}' has an unsupported document type '.{ext}'. "
            "Supported document types are: pdf, docx, txt, xls, xlsx, and pptx."
        )


def assert_audio_extension(key: str) -> None:
    from app.llm.prms_mining.models import UnsupportedSourceTypeError

    ext = extension_of(key)
    if ext not in PRMS_SUPPORTED_AUDIO_EXTENSIONS:
        raise UnsupportedSourceTypeError(
            f"The audio file '{key}' has an unsupported type '.{ext}'. "
            "Supported audio types are: mp3, wav, m4a, ogg, flac, and webm."
        )
