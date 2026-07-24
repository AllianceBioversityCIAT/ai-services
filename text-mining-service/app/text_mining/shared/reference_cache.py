import json
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from app.utils.logger.logger_util import get_logger
from app.utils.s3.s3_util import read_document_from_s3

logger = get_logger()

# Module-level cache - persists across warm Lambda invocations.
# key: "bucket_name:project_key" - {"regions": [...], "countries": [...]}
_reference_cache: dict = {}

REFERENCE_DATA_FILENAME = "clarisa_reference_data.json"

s3_client = boto3.client("s3")


def _cache_key(bucket_name: str, project_key: str) -> str:
    return f"{bucket_name}:{project_key}"


def _load_from_s3_json(bucket_name: str, project_key: str) -> dict | None:
    """
    Try to load pre-computed reference data from S3.
    Returns None if the file does not exist yet.
    """
    s3_key = f"{project_key}/{REFERENCE_DATA_FILENAME}"
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        data = json.loads(response["Body"].read())
        logger.info(f"📍 Loaded pre-computed reference data from s3://{bucket_name}/{s3_key}")
        return data
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            logger.info(
                f"⚠️ Pre-computed reference data not found at {s3_key} — will build from Excel"
            )
            return None
        logger.warning(f"⚠️ S3 error loading reference data: {e}")
        return None
    except Exception as e:
        logger.warning(f"❌ Unexpected error loading reference data from S3: {e}")
        return None


def _build_from_excel(
    bucket_name: str, file_key_regions: str, file_key_countries: str
) -> dict:
    """
    Read the two CLARISA Excel files from S3 and convert them to text chunks.
    This path is only hit on the very first cold start after a new deployment.
    """
    logger.info("🔄 Building reference data from Excel files (first-time setup)...")

    raw_regions = read_document_from_s3(bucket_name, file_key_regions)
    raw_countries = read_document_from_s3(bucket_name, file_key_countries)

    regions_chunks = (
        raw_regions["chunks"]
        if isinstance(raw_regions, dict) and raw_regions.get("type") == "excel"
        else [raw_regions]
    )
    countries_chunks = (
        raw_countries["chunks"]
        if isinstance(raw_countries, dict) and raw_countries.get("type") == "excel"
        else [raw_countries]
    )

    return {
        "regions": regions_chunks,
        "countries": countries_chunks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_regions": file_key_regions,
        "source_countries": file_key_countries,
    }


def _upload_to_s3_json(data: dict, bucket_name: str, project_key: str) -> None:
    """
    Upload the pre-computed reference data JSON to S3 so future cold starts
    skip the Excel processing entirely.
    """
    s3_key = f"{project_key}/{REFERENCE_DATA_FILENAME}"
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(data, ensure_ascii=False, indent=2),
            ContentType="application/json",
        )
        logger.info(f"📤 Uploaded pre-computed reference data to s3://{bucket_name}/{s3_key}")
    except Exception as e:
        logger.warning(
            f"⚠️ Could not upload reference data to S3 (will rebuild next cold start): {e}"
        )


def get_reference_data(
    bucket_name: str,
    project_key: str,
    file_key_regions: str,
    file_key_countries: str,
) -> dict:
    """
    Return reference data (regions + countries text chunks) with three-level caching:

    1. In-memory module variable  - warm Lambda starts, instant (0 ms)
    2. Pre-computed S3 JSON file  - cold starts, single GET (~150 ms)
    3. Excel files on S3          - first-ever run, builds + uploads JSON (~2 s)

    The returned dict has the shape:
        {
            "regions":   ["UN49 Code: 2, Name: Africa", ...],   # 30 entries
            "countries": ["Code: 784, ISO Alpha2: AE, ...", ...] # 248 entries
        }
    """
    key = _cache_key(bucket_name, project_key)

    # Level 1: in-memory (warm start)
    if key in _reference_cache:
        logger.info("📍 Reference data served from memory cache (warm start)")
        return _reference_cache[key]

    # Level 2: pre-computed S3 JSON (cold start)
    data = _load_from_s3_json(bucket_name, project_key)

    # Level 3: build from Excel and persist for next cold start
    if data is None:
        data = _build_from_excel(bucket_name, file_key_regions, file_key_countries)
        _upload_to_s3_json(data, bucket_name, project_key)

    n_regions = len(data.get("regions", []))
    n_countries = len(data.get("countries", []))
    logger.info(f"✅ Reference data ready: {n_regions} regions, {n_countries} countries")

    _reference_cache[key] = data
    return data


def format_reference_for_prompt(reference_data: dict) -> str:
    """
    Format the reference data into the section that is appended to every
    model prompt so Claude can look up official CLARISA codes.

    Shared by STAR, AICCRA, and bulk upload (geoscope_level / regions / countries).
    """
    regions_text = "\n".join(reference_data.get("regions", []))
    countries_text = "\n".join(reference_data.get("countries", []))

    return (
        "GEOGRAPHIC REFERENCE DATA - for geoscope fields only\n"
        "Use the codes below EXCLUSIVELY to fill the 'regions' (UN49 codes) and\n"
        "'countries' (ISO Alpha-2 codes) fields in the output JSON.\n"
        "This is a lookup table, NOT document content to be analyzed.\n\n"
        "REGIONS (UN49 codes):\n"
        f"{regions_text}\n\n"
        "COUNTRIES (ISO Alpha-2 codes):\n"
        f"{countries_text}"
    )
