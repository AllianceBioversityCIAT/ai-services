import boto3
import mammoth
import pandas as pd
from io import BytesIO
from pptx import Presentation
from utils.config.config_util import get_boto3_client_kwargs
from utils.logger.logger_util import get_logger

logger = get_logger()

SUPPORTED_DOCUMENT_EXTENSIONS = {
    'pdf', 'jpg', 'jpeg', 'png', 'tiff', 'tif',
    'docx', 'txt', 'xls', 'xlsx', 'pptx',
}
MAX_PROJECT_DOCUMENTS = 3

_s3_client = None


def _get_s3_client():
    """Lazy client — avoids caching invalid keys across warm Lambda containers."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", **get_boto3_client_kwargs())
    return _s3_client


def _process_file_content(file_extension, file_content):
    if file_extension == 'docx':
        logger.info("Processing DOCX file with Mammoth...")
        result = mammoth.convert_to_html(BytesIO(file_content))
        for message in result.messages:
            logger.warning(f"Mammoth conversion warning: {message}")
        html = result.value.strip()
        logger.info(f"DOCX converted to HTML — {len(html)} characters extracted")
        return html
    elif file_extension == 'txt':
        logger.info("📄 Processing TXT file...")
        return file_content.decode('utf-8')
    elif file_extension in ('xls', 'xlsx'):
        logger.info("📄 Processing EXCEL file...")
        df = pd.read_excel(BytesIO(file_content), header=0)
        logger.info(f"📊 Original DataFrame shape: {df.shape}")
        
        df = df.dropna(axis=1, how='all')        
        df = df.dropna(axis=0, how='all')
        df = df[~df.apply(lambda row: all(str(val).strip() == '' or pd.isna(val) for val in row), axis=1)]
        df = df.drop_duplicates()
        df = df.reset_index(drop=True)
        logger.info(f"📊 Cleaned DataFrame shape: {df.shape}")
    
        try:
            structured_rows = []
            for index, row in df.iterrows():
                row_parts = []
                for col in df.columns:
                    value = str(row[col]).strip()
                    if value and value != 'nan' and value != 'None':
                        row_parts.append(f"{col}: {value}")
                
                if row_parts:
                    row_text = ", ".join(row_parts)
                    structured_rows.append(row_text)
            
            logger.info(f"📊 Processed {len(structured_rows)} meaningful Excel rows as individual chunks")
            
            if structured_rows:
                logger.info("📝 Sample rows:")
                for i, row in enumerate(structured_rows[:3]):
                    logger.info(f"  Row {i+1}: {row}")
            
            return {"type": "excel", "chunks": structured_rows}
            
        except Exception as e:
            logger.warning(f"⚠️ Excel processing failed, falling back to CSV: {e}")
            df = df.to_csv(index=False, header=True)
            return df

    elif file_extension == 'pptx':
        logger.info("📄 Processing PPTX file...")
        prs = Presentation(BytesIO(file_content))
        text = ""
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
        return text
    else:
        raise ValueError(f"File format not supported: {file_extension}")


def list_project_documents(
    bucket_name: str,
    project_folder: str,
    max_documents: int = MAX_PROJECT_DOCUMENTS,
) -> list[str]:
    """
    List supported document keys under a project folder in S3.

    Args:
        bucket_name: S3 bucket name
        project_folder: Folder prefix for the project (e.g. star/ai-insights/projects/abc123)
        max_documents: Maximum number of documents allowed (default: 3)

    Returns:
        Sorted list of S3 object keys

    Raises:
        ValueError: If no supported documents are found or the limit is exceeded
    """
    prefix = project_folder.strip('/')
    if prefix:
        prefix = f"{prefix}/"

    logger.info(f"Listing documents in s3://{bucket_name}/{prefix}")

    response = _get_s3_client().list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    contents = response.get('Contents', [])

    document_keys = []
    for obj in contents:
        key = obj['Key']
        if key.endswith('/') or obj.get('Size', 0) == 0:
            continue

        extension = key.lower().rsplit('.', 1)[-1]
        if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
            logger.warning(f"Skipping unsupported file: {key}")
            continue

        document_keys.append(key)

    document_keys.sort()

    if not document_keys:
        raise ValueError(
            f"No supported documents found in s3://{bucket_name}/{project_folder}"
        )

    if len(document_keys) > max_documents:
        raise ValueError(
            f"Found {len(document_keys)} documents in project folder "
            f"(maximum allowed: {max_documents})"
        )

    logger.info(f"Found {len(document_keys)} document(s): {document_keys}")
    return document_keys


def read_document_from_s3(bucket_name, file_key):
    try:
        logger.info(
            f"📂 Downloading the {file_key} file from the bucket {bucket_name}...")
        response = _get_s3_client().get_object(Bucket=bucket_name, Key=file_key)
        file_content = response['Body'].read()
        file_extension = file_key.lower().split('.')[-1]

        return _process_file_content(file_extension, file_content)

    except Exception as e:
        logger.error(
            f"❌ Error while reading {file_key} from bucket {bucket_name}: {str(e)}")
        raise


def download_file_from_s3(bucket_name: str, file_key: str) -> bytes:
    """
    Download raw file bytes from S3 without any content processing.
    Useful for passing documents directly to Amazon Textract or other services.

    Args:
        bucket_name: Name of the S3 bucket
        file_key: The key (path) of the file in S3

    Returns:
        Raw file content as bytes

    Raises:
        Exception: If the download fails
    """
    try:
        logger.info(f"Downloading raw file {file_key} from bucket {bucket_name}...")
        response = _get_s3_client().get_object(Bucket=bucket_name, Key=file_key)
        file_content = response['Body'].read()
        logger.info(f"Successfully downloaded {file_key} ({len(file_content)} bytes)")
        return file_content
    except Exception as e:
        logger.error(f"Error downloading {file_key} from bucket {bucket_name}: {str(e)}")
        raise


def upload_file_to_s3(file_content, bucket_name, file_key, content_type=None):
    """
    Upload a file to an S3 bucket.

    Args:
        file_content: The content of the file to upload (bytes or file-like object)
        bucket_name: Name of the S3 bucket
        file_key: The key (path) where the file will be stored in S3
        content_type: Optional MIME type of the file

    Returns:
        dict: The response from S3 upload operation

    Raises:
        Exception: If the upload fails
    """
    try:
        logger.info(f"📤 Uploading file to {bucket_name}/{file_key}...")

        # Prepare upload parameters
        upload_args = {
            'Bucket': bucket_name,
            'Key': file_key,
            'Body': file_content
        }

        # Add content type if provided
        if content_type:
            upload_args['ContentType'] = content_type

        # Upload the file
        response = _get_s3_client().put_object(**upload_args)

        logger.info(
            f"✅ File successfully uploaded to {bucket_name}/{file_key}")
        return response

    except Exception as e:
        logger.error(
            f"❌ Error uploading file to {bucket_name}/{file_key}: {str(e)}")
        raise
