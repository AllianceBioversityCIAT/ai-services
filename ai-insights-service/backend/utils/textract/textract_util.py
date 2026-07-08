import time
import boto3
from utils.config.config_util import get_boto3_client_kwargs
from utils.logger.logger_util import get_logger

logger = get_logger()

# Formats supported by Amazon Textract
TEXTRACT_SUPPORTED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'tiff', 'tif'}

# Formats where async is required (multi-page capable)
ASYNC_REQUIRED_EXTENSIONS = {'pdf', 'tiff', 'tif'}

POLL_INTERVAL_SECONDS = 5
MAX_POLL_ATTEMPTS = 60  # 5 minutes max

_textract_client = None


def _get_textract_client():
    global _textract_client
    if _textract_client is None:
        _textract_client = boto3.client("textract", **get_boto3_client_kwargs())
    return _textract_client


def _blocks_to_text(blocks: list) -> str:
    """Extract LINE-type blocks and join them as plain text."""
    lines = [block['Text'] for block in blocks if block.get('BlockType') == 'LINE']
    return '\n'.join(lines)


def extract_text_sync(bucket_name: str, file_key: str) -> str:
    """
    Extract text from a single-page document stored in S3 using Textract synchronously.
    Suitable for: single-page PDF, JPEG, PNG, TIFF.

    Args:
        bucket_name: S3 bucket name
        file_key: S3 object key

    Returns:
        Extracted text as a string
    """
    logger.info(f"Starting synchronous Textract extraction for s3://{bucket_name}/{file_key}...")

    response = _get_textract_client().detect_document_text(
        Document={'S3Object': {'Bucket': bucket_name, 'Name': file_key}}
    )

    text = _blocks_to_text(response.get('Blocks', []))
    logger.info(f"Synchronous Textract extraction complete — {len(text)} characters extracted from {file_key}")
    return text


def extract_text_async(bucket_name: str, file_key: str) -> str:
    """
    Extract text from a multi-page document stored in S3 using Textract asynchronously.
    Suitable for: multi-page PDF, TIFF.

    Polls until the job completes or the timeout is reached.

    Args:
        bucket_name: S3 bucket name
        file_key: S3 object key

    Returns:
        Extracted text as a string

    Raises:
        RuntimeError: If the Textract job fails
        TimeoutError: If the job does not complete within the allowed time
    """
    logger.info(f"Starting asynchronous Textract extraction for s3://{bucket_name}/{file_key}...")

    start_response = _get_textract_client().start_document_text_detection(
        DocumentLocation={'S3Object': {'Bucket': bucket_name, 'Name': file_key}}
    )
    job_id = start_response['JobId']
    logger.info(f"Textract job started — Job ID: {job_id}")

    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        time.sleep(POLL_INTERVAL_SECONDS)

        result = _get_textract_client().get_document_text_detection(JobId=job_id)
        status = result['JobStatus']
        logger.info(f"Textract job status (attempt {attempt}/{MAX_POLL_ATTEMPTS}): {status}")

        if status == 'SUCCEEDED':
            blocks = result.get('Blocks', [])

            # Handle paginated results
            while 'NextToken' in result:
                result = _get_textract_client().get_document_text_detection(
                    JobId=job_id,
                    NextToken=result['NextToken']
                )
                blocks.extend(result.get('Blocks', []))

            text = _blocks_to_text(blocks)
            logger.info(
                f"Async Textract extraction complete — {len(text)} characters extracted from {file_key}"
            )
            return text

        if status == 'FAILED':
            error_msg = result.get('StatusMessage', 'Unknown error')
            logger.error(f"Textract job {job_id} failed: {error_msg}")
            raise RuntimeError(f"Textract text detection failed for {file_key}: {error_msg}")

    raise TimeoutError(
        f"Textract job {job_id} did not complete within "
        f"{MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS} seconds"
    )


def extract_text_from_s3(bucket_name: str, file_key: str, force_async: bool = False) -> str:
    """
    Extract text from a document stored in S3 using Amazon Textract.

    Automatically selects synchronous mode for images and asynchronous mode
    for multi-page capable formats (PDF, TIFF), unless force_async is True.

    Args:
        bucket_name: S3 bucket name
        file_key: S3 object key
        force_async: Force asynchronous extraction regardless of file type

    Returns:
        Extracted text as a string

    Raises:
        ValueError: If the file format is not supported by Textract
    """
    extension = file_key.lower().rsplit('.', 1)[-1]

    if extension not in TEXTRACT_SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"File format '{extension}' is not supported by Amazon Textract. "
            f"Supported formats: {', '.join(sorted(TEXTRACT_SUPPORTED_EXTENSIONS))}"
        )

    if force_async or extension in ASYNC_REQUIRED_EXTENSIONS:
        return extract_text_async(bucket_name, file_key)

    return extract_text_sync(bucket_name, file_key)
