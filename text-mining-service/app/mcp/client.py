import os
import json
import base64
import boto3
import uvicorn
from typing import Optional, Union
from pydantic import BaseModel, Field
from mcp.client.stdio import stdio_client
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.utils.s3.s3_util import upload_file_to_s3
from app.utils.logger.logger_util import get_logger
from botocore.exceptions import BotoCoreError, ClientError
from mcp import ClientSession, StdioServerParameters, types
from app.utils.prompt.prompt_aiccra import DEFAULT_PROMPT_AICCRA
from app.utils.config.config_util import AWS, CLIENT_ID, CLIENT_SECRET
from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form
from app.utils.dynamo.create_bulk_table import create_bulk_upload_table_if_not_exists
from app.utils.config.config_util import STAR_BUCKET_KEY_NAME, PRMS_BUCKET_KEY_NAME, AICCRA_BUCKET_KEY_NAME


logger = get_logger()

dynamodb = boto3.resource('dynamodb', region_name=AWS.get('region', 'us-east-1'))
BULK_UPLOAD_TABLE_NAME = 'bulk_upload_records'

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


class BulkUploadRecord(BaseModel):
    fileName: str = Field(..., description="Name of the file (Primary Key)")
    complete: list[str] = Field(default_factory=list, description="List of completed record IDs")
    failed: list[str] = Field(default_factory=list, description="List of failed record IDs")
    links: dict[str, str] = Field(default_factory=dict, description="Dictionary of {recordId: starLink}")
    lastUpdated: str = Field(..., description="Timestamp of last update")


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
    - 🤖 AI-powered analysis using AWS Bedrock (Claude 3 Sonnet)
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
    return FileResponse('interface/index.html')


@app.get("/bulk-upload", tags=["STAR Project"])
async def serve_bulk_upload():
    """Serve the bulk upload interface"""
    return FileResponse('interface/bulk_upload.html')


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
            "complete": item.get('complete', []),
            "failed": item.get('failed', []),
            "links": item.get('links', {}),
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
        from datetime import datetime
        
        table = dynamodb.Table(BULK_UPLOAD_TABLE_NAME)
        
        # Get existing record or create new one
        response = table.get_item(Key={'fileName': data.fileName})
        
        if 'Item' in response:
            item = response['Item']
        else:
            # Create new record
            item = {
                'fileName': data.fileName,
                'complete': [],
                'failed': [],
                'links': {}
            }
        
        # Convert to standard Python types
        complete_list = list(item.get('complete', []))
        failed_list = list(item.get('failed', []))
        links_dict = dict(item.get('links', {}))
        
        # Update based on status
        if data.status == "complete":
            # Add to complete, remove from failed
            if data.recordId not in complete_list:
                complete_list.append(data.recordId)
            if data.recordId in failed_list:
                failed_list.remove(data.recordId)
            # Update link
            if data.link:
                links_dict[data.recordId] = data.link
        
        elif data.status == "failed":
            # Add to failed, remove from complete
            if data.recordId not in failed_list:
                failed_list.append(data.recordId)
            if data.recordId in complete_list:
                complete_list.remove(data.recordId)
            # Remove link if exists
            if data.recordId in links_dict:
                del links_dict[data.recordId]
        
        # Save to DynamoDB
        table.put_item(
            Item={
                'fileName': data.fileName,
                'complete': complete_list,
                'failed': failed_list,
                'links': links_dict,
                'lastUpdated': datetime.now().isoformat()
            }
        )
        
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



@app.post("/star/text-mining",
          summary="Process Document for STAR Project",
          description="""
          Process a document using AI text mining techniques for the STAR project.
          
          Processing Flow:
          1. Document validation and upload (if file provided)
          2. Authentication verification  
          3. Document chunking and vectorization
          4. AI analysis using Claude 3 Sonnet
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
          summary="Process document for PRMS Project",
          description="""
          Process a document using AI text mining techniques for the PRMS (Policy Research and Management Systems) project.
          
          PRMS-Specific Features:
          - Policy change analysis and classification
          - Innovation development assessment
          - Capacity sharing evaluation with detailed demographics
          - Stakeholder identification and categorization
          
          Processing Capabilities:
          - Extract policy interventions and their stages
          - Identify innovation readiness levels (0-9 scale)
          - Analyze training programs and participant demographics
          - Classify organization types and roles
          
          Note: You must provide either `key` (for existing S3 documents) or `file` (for upload), but not both.
          """,
          responses={
              200: {"description": "Document processed successfully for PRMS"},
              400: {"description": "Bad Request - Missing or invalid parameters"},
              401: {"description": "Unauthorized - Authentication failed"},
              500: {"description": "Internal Server Error - Error processing document for PRMS"}
          },
          tags=["PRMS Project"])
async def process_document_prms_endpoint(
    bucketName: str = Form(
        ..., description="Name of the S3 bucket where the document is/will be located", examples=["prms-policy-documents"]),
    token: str = Form(
        ..., description="Authentication token for PRMS access", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]),
    key: Optional[str] = Form(
        None, description="Object key in the S3 bucket. Optional if file is provided", examples=["prms/text-mining/files/test/climate-policy-2024.docx"]),
    file: Optional[Union[UploadFile, str]] = File(
        default=None, description="File to upload and process. Optional if key is provided"),
    environmentUrl: str = Form(
        ..., description="Target environment URL for PRMS authentication"
    ),
    user_id: Optional[str] = Form(
        None, description="User identifier for interaction tracking", examples=["user@example.com", "researcher@cgiar.org"]
    )
):
    """
    Process a document stored in S3 using text mining techniques for PRMS project.
    You can either provide a key to an existing document in S3 or upload a new file.

    - bucketName: Name of the S3 bucket where the document is/will be located
    - token: Authentication token
    - key: Object key in the S3 bucket (required if no file is provided)
    - file: File to upload and process (required if no key is provided)
    - environmentUrl: Environment for the service (e.g., production, test)
    - user_id: User identifier for interaction tracking (optional)

    Returns:
        dict: Result of the document processing for PRMS
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
            key = f"{PRMS_BUCKET_KEY_NAME}/{filename}"

            content_type = file.content_type

            upload_file_to_s3(
                file_content=file_content,
                bucket_name=bucketName,
                file_key=key,
                content_type=content_type
            )

            logger.info(f"✅ File {filename} uploaded to {bucketName}/{key} for PRMS")

        except Exception as e:
            logger.error(f"❌ Error uploading file for PRMS: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error uploading file for PRMS: {str(e)}")

    logger.info(
        f"Processing document for PRMS with key: {key} from bucket {bucketName}")

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
                    "process_document_prms",
                    arguments=mcp_arguments
                )
                return result

    except Exception as e:
        logger.error(f"Error processing document for PRMS: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                await session.initialize()

                result = await session.call_tool(
                    "process_document_capdev",
                    arguments={
                        "bucket": bucketName,
                        "key": key,
                        "token": token,
                        "environmentUrl": environmentUrl
                    }
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
          3. AI analysis using Claude 4 Sonnet with custom or default prompt
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
    

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)