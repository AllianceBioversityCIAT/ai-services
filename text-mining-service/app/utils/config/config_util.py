import os
from dotenv import load_dotenv

load_dotenv()


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        value = default
    else:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")
    return value


def _optional_positive_int(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")
    return value


AWS = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "aws_region": os.getenv("AWS_REGION", "us-east-1")
}

MS_NAME = os.getenv("MS_NAME", "Mining Microservice")

STAR_BUCKET_KEY_NAME = os.getenv("STAR_BUCKET_KEY_NAME")
PRMS_BUCKET_KEY_NAME = os.getenv("PRMS_BUCKET_KEY_NAME")
AICCRA_BUCKET_KEY_NAME = os.getenv("AICCRA_BUCKET_KEY_NAME")

MAPPING_URL = os.getenv("MAPPING_URL")

CLIENT_ID = os.getenv("CLIENT_ID", None)
CLIENT_SECRET = os.getenv("CLIENT_SECRET", None)

IS_PROD = os.getenv("IS_PROD", "false").lower() == "true"

CLARISA_VALIDATE_URL = os.getenv("CLARISA_VALIDATE_URL")

PRMS_EXTRACTION_MAX_WORKERS = _positive_int("PRMS_EXTRACTION_MAX_WORKERS", 4)
PRMS_MAX_SOURCES = _positive_int("PRMS_MAX_SOURCES", 6)
PRMS_MAX_FILE_BYTES = _positive_int("PRMS_MAX_FILE_BYTES", 25_000_000)
PRMS_MAX_PDF_PAGES = _positive_int("PRMS_MAX_PDF_PAGES", 100)
PRMS_MAX_TEXT_CHARS = _positive_int("PRMS_MAX_TEXT_CHARS", 50_000)
PRMS_CONTEXT_TOKEN_BUDGET = _positive_int("PRMS_CONTEXT_TOKEN_BUDGET", 300_000)
PRMS_FULL_SOURCE_MAX_CHARS = _positive_int("PRMS_FULL_SOURCE_MAX_CHARS", 50_000)
PRMS_RETRIEVAL_TOP_K_PER_SOURCE = _positive_int("PRMS_RETRIEVAL_TOP_K_PER_SOURCE", 8)
PRMS_FINAL_VALIDATION_ENABLED = os.getenv("PRMS_FINAL_VALIDATION_ENABLED", "false").lower() == "true"

PRMS_AUDIO_TRANSCRIBER = (os.getenv("PRMS_AUDIO_TRANSCRIBER") or "").strip()
PRMS_MAX_AUDIO_SECONDS = _optional_positive_int("PRMS_MAX_AUDIO_SECONDS")
PRMS_TRANSCRIBE_LANGUAGE_CODE = (os.getenv("PRMS_TRANSCRIBE_LANGUAGE_CODE") or "").strip()
PRMS_TRANSCRIBE_POLL_INTERVAL_SECONDS = _positive_int("PRMS_TRANSCRIBE_POLL_INTERVAL_SECONDS", 2)
PRMS_TRANSCRIBE_TIMEOUT_SECONDS = _positive_int("PRMS_TRANSCRIBE_TIMEOUT_SECONDS", 300)

_raw_lang_options = (os.getenv("PRMS_TRANSCRIBE_LANGUAGE_OPTIONS") or "en-US,es-ES,fr-FR,pt-BR").strip()
PRMS_TRANSCRIBE_LANGUAGE_OPTIONS = tuple(
    part.strip() for part in _raw_lang_options.split(",") if part.strip()
)

PRMS_SUPPORTED_DOCUMENT_EXTENSIONS = frozenset(
    {"pdf", "docx", "txt", "xls", "xlsx", "pptx"}
)
PRMS_SUPPORTED_AUDIO_EXTENSIONS = frozenset(
    {"mp3", "wav", "m4a", "ogg", "flac", "webm"}
)