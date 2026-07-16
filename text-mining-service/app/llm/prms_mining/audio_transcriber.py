"""Speech-to-text adapters for PRMS audio sources."""

from __future__ import annotations

import json
import ssl
import time
import uuid
import certifi
from typing import Any
from urllib.request import urlopen
from abc import ABC, abstractmethod
from app.utils.logger.logger_util import get_logger
from app.llm.providers.transcribe_client import get_transcribe_client
from app.llm.prms_mining.models import AudioTranscriptionUnavailableError, SourceExtractionError, SourceLimitExceededError
from app.utils.config.config_util import PRMS_AUDIO_TRANSCRIBER, PRMS_MAX_AUDIO_SECONDS, PRMS_TRANSCRIBE_LANGUAGE_CODE, PRMS_TRANSCRIBE_LANGUAGE_OPTIONS, PRMS_TRANSCRIBE_POLL_INTERVAL_SECONDS, PRMS_TRANSCRIBE_TIMEOUT_SECONDS


logger = get_logger()

_MEDIA_FORMAT_BY_EXTENSION = {
    "mp3": "mp3",
    "wav": "wav",
    "flac": "flac",
    "ogg": "ogg",
    "amr": "amr",
    "webm": "webm",
    "m4a": "m4a",
    "mp4": "mp4",
}


class AudioTranscriber(ABC):
    @abstractmethod
    def transcribe(
        self,
        audio_bytes: bytes | None = None,
        file_name: str | None = None,
        *,
        bucket_name: str | None = None,
        object_key: str | None = None,
    ) -> str:
        raise NotImplementedError


class UnavailableAudioTranscriber(AudioTranscriber):
    """Fail-closed adapter used when no provider is configured."""

    def transcribe(
        self,
        audio_bytes: bytes | None = None,
        file_name: str | None = None,
        *,
        bucket_name: str | None = None,
        object_key: str | None = None,
    ) -> str:
        raise AudioTranscriptionUnavailableError(
            "Audio transcription provider is not configured "
            "(set PRMS_AUDIO_TRANSCRIBER=amazon_transcribe to enable Amazon Transcribe)"
        )


class AmazonTranscribeTranscriber(AudioTranscriber):
    """
    Amazon Transcribe batch adapter.

    Reads audio directly from S3 (preferred) via MediaFileUri, polls until complete,
    and returns the plain transcript text.
    """

    def __init__(self, transcribe_client: Any | None = None):
        self._client = transcribe_client or get_transcribe_client()

    def transcribe(
        self,
        audio_bytes: bytes | None = None,
        file_name: str | None = None,
        *,
        bucket_name: str | None = None,
        object_key: str | None = None,
    ) -> str:
        if not bucket_name or not object_key:
            raise SourceExtractionError(
                "Amazon Transcribe requires bucket_name and object_key for S3 media"
            )

        media_format = self._media_format(object_key, file_name)
        job_name = f"prms-{uuid.uuid4().hex}"
        media_uri = f"s3://{bucket_name}/{object_key}"

        start_args: dict[str, Any] = {
            "TranscriptionJobName": job_name,
            "Media": {"MediaFileUri": media_uri},
            "MediaFormat": media_format,
        }
        language_code = (PRMS_TRANSCRIBE_LANGUAGE_CODE or "").strip()
        if language_code:
            start_args["LanguageCode"] = language_code
        else:
            start_args["IdentifyLanguage"] = True
            if PRMS_TRANSCRIBE_LANGUAGE_OPTIONS:
                start_args["LanguageOptions"] = list(PRMS_TRANSCRIBE_LANGUAGE_OPTIONS)

        logger.info(
            "Starting Amazon Transcribe job=%s format=%s uri=s3://%s/%s",
            job_name,
            media_format,
            bucket_name,
            object_key.split("/")[-1],
        )

        try:
            self._client.start_transcription_job(**start_args)
            transcript_uri = self._wait_for_transcript_uri(job_name)
            transcript_payload = self._fetch_transcript_payload(transcript_uri)
            transcript = self._extract_transcript_text(transcript_payload)
            self._enforce_max_duration(transcript_payload)
            return transcript
        except (AudioTranscriptionUnavailableError, SourceLimitExceededError, SourceExtractionError):
            raise
        except Exception as exc:
            message = str(exc)
            if "languageCode" in message or "LanguageOptions" in message:
                raise SourceExtractionError(
                    "Audio transcription failed because of an invalid language setting. "
                    "Leave the language code empty for auto-detect, or set a valid "
                    "Amazon Transcribe language code (for example es-ES or en-US)."
                ) from exc
            raise SourceExtractionError(
                f"Audio transcription failed for '{object_key.split('/')[-1]}'."
            ) from exc
        finally:
            self._cleanup_job(job_name)

    def _media_format(self, object_key: str, file_name: str | None) -> str:
        name = file_name or object_key
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        media_format = _MEDIA_FORMAT_BY_EXTENSION.get(ext)
        if not media_format:
            raise SourceExtractionError(
                f"Amazon Transcribe does not support media extension '.{ext}'"
            )
        return media_format

    def _wait_for_transcript_uri(self, job_name: str) -> str:
        deadline = time.time() + PRMS_TRANSCRIBE_TIMEOUT_SECONDS
        while time.time() < deadline:
            response = self._client.get_transcription_job(TranscriptionJobName=job_name)
            job = response["TranscriptionJob"]
            status = job["TranscriptionJobStatus"]
            if status == "COMPLETED":
                uri = job.get("Transcript", {}).get("TranscriptFileUri")
                if not uri:
                    raise SourceExtractionError(
                        f"Amazon Transcribe job {job_name} completed without TranscriptFileUri"
                    )
                return uri
            if status == "FAILED":
                reason = job.get("FailureReason") or "unknown reason"
                raise SourceExtractionError(
                    f"Amazon Transcribe job {job_name} failed: {reason}"
                )
            time.sleep(PRMS_TRANSCRIBE_POLL_INTERVAL_SECONDS)

        raise SourceExtractionError(
            f"Amazon Transcribe job {job_name} timed out after "
            f"{PRMS_TRANSCRIBE_TIMEOUT_SECONDS}s"
        )

    def _fetch_transcript_payload(self, transcript_uri: str) -> dict[str, Any]:
        # TranscriptFileUri is a temporary HTTPS URL; no AWS credentials required.
        # Use certifi CA bundle so local macOS/venv Python can verify AWS TLS.
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(  # nosec B310 - AWS-signed HTTPS URL from Transcribe
            transcript_uri, timeout=60, context=ssl_context
        ) as response:
            return json.loads(response.read().decode("utf-8"))

    def _extract_transcript_text(self, payload: dict[str, Any]) -> str:
        results = payload.get("results") or {}
        transcripts = results.get("transcripts") or []
        if not transcripts:
            return ""
        text = (transcripts[0].get("transcript") or "").strip()
        return text

    def _enforce_max_duration(self, payload: dict[str, Any]) -> None:
        if PRMS_MAX_AUDIO_SECONDS is None:
            return
        duration = self._duration_seconds(payload)
        if duration is not None and duration > PRMS_MAX_AUDIO_SECONDS:
            raise SourceLimitExceededError(
                "The audio file is too long to process. "
                f"Maximum allowed duration: {PRMS_MAX_AUDIO_SECONDS // 60} min "
                f"{PRMS_MAX_AUDIO_SECONDS % 60} sec; "
                f"this audio is {int(duration) // 60} min {int(duration) % 60} sec."
            )

    def _duration_seconds(self, payload: dict[str, Any]) -> float | None:
        items = (payload.get("results") or {}).get("items") or []
        end_times: list[float] = []
        for item in items:
            raw = item.get("end_time")
            if raw is None:
                continue
            try:
                end_times.append(float(raw))
            except (TypeError, ValueError):
                continue
        if not end_times:
            return None
        return max(end_times)

    def _cleanup_job(self, job_name: str) -> None:
        try:
            self._client.delete_transcription_job(TranscriptionJobName=job_name)
        except Exception as cleanup_exc:
            logger.debug("Could not delete Transcribe job %s: %s", job_name, cleanup_exc)


def get_audio_transcriber() -> AudioTranscriber:
    provider = (PRMS_AUDIO_TRANSCRIBER or "").strip().lower()
    if not provider:
        logger.info("PRMS audio transcriber unavailable (PRMS_AUDIO_TRANSCRIBER unset)")
        return UnavailableAudioTranscriber()

    if provider in {"amazon_transcribe", "aws_transcribe", "transcribe"}:
        logger.info("Using Amazon Transcribe for PRMS audio")
        return AmazonTranscribeTranscriber()

    logger.warning(
        "Unknown PRMS_AUDIO_TRANSCRIBER=%s; treating audio as unavailable",
        provider,
    )
    return UnavailableAudioTranscriber()
