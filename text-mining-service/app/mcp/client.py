import os
import json
import base64
import boto3
import httpx
import requests
import uvicorn
from io import BytesIO
from datetime import datetime
from typing import List, Optional, Union
from mcp.client.stdio import stdio_client
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from botocore.exceptions import ClientError
from pydantic import BaseModel, ConfigDict, Field
from fastapi.middleware.cors import CORSMiddleware
from app.utils.s3.s3_util import upload_file_to_s3
from app.utils.logger.logger_util import get_logger
from botocore.exceptions import BotoCoreError, ClientError
from mcp import ClientSession, StdioServerParameters, types
from fastapi.responses import FileResponse, StreamingResponse
from app.utils.prompt.prompt_aiccra import DEFAULT_PROMPT_AICCRA
from app.utils.dynamo.create_bulk_table import create_bulk_upload_table_if_not_exists
from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form, Depends, Request, status
from app.text_mining.prms_mining.request_normalization import assert_audio_extension, assert_document_extension, normalize_prms_sources
from app.text_mining.prms_mining.models import EmptySourceSetError, PrmsMiningError, SourceLimitExceededError, UnsupportedSourceTypeError
from app.utils.config.config_util import AWS, CLIENT_ID, CLIENT_SECRET, IS_PROD, STAR_BUCKET_KEY_NAME, PRMS_BUCKET_KEY_NAME, AICCRA_BUCKET_KEY_NAME, CLARISA_VALIDATE_URL, PRMS_MAX_FILE_BYTES


logger = get_logger()


def _format_mb(value: int | float) -> str:
    return f"{value / 1_000_000:.1f} MB"


def _text_from_mcp_tool_result(result) -> str | None:
    content = getattr(result, "content", None)
    if not content:
        return None
    first = content[0]
    return getattr(first, "text", None)


def _unwrap_prms_mcp_result(result):
    text = _text_from_mcp_tool_result(result)
    if text is None:
        return result

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        if getattr(result, "isError", False):
            raise HTTPException(status_code=500, detail=text)
        return result

    if isinstance(payload, dict) and payload.get("status") == "error":
        status_code = int(payload.get("http_status") or 500)
        raise HTTPException(
            status_code=status_code,
            detail=payload.get("error") or "PRMS mining failed",
        )

    if getattr(result, "isError", False):
        raise HTTPException(status_code=500, detail=payload)

    return payload


dynamodb = boto3.resource('dynamodb', region_name=AWS.get('region', 'us-east-1'))
BULK_UPLOAD_TABLE_NAME = 'bulk_upload_records' if IS_PROD else 'bulk_upload_records_test'
AI_REQUESTS_TABLE_NAME = 'ai-requests-prod' if IS_PROD else 'ai-requests-testing'

server_params = StdioServerParameters(
    command="python",
    args=[os.path.join(os.path.dirname(__file__), "server.py")],
    cwd=os.path.dirname(os.path.abspath(__file__)),
    env={"PYTHONPATH": os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../.."))}
)


class TextMiningRequest(BaseModel):
    bucketName: str = Field(
        ..., description="Name of the S3 bucket where the document is located", examples=["my-documents-bucket"])
    key: Optional[str] = Field(
        None, description="Object key in the S3 bucket. Optional if file is provided", examples=["reports/annual-report-2024.pdf"])
    token: str = Field(
        ..., description="Authentication token", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    environmentUrl: str = Field(
        ..., description="Environment for the service (e.g., production, test)")
    user_id: Optional[str] = Field(
        None, description="User identifier for interaction tracking", examples=["user@example.com", "researcher@cgiar.org"])


class PrmsTextMiningRequest(BaseModel):
    """JSON body for POST /prms/text-mining."""

    model_config = ConfigDict(extra="forbid")

    bucketName: Optional[str] = Field(
        None,
        description="S3 bucket for document and audio keys. Required when using keys or audio_keys.",
        examples=["prms-policy-documents"],
    )
    keys: Optional[list[str]] = Field(
        None,
        description="Existing S3 object keys for documents.",
    )
    text: Optional[str] = Field(
        None,
        description="Optional free-text context. Blank values are ignored.",
    )
    audio_keys: Optional[list[str]] = Field(
        None,
        description="Existing S3 object keys for audio sources.",
    )
    user_id: Optional[str] = Field(
        None,
        description="User identifier for interaction tracking",
        examples=["user@example.com", "researcher@cgiar.org"],
    )


class UploadResponse(BaseModel):
    bucket: str = Field(..., description="S3 bucket where the file was uploaded")
    key: str = Field(..., description="Key (path) of the uploaded file in S3")
    status: str = Field(..., description="Status of the upload operation")
    message: str = Field(..., description="Detailed message about the upload operation")

class S3ListRequest(BaseModel):
    bucket: str
    prefix: str = ""
    max_items: int = 1000


class RecordStatusUpdate(BaseModel):
    fileName: str = Field(..., description="Name of the file")
    recordId: str = Field(..., description="ID of the record")
    status: str = Field(..., description="Status of the record: 'complete' or 'failed'")
    link: Optional[str] = Field(None, description="Link to the result in STAR (only if status is 'complete')")
    title: Optional[str] = Field(None, description="Title of the record (stored for re-upload display)")
    contractCode: Optional[str] = Field(None, description="Contract code of the record (stored for re-upload display)")
    submissionType: Optional[str] = Field(None, description="Submission type: 'approved' or 'draft'")
    year: Optional[str] = Field(None, description="Reporting year of the record")


class RecordStatusUpdateItem(BaseModel):
    recordId: str = Field(..., description="ID of the record")
    status: str = Field(..., description="Status of the record: 'complete' or 'failed'")
    link: Optional[str] = Field(None, description="Link to the result in STAR (only if status is 'complete')")
    title: Optional[str] = Field(None, description="Title of the record (stored for re-upload display)")
    contractCode: Optional[str] = Field(None, description="Contract code of the record (stored for re-upload display)")
    submissionType: Optional[str] = Field(None, description="Submission type: 'approved' or 'draft'")
    year: Optional[str] = Field(None, description="Reporting year of the record")


class BulkRecordStatusUpdate(BaseModel):
    fileName: str = Field(..., description="Name of the file")
    updates: list[RecordStatusUpdateItem] = Field(..., description="List of record status updates to apply atomically")


class BulkUploadRecord(BaseModel):
    fileName: str = Field(..., description="Name of the file (Primary Key)")
    complete: list[str] = Field(default_factory=list, description="List of completed record IDs")
    failed: list[str] = Field(default_factory=list, description="List of failed record IDs")
    links: dict[str, str] = Field(default_factory=dict, description="Dictionary of {recordId: starLink}")
    lastUpdated: str = Field(..., description="Timestamp of last update")


def _normalize_id_list(values) -> list:
    """Normalize DynamoDB ID lists to unique strings, preserving order."""
    seen = set()
    result = []
    for value in list(values or []):
        rid = str(value)
        if rid not in seen:
            seen.add(rid)
            result.append(rid)
    return result


def _normalize_str_dict(mapping) -> dict:
    """Normalize DynamoDB map keys to strings."""
    return {str(k): v for k, v in dict(mapping or {}).items()}


def _apply_record_status_update(
    complete_list: list,
    failed_list: list,
    links_dict: dict,
    record_data_dict: dict,
    record_id: str,
    status: str,
    link: Optional[str] = None,
    title: Optional[str] = None,
    contract_code: Optional[str] = None,
    submission_type: Optional[str] = None,
    year: Optional[str] = None,
) -> None:
    """Apply a single record status mutation to in-memory Dynamo fields."""
    record_id = str(record_id)

    if status == "complete":
        if record_id not in complete_list:
            complete_list.append(record_id)
        if record_id in failed_list:
            failed_list.remove(record_id)
        if link:
            links_dict[record_id] = link
    elif status == "failed":
        if record_id not in failed_list:
            failed_list.append(record_id)
        if record_id in complete_list:
            complete_list.remove(record_id)
        if record_id in links_dict:
            del links_dict[record_id]

    if title or contract_code or submission_type or year:
        record_data_dict[record_id] = {
            'title': title or '',
            'contract_code': contract_code or '',
            'submission_type': submission_type or '',
            'year': year or '',
        }


def _put_bulk_upload_item_with_retry(table, file_name: str, apply_updates) -> dict:
    """
    Read-modify-write a bulk upload item with optimistic locking.

    apply_updates(complete_list, failed_list, links_dict, record_data_dict) mutates
    the working copies in place. Returns the saved item payload.
    """

    max_attempts = 8
    for attempt in range(max_attempts):
        response = table.get_item(Key={'fileName': file_name})
        existing = response.get('Item')
        expected_updated = existing.get('lastUpdated') if existing else None

        complete_list = _normalize_id_list(existing.get('complete', []) if existing else [])
        failed_list = _normalize_id_list(existing.get('failed', []) if existing else [])
        links_dict = _normalize_str_dict(existing.get('links', {}) if existing else {})
        record_data_dict = _normalize_str_dict(existing.get('record_data', {}) if existing else {})

        apply_updates(complete_list, failed_list, links_dict, record_data_dict)

        item = {
            'fileName': file_name,
            'complete': complete_list,
            'failed': failed_list,
            'links': links_dict,
            'record_data': record_data_dict,
            'lastUpdated': datetime.now().isoformat(),
        }

        try:
            if existing is None:
                table.put_item(
                    Item=item,
                    ConditionExpression='attribute_not_exists(fileName)',
                )
            elif expected_updated is not None:
                table.put_item(
                    Item=item,
                    ConditionExpression='lastUpdated = :lu',
                    ExpressionAttributeValues={':lu': expected_updated},
                )
            else:
                # Legacy item without lastUpdated — write once, then retries use locking
                table.put_item(Item=item)
            return item
        except ClientError as e:
            if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
                raise
            # Concurrent write — retry with fresh read
            if attempt == max_attempts - 1:
                raise
            continue

    raise RuntimeError(f"Failed to update bulk upload record for {file_name} after retries")


class FeedbackRequest(BaseModel):
    feedback_type: str = Field(..., description="Feedback type: 'positive' or 'negative'")
    feedback_comment: Optional[str] = Field(None, description="Optional comment (required when feedback_type is 'negative')")
    file_name: Optional[str] = Field(None, description="Name of the processed file")
    user_id: Optional[str] = Field(None, description="User identifier")
    interaction_id: Optional[str] = Field(None, description="ID of the original processing interaction to link feedback to")


app = FastAPI(
    title="CGIAR Text Mining Service API",
    description="""
    AI-Powered Document Processing Service:
    
    This service provides intelligent document analysis using Large Language Models (LLMs) 
    for extracting structured information from various document formats.
    
    Supported Projects:
    - STAR
    - PRMS

    Key Features:
    - 📄 Multi-format document support (PDF, DOCX, Excel, PowerPoint, TXT)
    - 🔍 Semantic content extraction with vector embeddings
    - 🤖 AI-powered analysis using AWS Bedrock (Claude 4.5 Sonnet)
    - 🔐 Authentication integration
    - 📊 Excel row-level processing for structured data
    - 🚀 Real-time processing with MCP protocol
    - 📱 Slack notifications for processing status

    Authentication:
    All requests require a valid token for authentication.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {"url": "https://oxnrkcntlheycdgcnilexrwp4i0tucqz.lambda-url.us-east-1.on.aws", "description": "Test server"},
        {"url": "http://localhost:8000", "description": "Local server"},
        {"url": "https://xps47vud6h2wtznurbtxlgpr4i0qwxlg.lambda-url.us-east-1.on.aws", "description": "Production server"}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create table on startup
try:
    create_bulk_upload_table_if_not_exists()
except Exception as e:
    logger.warning(f"Could not verify/create DynamoDB table: {str(e)}")


async def handle_sampling_message(message: types.CreateMessageRequestParams) -> types.CreateMessageResult:
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            content="Processed by mock model", type="text"),
        model="mock-model",
        stopReason="endTurn"
    )


API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

http_client = httpx.AsyncClient()

def validate_with_clarisa(microservice_name: str):
    async def _validate(request: Request, api_key: str = Depends(api_key_header)):
        client_ip = request.client.host if request.client else "0.0.0.0"
        endpoint = request.url.path

        payload = {
            "api_key": api_key,
            "microservice_name": microservice_name,
            "endpoint_accessed": endpoint,
            "ip_address": client_ip
        }

        try:
            response = await http_client.post(CLARISA_VALIDATE_URL, json=payload, timeout=5.0)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Communication error with the authentication service"
                )

            data = response.json()

            if not data.get("valid"):
                error_msg = data.get("error", "Invalid API Key")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_msg
                )

            return data.get("mis")

        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is temporarily unavailable"
            )

    return _validate


app.mount("/static", StaticFiles(directory="interface"), name="static")


@app.get("/api/auth/token", tags=["Authentication"])
async def get_auth_token():
    """
    Generate authentication token securely from backend.
    This endpoint prevents exposing client credentials to the frontend.
    """
    try:
        credentials = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
        json_string = json.dumps(credentials)
        encoded_token = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
        
        return {
            "status": "success",
            "token": encoded_token
        }
    except Exception as e:
        logger.error(f"Error generating auth token: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate authentication token")


@app.get("/ui", tags=["AICCRA Project"])
async def serve_ui_alt():
    """Alternative endpoint for the UI"""
    return FileResponse('interface/aiccra_mining/index.html')


@app.get("/bulk-upload", tags=["STAR Project"])
async def serve_bulk_upload():
    """Serve the bulk upload interface"""
    return FileResponse('interface/bulk_upload/bulk_upload.html')


@app.get("/aiccra/prompt", tags=["AICCRA Project"])
async def get_aiccra_prompt():
    """Get the default AICCRA prompt template"""
    return {
        "status": "success",
        "content": DEFAULT_PROMPT_AICCRA.strip(),
        "source": "prompt_aiccra.py"
    }


@app.post("/list-s3-objects", tags=["AICCRA Project"])
async def list_s3_objects(request: S3ListRequest):
    """List objects in S3 bucket with given prefix, ordered by LastModified (desc)."""
    try:
        s3 = boto3.client("s3")
        
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=request.bucket, Prefix=request.prefix)
        
        items = []
        for page in pages:
            for obj in page.get("Contents", []):
                items.append((obj["Key"], obj["LastModified"]))
                if len(items) >= request.max_items:
                    break
        
        items.sort(key=lambda x: x[1], reverse=True)
        objects = [k for k, _ in items]
        
        return {
            "status": "success",
            "objects": objects,
            "count": len(objects)
        }
        
    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=f"S3 listing error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/s3/list", tags=["S3 Management"])
async def list_s3_objects_get(bucket: str, prefix: str = "", max_items: int = 1000):
    """
    List objects in S3 bucket with given prefix (GET method for frontend).
    Returns objects ordered by LastModified (desc).
    """
    try:
        s3 = boto3.client("s3")
        
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        
        items = []
        for page in pages:
            for obj in page.get("Contents", []):
                items.append((obj["Key"], obj["LastModified"]))
                if len(items) >= max_items:
                    break
        
        items.sort(key=lambda x: x[1], reverse=True)
        objects = [k for k, _ in items]
        
        return {
            "status": "success",
            "objects": objects,
            "count": len(objects)
        }
        
    except (BotoCoreError, ClientError) as e:
        logger.error(f"S3 listing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"S3 listing error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in S3 listing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/s3/download-template", tags=["S3 Management"])
async def download_excel_template(language: str = "es"):
    try:
        bucket = "ai-services-ibd"
        
        if language == "en":
            key = "star/text-mining/files/capdev_guide_english.zip"
            filename = "capdev_guide_english.zip"
        else:
            key = "star/text-mining/files/capdev_guide_spanish.zip"
            filename = "capdev_guide_spanish.zip"
        
        s3 = boto3.client("s3")
        
        file_obj = s3.get_object(Bucket=bucket, Key=key)
        file_content = file_obj["Body"].read()
        
        return StreamingResponse(
            BytesIO(file_content),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except s3.exceptions.NoSuchKey:
        logger.error(f"Template file not found: {key}")
        raise HTTPException(status_code=404, detail=f"Template file not found in S3: {key}")
    except (BotoCoreError, ClientError) as e:
        logger.error(f"S3 error downloading template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading template: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error downloading template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/dynamo/bulk-upload-records/{file_name}",
         summary="Get Record Statuses",
         description="""
         Retrieve the status of records for a specific file from DynamoDB.
         
         Returns:
         - complete: List of record IDs that were successfully uploaded
         - failed: List of record IDs that failed to upload
         - links: Dictionary mapping record IDs to their STAR URLs
         - lastUpdated: Timestamp of last update
         
         If the file has not been processed before, returns 404.
         """,
         responses={
             200: {"description": "Record statuses retrieved successfully"},
             404: {"description": "File not found in database"},
             500: {"description": "Internal server error"}
         },
         tags=["Bulk Upload Status"])
async def get_record_statuses(file_name: str):
    """
    Get the status of records for a specific file from DynamoDB.
    
    Args:
        file_name: Name of the file (URL encoded)
    
    Returns:
        dict: Record statuses including complete, failed, and links
    """
    try:
        table = dynamodb.Table(BULK_UPLOAD_TABLE_NAME)
        
        response = table.get_item(Key={'fileName': file_name})
        
        if 'Item' not in response:
            raise HTTPException(
                status_code=404,
                detail=f"Record not found for file: {file_name}"
            )
        
        item = response['Item']
        
        return {
            "fileName": item.get('fileName'),
            "complete": _normalize_id_list(item.get('complete', [])),
            "failed": _normalize_id_list(item.get('failed', [])),
            "links": _normalize_str_dict(item.get('links', {})),
            "record_data": _normalize_str_dict(item.get('record_data', {})),
            "lastUpdated": item.get('lastUpdated')
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving record statuses for {file_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving record statuses: {str(e)}"
        )


@app.post("/dynamo/bulk-upload-records",
          summary="Update Record Status",
          description="""
          Update the status of a specific record in DynamoDB.
          
          This endpoint handles the state management for bulk upload records:
          - Creates a new file record if it doesn't exist
          - Updates the status of a record (complete or failed)
          - Manages the links to STAR for completed records
          
          Status Logic:
          - 'complete': Adds record to complete list, removes from failed, stores STAR link
          - 'failed': Adds record to failed list, removes from complete, removes link
          
          Uses optimistic locking with retries to avoid lost updates under concurrency.
          The endpoint is idempotent - calling it multiple times with the same data is safe.
          """,
          responses={
              200: {"description": "Record status updated successfully"},
              400: {"description": "Invalid request - status must be 'complete' or 'failed'"},
              500: {"description": "Internal server error"}
          },
          tags=["Bulk Upload Status"])
async def update_record_status(data: RecordStatusUpdate):
    """
    Update the status of a specific record in DynamoDB.
    
    Args:
        data: RecordStatusUpdate containing fileName, recordId, status, and optional link
    
    Returns:
        dict: Success confirmation with updated record details
    """
    if data.status not in ["complete", "failed"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be either 'complete' or 'failed'"
        )
    
    try:
        table = dynamodb.Table(BULK_UPLOAD_TABLE_NAME)

        def apply_updates(complete_list, failed_list, links_dict, record_data_dict):
            _apply_record_status_update(
                complete_list,
                failed_list,
                links_dict,
                record_data_dict,
                data.recordId,
                data.status,
                data.link,
                data.title,
                data.contractCode,
                data.submissionType,
                data.year,
            )

        _put_bulk_upload_item_with_retry(table, data.fileName, apply_updates)
        
        logger.info(f"✅ Updated status for record {data.recordId} in file {data.fileName}: {data.status}")
        
        return {
            "success": True,
            "fileName": data.fileName,
            "recordId": data.recordId,
            "status": data.status,
            "message": "Record status updated successfully"
        }
    
    except Exception as e:
        logger.error(f"Error updating record status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating record status: {str(e)}"
        )


@app.post("/dynamo/bulk-upload-records/batch",
          summary="Batch Update Record Statuses",
          description="""
          Atomically apply multiple record status updates for a single file.
          
          All updates are merged into one read-modify-write of the DynamoDB item,
          avoiding lost updates when many records succeed in the same STAR submission.
          Uses optimistic locking with retries if another writer updates the same file.
          """,
          responses={
              200: {"description": "Record statuses updated successfully"},
              400: {"description": "Invalid request"},
              500: {"description": "Internal server error"}
          },
          tags=["Bulk Upload Status"])
async def batch_update_record_statuses(data: BulkRecordStatusUpdate):
    """Apply multiple record status updates in a single atomic write."""
    if not data.updates:
        raise HTTPException(status_code=400, detail="updates must not be empty")

    for update in data.updates:
        if update.status not in ["complete", "failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{update.status}' for record {update.recordId}"
            )

    try:
        table = dynamodb.Table(BULK_UPLOAD_TABLE_NAME)

        def apply_updates(complete_list, failed_list, links_dict, record_data_dict):
            for update in data.updates:
                _apply_record_status_update(
                    complete_list,
                    failed_list,
                    links_dict,
                    record_data_dict,
                    update.recordId,
                    update.status,
                    update.link,
                    update.title,
                    update.contractCode,
                    update.submissionType,
                    update.year,
                )

        saved = _put_bulk_upload_item_with_retry(table, data.fileName, apply_updates)

        logger.info(
            f"✅ Batch-updated {len(data.updates)} record(s) in file {data.fileName}"
        )

        return {
            "success": True,
            "fileName": data.fileName,
            "updatedCount": len(data.updates),
            "complete": saved.get('complete', []),
            "failed": saved.get('failed', []),
            "links": saved.get('links', {}),
            "record_data": saved.get('record_data', {}),
            "lastUpdated": saved.get('lastUpdated'),
            "message": "Record statuses updated successfully"
        }

    except Exception as e:
        logger.error(f"Error batch-updating record statuses: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error batch-updating record statuses: {str(e)}"
        )



@app.post("/star/text-mining",
          summary="Process Document for STAR Project",
          description="""
          Process a document using AI text mining techniques for the STAR project.
          
          Processing Flow:
          1. Document validation and upload (if file provided)
          2. Authentication verification  
          3. Document chunking and vectorization
          4. AI analysis using Claude 4.5 Sonnet
          5. Structured data extraction
          
          Supported File Types:
          - PDF documents (.pdf)
          - Microsoft Word (.docx, .doc)
          - Excel spreadsheets (.xlsx, .xls)
          - PowerPoint presentations (.pptx, .ppt)
          - Plain text files (.txt)
          
          Note: You must provide either `key` (for existing S3 documents) or `file` (for upload), but not both.
          """,
          responses={
              200: {"description": "Document processed successfully"},
              400: {"description": "Bad Request - Missing or invalid parameters"},
              401: {"description": "Unauthorized - Invalid or missing authentication token"},
              500: {"description": "Internal Server Error - Error processing document"}
          },
          tags=["STAR Project"])
async def process_document_endpoint(
    request: Request,
    bucketName: str = Form(
        ..., description="Name of the S3 bucket where the document is/will be located", examples=["cgiar-documents"]),
    token: str = Form(
        ..., description="Authentication token", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]),
    key: Optional[str] = Form(
        None, description="Object key in the S3 bucket. Optional if file is provided", examples=["star/text-mining/files/test/training-report-2024.pdf"]),
    file: Optional[Union[UploadFile, str]] = File(
        default=None, description="Document file to upload and process. Optional if key is provided"),
    environmentUrl: str = Form(
        ..., description="Target environment URL for authentication"
    ),
    user_id: Optional[str] = Form(
        None, description="User identifier for interaction tracking", examples=["user@example.com", "researcher@cgiar.org"]
    ),
    mis: str = Depends(validate_with_clarisa("AI Text Mining - STAR"))
):
    """
    Process a document stored in S3 using text mining techniques.
    You can either provide a key to an existing document in S3 or upload a new file.

    - bucketName: Name of the S3 bucket where the document is/will be located
    - token: Authentication token
    - key: Object key in the S3 bucket (required if no file is provided)
    - file: File to upload and process (required if no key is provided)
    - environmentUrl: Environment for the service (e.g., production, test)
    - user_id: User identifier for interaction tracking (optional)

    Returns:
        dict: Result of the document processing
    """
    
    if isinstance(file, str) and file == "":
        file = None

    if key is None and file is None:
        raise HTTPException(
            status_code=400,
            detail="Either 'key' or 'file' must be provided"
        )

    if file is not None:
        try:
            file_content = await file.read()

            filename = file.filename
            key = f"{STAR_BUCKET_KEY_NAME}/{filename}"

            content_type = file.content_type

            upload_file_to_s3(
                file_content=file_content,
                bucket_name=bucketName,
                file_key=key,
                content_type=content_type
            )

            logger.info(f"✅ File {filename} uploaded to {bucketName}/{key}")

        except Exception as e:
            logger.error(f"❌ Error uploading file: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error uploading file: {str(e)}")

    logger.info(
        f"Processing document with key: {key} from bucket {bucketName}")

    result = None
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                await session.initialize()

                mcp_arguments = {
                    "bucket": bucketName,
                    "key": key,
                    "token": token,
                    "environmentUrl": environmentUrl
                }
                
                if user_id:
                    mcp_arguments["user_id"] = user_id

                result = await session.call_tool(
                    "process_document",
                    arguments=mcp_arguments
                )
                return result

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/prms/text-mining",
          summary="Multisource AI extraction for PRMS",
          description="""
          Analyze one or more PRMS sources (documents, free text, and/or S3 audio keys)
          and extract candidate results for CapDev, Policy Change, Innovation Development,
          Innovation Use, Other Output, and Other Outcome (Knowledge Product excluded).

          Source groups are independently optional; at least one non-empty source is required.
          Authenticate with the CLARISA `X-API-Key` header only.

          Request body must be JSON (`application/json`). Audio is accepted only via existing S3 `audio_keys`.
          """,
          responses={
              200: {"description": "Sources processed successfully for PRMS"},
              400: {"description": "Bad Request - Missing or invalid parameters"},
              401: {"description": "Unauthorized - Invalid or missing X-API-Key"},
              413: {"description": "Payload too large"},
              415: {"description": "Unsupported media type"},
              500: {"description": "Internal Server Error - Error processing PRMS sources"},
              503: {"description": "Authentication or audio transcription unavailable"},
          },
          tags=["PRMS Project"])
async def process_document_prms_endpoint(
    body: PrmsTextMiningRequest,
    mis: str = Depends(validate_with_clarisa("AI Text Mining - PRMS")),
):
    """Multisource PRMS mining endpoint (CLARISA X-API-Key only)."""

    try:
        document_keys, normalized_audio_keys, normalized_text = normalize_prms_sources(
            keys=body.keys,
            audio_keys=body.audio_keys,
            text=body.text,
        )
    except EmptySourceSetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    needs_bucket = bool(document_keys or normalized_audio_keys)
    if needs_bucket and not body.bucketName:
        raise HTTPException(
            status_code=400,
            detail="bucketName is required when document keys or audio keys are provided",
        )

    for audio_key in normalized_audio_keys:
        try:
            assert_audio_extension(audio_key)
        except UnsupportedSourceTypeError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc

    for document_key in document_keys:
        try:
            assert_document_extension(document_key)
        except UnsupportedSourceTypeError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc

    logger.info(
        "Processing PRMS request docs=%s audio=%s free_text=%s bucket=%s",
        len(document_keys),
        len(normalized_audio_keys),
        bool(normalized_text),
        body.bucketName,
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                await session.initialize()

                mcp_arguments = {
                    "bucket": body.bucketName,
                    "keys": document_keys or None,
                    "text": normalized_text,
                    "audio_keys": normalized_audio_keys or None,
                }
                if body.user_id:
                    mcp_arguments["user_id"] = body.user_id

                result = await session.call_tool(
                    "process_document_prms",
                    arguments=mcp_arguments,
                )

    except PrmsMiningError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e)) from e
    except SourceLimitExceededError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    except Exception as e:
        logger.error("Error processing document for PRMS: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e

    return _unwrap_prms_mcp_result(result)


@app.post("/star/mining-bulk-upload/capdev",
          summary="Bulk Upload for STAR Project",
          description="""
          This endpoint allows for the bulk upload of documents for the STAR project, specifically for the Capacity Sharing for Development (CapDev) indicator.

          Note: You must provide either `key` (for existing S3 documents) or `file` (for upload), but not both.
          """,
          responses={
              200: {"description": "Document processed successfully"},
              400: {"description": "Bad Request - Missing or invalid parameters"},
              401: {"description": "Unauthorized - Invalid or missing authentication token"},
              500: {"description": "Internal Server Error - Error processing document"}
          },
          tags=["STAR Project"])
async def bulk_upload_capdev_endpoint(
    request: Request,
    bucketName: str = Form(
        ..., description="Name of the S3 bucket where the document is/will be located", examples=["cgiar-documents"]),
    token: str = Form(
        ..., description="Authentication token", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]),
    key: Optional[str] = Form(
        None, description="Object key in the S3 bucket. Optional if file is provided", examples=["star/text-mining/files/test/training-report-2024.pdf"]),
    file: Optional[Union[UploadFile, str]] = File(
        default=None, description="Document file to upload and process. Optional if key is provided"),
    environmentUrl: str = Form(
        ..., description="Target environment URL for authentication"
    ),
    skip_ids: Optional[str] = Form(
        None, description="Comma-separated list of record IDs to skip (already submitted)"
    ),
    user_id: Optional[str] = Form(
        None, description="User identifier for interaction tracking", examples=["user@example.com"]
    ),
    user_name: Optional[str] = Form(
        None, description="Full name of the user for interaction tracking", examples=["John Doe"]
    ),
    mis: str = Depends(validate_with_clarisa("AI Bulk Upload - STAR"))
):
    """
    Process a document stored in S3 using text mining techniques.
    You can either provide a key to an existing document in S3 or upload a new file.

    - bucketName: Name of the S3 bucket where the document is/will be located
    - token: Authentication token
    - key: Object key in the S3 bucket (required if no file is provided)
    - file: File to upload and process (required if no key is provided)
    - environmentUrl: Environment for the service (e.g., production, test)

    Returns:
        dict: Result of the document processing
    """
    
    if isinstance(file, str) and file == "":
        file = None

    if key is None and file is None:
        raise HTTPException(
            status_code=400,
            detail="Either 'key' or 'file' must be provided"
        )

    if file is not None:
        try:
            file_content = await file.read()

            filename = file.filename
            key = f"{STAR_BUCKET_KEY_NAME}/bulk_upload/{filename}"

            content_type = file.content_type

            upload_file_to_s3(
                file_content=file_content,
                bucket_name=bucketName,
                file_key=key,
                content_type=content_type
            )

            logger.info(f"✅ File {filename} uploaded to {bucketName}/{key}")

        except Exception as e:
            logger.error(f"❌ Error uploading file: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error uploading file: {str(e)}")

    logger.info(
        f"Processing document with key: {key} from bucket {bucketName}")

    # Parse skip_ids from comma-separated string
    parsed_skip_ids = [sid.strip() for sid in skip_ids.split(",") if sid.strip()] if skip_ids else []
    if parsed_skip_ids:
        logger.info(f"⏭️ Skipping {len(parsed_skip_ids)} already-submitted record IDs")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                await session.initialize()

                mcp_arguments = {
                    "bucket": bucketName,
                    "key": key,
                    "token": token,
                    "environmentUrl": environmentUrl,
                    "skip_ids": parsed_skip_ids
                }
                if user_id:
                    mcp_arguments["user_id"] = user_id
                if user_name:
                    mcp_arguments["user_name"] = user_name

                result = await session.call_tool(
                    "process_document_capdev",
                    arguments=mcp_arguments
                )
                return result

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/aiccra/text-mining",
          summary="Process Document for AICCRA Project",
          description="""
          Process a document using AI text mining techniques for the AICCRA project.
          
          Processing Flow:
          1. Document validation and upload (if file provided)
          2. Document chunking and vectorization
          3. AI analysis using Claude 4.5 Sonnet with custom or default prompt
          4. Structured data extraction
          
          Supported File Types:
          - PDF documents (.pdf)
          - Microsoft Word (.docx, .doc)
          - Excel spreadsheets (.xlsx, .xls)
          - PowerPoint presentations (.pptx, .ppt)
          - Plain text files (.txt)
          
          Custom Prompts:
          - You can provide a custom prompt to guide the AI analysis
          - If no prompt is provided, the default AICCRA prompt will be used
          - Custom prompts allow for dynamic analysis based on specific requirements
          
          Note: You must provide either `key` (for existing S3 documents) or `file` (for upload), but not both.
          """,
          responses={
              200: {"description": "Document processed successfully"},
              400: {"description": "Bad Request - Missing or invalid parameters"},
              401: {"description": "Unauthorized - Invalid or missing authentication token"},
              500: {"description": "Internal Server Error - Error processing document"}
          },
          tags=["AICCRA Project"])
async def process_document_aiccra_endpoint(
    bucketName: str = Form(
        ..., description="Name of the S3 bucket where the document is/will be located", examples=["cgiar-documents"]),
    token: Optional[str] = Form(
        None, description="Authentication token", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]),
    key: Optional[str] = Form(
        None, description="Object key in the S3 bucket. Optional if file is provided", examples=["star/text-mining/files/test/training-report-2024.pdf"]),
    file: Optional[Union[UploadFile, str]] = File(
        default=None, description="Document file to upload and process. Optional if key is provided"),
    environmentUrl: Optional[str] = Form(
        None, description="Target environment URL for authentication"
    ),
    user_id: Optional[str] = Form(
        None, description="User identifier for interaction tracking", examples=["user@example.com", "researcher@cgiar.org"]
    ),
    prompt: Optional[str] = Form(
        None, description="Custom prompt for document analysis. If not provided, the default AICCRA prompt will be used", examples=["Extract all climate adaptation strategies mentioned in this document and categorize them by sector."]
    )
):
    """
    Process a document stored in S3 using text mining techniques.
    You can either provide a key to an existing document in S3 or upload a new file.

    - bucketName: Name of the S3 bucket where the document is/will be located
    - token: Authentication token
    - key: Object key in the S3 bucket (required if no file is provided)
    - file: File to upload and process (required if no key is provided)
    - environmentUrl: Environment for the service (e.g., production, test)
    - user_id: User identifier for interaction tracking (optional)

    Returns:
        dict: Result of the document processing
    """
    
    if isinstance(file, str) and file == "":
        file = None

    if key is None and file is None:
        raise HTTPException(
            status_code=400,
            detail="Either 'key' or 'file' must be provided"
        )

    if file is not None:
        try:
            file_content = await file.read()

            filename = file.filename
            key = f"{AICCRA_BUCKET_KEY_NAME}/{filename}"

            content_type = file.content_type

            upload_file_to_s3(
                file_content=file_content,
                bucket_name=bucketName,
                file_key=key,
                content_type=content_type
            )

            logger.info(f"✅ File {filename} uploaded to {bucketName}/{key}")

        except Exception as e:
            logger.error(f"❌ Error uploading file: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error uploading file: {str(e)}")

    logger.info(
        f"Processing document with key: {key} from bucket {bucketName}")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                await session.initialize()

                mcp_arguments = {
                    "bucket": bucketName,
                    "key": key,
                    "token": token,
                    "environmentUrl": environmentUrl
                }
                
                if user_id:
                    mcp_arguments["user_id"] = user_id
                
                if prompt:
                    mcp_arguments["prompt"] = prompt

                result = await session.call_tool(
                    "process_document_aiccra",
                    arguments=mcp_arguments
                )
                return result

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback",
          summary="Submit user feedback for bulk upload experience",
          tags=["Feedback"])
async def submit_feedback(req: FeedbackRequest):
    """Receive thumbs-up / thumbs-down feedback from the bulk upload UI and update
    the original processing interaction via the interaction tracking service."""
    logger.info(f"📝 Feedback received: feedback_type={req.feedback_type}, user={req.user_id}, file={req.file_name}, interaction_id={req.interaction_id}")
    if req.feedback_comment:
        logger.info(f"💬 Feedback comment: {req.feedback_comment}")

    try:
        from app.utils.interactions.interaction_client import INTERACTION_SERVICE_URL
        payload = {
            "user_id": req.user_id or "anonymous",
            "service_name": "bulk-text-mining",
            "update_mode": True,
            "interaction_id": req.interaction_id,
            "feedback_type": req.feedback_type,
            "feedback_comment": req.feedback_comment,
        }
        
        payload = {k: v for k, v in payload.items() if v is not None}
        logger.info(f"📦 Sending feedback payload to interaction service: {payload}")
        response = requests.post(
            f"{INTERACTION_SERVICE_URL.rstrip('/')}/api/interactions",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            logger.info(f"✅ Feedback tracked successfully: {response.json()}")
        else:
            logger.error(f"❌ Interaction service returned {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Failed to send feedback to interaction service: {e}")

    return {"status": "ok"}


@app.get("/feedback/{interaction_id}",
         summary="Query feedback by interaction ID",
         description="""
         Retrieve feedback data stored in DynamoDB for a specific AI processing interaction.

         Intended for STAR backend services to check whether a user left feedback
         for a given bulk upload session identified by its AI interaction ID.

         Returns feedback_type ('positive' or 'negative'), optional comment, file name,
         user identifier, and timestamp.
         """,
         responses={
             200: {"description": "Feedback record found"},
             404: {"description": "No feedback found for this interaction_id"},
             500: {"description": "Internal server error"},
         },
         tags=["Feedback"])
async def get_feedback_by_interaction(interaction_id: str):
    """Query DynamoDB for feedback associated with a given AI interaction ID."""
    try:
        ai_requests_table = dynamodb.Table(AI_REQUESTS_TABLE_NAME)
        response = ai_requests_table.get_item(Key={
            "interaction_id": interaction_id,
            "service_name": "bulk-text-mining",
        })
        if "Item" not in response:
            raise HTTPException(
                status_code=404,
                detail=f"No record found for interaction_id: {interaction_id}"
            )
        return {"status": "ok", "data": response["Item"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying feedback for interaction_id={interaction_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error querying feedback: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)