"""Bounded parallel extraction of PRMS document and audio sources."""

from __future__ import annotations

import time
from io import BytesIO
from typing import Callable
from PyPDF2 import PdfReader
from botocore.exceptions import ClientError
from app.utils.logger.logger_util import get_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.utils.s3.s3_util import _process_file_content, s3_client
from app.text_mining.prms_mining.audio_transcriber import get_audio_transcriber

from app.text_mining.prms_mining.models import (
    AudioTranscriptionUnavailableError,
    ExtractedPrmsSource,
    PrmsSource,
    PrmsSourceType,
    SourceDownloadError,
    SourceExtractionError,
    SourceLimitExceededError,
    UnsupportedSourceTypeError,
)
from app.utils.config.config_util import (
    PRMS_EXTRACTION_MAX_WORKERS,
    PRMS_MAX_FILE_BYTES,
    PRMS_MAX_PDF_PAGES,
    PRMS_MAX_SOURCES,
    PRMS_MAX_TEXT_CHARS,
    PRMS_SUPPORTED_AUDIO_EXTENSIONS,
    PRMS_SUPPORTED_DOCUMENT_EXTENSIONS,
)


logger = get_logger()


def _mb(value: int | float) -> str:
    return f"{value / 1_000_000:.1f} MB"


def _source_label(source: PrmsSource) -> str:
    return source.file_name or (source.object_key.split("/")[-1] if source.object_key else "this source")


def _extension(object_key: str | None, file_name: str | None = None) -> str:
    name = file_name or object_key or ""
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()


def _head_s3_object(bucket: str, key: str, source_id: str) -> int:
    """Return ContentLength and enforce per-file byte limit."""
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        content_length = int(response.get("ContentLength") or 0)
        if content_length > PRMS_MAX_FILE_BYTES:
            raise SourceLimitExceededError(
                "The file is too large to process. "
                f"Maximum allowed size is {_mb(PRMS_MAX_FILE_BYTES)}; "
                f"this file is {_mb(content_length)}.",
                source_id=source_id,
            )
        return content_length
    except SourceLimitExceededError:
        raise
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"NoSuchKey", "404", "NotFound", "404 Not Found"}:
            raise SourceDownloadError(
                "One of the provided files could not be found in storage.",
                source_id=source_id,
            ) from exc
        raise SourceDownloadError(
            "The service could not read the file metadata from storage.",
            source_id=source_id,
        ) from exc
    except Exception as exc:
        raise SourceDownloadError(
            f"The service could not read the file metadata from storage: {exc}",
            source_id=source_id,
        ) from exc


def _download_s3_object(bucket: str, key: str, source_id: str) -> bytes:
    try:
        _head_s3_object(bucket, key, source_id)
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
    except (SourceLimitExceededError, SourceDownloadError):
        raise
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"NoSuchKey", "404", "NotFound"}:
            raise SourceDownloadError(
                "One of the provided files could not be found in storage.",
                source_id=source_id,
            ) from exc
        raise SourceDownloadError(
            "The service could not download one of the provided files from storage.",
            source_id=source_id,
        ) from exc
    except Exception as exc:
        raise SourceDownloadError(
            f"The service could not download one of the provided files from storage: {exc}",
            source_id=source_id,
        ) from exc


def _segments_from_content(content) -> tuple[str, list[str], int | None]:
    """Normalize parser output into plain text, segments, and optional page count."""
    if isinstance(content, dict) and content.get("type") == "excel":
        segments = list(content.get("chunks") or [])
        joined = "\n".join(segments)
        return joined, segments, None
    if not isinstance(content, str):
        content = str(content)
    return content, [content] if content.strip() else [], None


def extract_document_source(source: PrmsSource) -> ExtractedPrmsSource:
    start = time.time()
    ext = _extension(source.object_key, source.file_name)
    label = _source_label(source)
    if ext == "doc":
        raise UnsupportedSourceTypeError(
            f"The file '{label}' uses the legacy .doc format, which is not supported. "
            "Please upload a .docx, .pdf, .txt, .xls, .xlsx, or .pptx file.",
            source_id=source.source_id,
        )
    if ext not in PRMS_SUPPORTED_DOCUMENT_EXTENSIONS:
        raise UnsupportedSourceTypeError(
            f"The file '{label}' has an unsupported document type '.{ext}'. "
            "Supported document types are: pdf, docx, txt, xls, xlsx, and pptx.",
            source_id=source.source_id,
        )
    if not source.bucket_name or not source.object_key:
        raise SourceExtractionError(
            "A document source is missing its storage location.",
            source_id=source.source_id,
        )

    raw = _download_s3_object(source.bucket_name, source.object_key, source.source_id)
    page_count = None
    if ext == "pdf":
        try:
            page_count = len(PdfReader(BytesIO(raw)).pages)
        except Exception:
            page_count = None
        if page_count is not None and page_count > PRMS_MAX_PDF_PAGES:
            raise SourceLimitExceededError(
                f"The PDF '{label}' has too many pages to process. "
                f"Maximum allowed pages: {PRMS_MAX_PDF_PAGES}; this file has {page_count}.",
                source_id=source.source_id,
            )

    try:
        parsed = _process_file_content(ext, raw)
        text, segments, _ = _segments_from_content(parsed)
    except ValueError as exc:
        raise UnsupportedSourceTypeError(str(exc), source_id=source.source_id) from exc
    except Exception as exc:
        raise SourceExtractionError(
            f"The file '{label}' could not be parsed as readable text.",
            source_id=source.source_id,
        ) from exc

    if not text.strip():
        raise SourceExtractionError(
            f"The file '{label}' did not contain readable text.",
            source_id=source.source_id,
        )

    elapsed = time.time() - start
    return ExtractedPrmsSource(
        source_id=source.source_id,
        source_index=source.source_index,
        source_type=PrmsSourceType.DOCUMENT,
        content=text,
        segments=segments,
        page_count=page_count,
        character_count=len(text),
        extraction_seconds=elapsed,
        file_name=source.file_name or (source.object_key.split("/")[-1] if source.object_key else None),
        eligible_as_formal_evidence=True,
    )


def extract_audio_source(source: PrmsSource) -> ExtractedPrmsSource:
    start = time.time()
    ext = _extension(source.object_key, source.file_name)
    label = _source_label(source)
    if ext not in PRMS_SUPPORTED_AUDIO_EXTENSIONS:
        raise UnsupportedSourceTypeError(
            f"The audio file '{label}' has an unsupported type '.{ext}'. "
            "Supported audio types are: mp3, wav, m4a, ogg, flac, and webm.",
            source_id=source.source_id,
        )
    if not source.bucket_name or not source.object_key:
        raise SourceExtractionError(
            "An audio source is missing its storage location.",
            source_id=source.source_id,
        )

    # Size check only — Amazon Transcribe reads the object from S3 directly.
    _head_s3_object(source.bucket_name, source.object_key, source.source_id)

    transcriber = get_audio_transcriber()
    try:
        transcript = transcriber.transcribe(
            None,
            file_name=source.file_name or source.object_key,
            bucket_name=source.bucket_name,
            object_key=source.object_key,
        )
    except (AudioTranscriptionUnavailableError, SourceLimitExceededError, SourceExtractionError):
        raise
    except Exception as exc:
        raise SourceExtractionError(
            f"The audio file '{label}' could not be transcribed.",
            source_id=source.source_id,
        ) from exc

    if not transcript or not transcript.strip():
        raise SourceExtractionError(
            f"The audio file '{label}' did not produce a readable transcript.",
            source_id=source.source_id,
        )

    elapsed = time.time() - start
    return ExtractedPrmsSource(
        source_id=source.source_id,
        source_index=source.source_index,
        source_type=PrmsSourceType.AUDIO,
        content=transcript,
        segments=[transcript],
        page_count=None,
        character_count=len(transcript),
        extraction_seconds=elapsed,
        file_name=source.file_name or (source.object_key.split("/")[-1] if source.object_key else None),
        eligible_as_formal_evidence=False,
    )


def extract_free_text_source(source: PrmsSource) -> ExtractedPrmsSource:
    start = time.time()
    text = (source.text or "").strip()
    if not text:
        raise SourceExtractionError(
            "The free-text input is empty.",
            source_id=source.source_id,
        )
    if len(text) > PRMS_MAX_TEXT_CHARS:
        raise SourceLimitExceededError(
            "The free-text input is too long to process. "
            f"Maximum allowed characters: {PRMS_MAX_TEXT_CHARS:,}; "
            f"received: {len(text):,}.",
            source_id=source.source_id,
        )
    elapsed = time.time() - start
    return ExtractedPrmsSource(
        source_id=source.source_id,
        source_index=source.source_index,
        source_type=PrmsSourceType.FREE_TEXT,
        content=text,
        segments=[text],
        page_count=None,
        character_count=len(text),
        extraction_seconds=elapsed,
        file_name=None,
        eligible_as_formal_evidence=False,
    )


def _adapter_for(source_type: PrmsSourceType) -> Callable[[PrmsSource], ExtractedPrmsSource]:
    """Resolve adapters at call time so tests can patch extract_* functions."""
    if source_type == PrmsSourceType.DOCUMENT:
        return extract_document_source
    if source_type == PrmsSourceType.AUDIO:
        return extract_audio_source
    if source_type == PrmsSourceType.FREE_TEXT:
        return extract_free_text_source
    raise SourceExtractionError(f"No adapter for source type {source_type}")


def extract_sources(
    sources: list[PrmsSource],
    max_workers: int | None = None,
) -> list[ExtractedPrmsSource]:
    """
    Extract all sources. Free text is handled inline; documents/audio use a bounded pool.
    Fail-all-or-nothing: any worker failure raises and cancels outstanding futures.
    """
    if not sources:
        raise SourceExtractionError("No sources to extract")

    if len(sources) > PRMS_MAX_SOURCES:
        raise SourceLimitExceededError(
            "Too many sources were provided for one request. "
            f"Maximum allowed sources: {PRMS_MAX_SOURCES}; received: {len(sources)}."
        )

    free_text_results: list[ExtractedPrmsSource] = []
    for source in sources:
        if source.source_type == PrmsSourceType.FREE_TEXT:
            free_text_results.append(extract_free_text_source(source))

    worker_sources = [
        s for s in sources if s.source_type != PrmsSourceType.FREE_TEXT
    ]
    worker_results: list[ExtractedPrmsSource] = []

    if worker_sources:
        configured = max_workers if max_workers is not None else PRMS_EXTRACTION_MAX_WORKERS
        if configured <= 0:
            raise ValueError("max_workers must be > 0")
        pool_size = min(configured, len(worker_sources))
        logger.info(
            "📥 PRMS source extraction: %s worker source(s), max_workers=%s",
            len(worker_sources),
            pool_size,
        )

        with ThreadPoolExecutor(max_workers=pool_size) as executor:
            future_map = {
                executor.submit(_adapter_for(source.source_type), source): source
                for source in worker_sources
            }
            try:
                for future in as_completed(future_map):
                    try:
                        worker_results.append(future.result())
                    except Exception:
                        for pending in future_map:
                            pending.cancel()
                        raise
            except Exception:
                raise

    combined = free_text_results + worker_results
    combined.sort(key=lambda item: item.source_index)
    logger.info(
        "📥 PRMS source extraction complete: %s source(s)",
        len(combined),
    )
    return combined


def build_sources_from_request(
    *,
    bucket: str | None,
    keys: list[str] | None,
    audio_keys: list[str] | None,
    text: str | None,
) -> list[PrmsSource]:
    """Build typed source descriptors from MCP arguments."""
    sources: list[PrmsSource] = []
    index = 0

    for key in keys or []:
        if not key or not str(key).strip():
            continue
        key = str(key).strip()
        sources.append(
            PrmsSource(
                source_id=f"source-{index + 1}",
                source_index=index,
                source_type=PrmsSourceType.DOCUMENT,
                bucket_name=bucket,
                object_key=key,
                file_name=key.split("/")[-1],
            )
        )
        index += 1

    for key in audio_keys or []:
        if not key or not str(key).strip():
            continue
        key = str(key).strip()
        sources.append(
            PrmsSource(
                source_id=f"source-{index + 1}",
                source_index=index,
                source_type=PrmsSourceType.AUDIO,
                bucket_name=bucket,
                object_key=key,
                file_name=key.split("/")[-1],
            )
        )
        index += 1

    normalized_text = (text or "").strip()
    if normalized_text:
        sources.append(
            PrmsSource(
                source_id=f"source-{index + 1}",
                source_index=index,
                source_type=PrmsSourceType.FREE_TEXT,
                text=normalized_text,
            )
        )

    return sources
