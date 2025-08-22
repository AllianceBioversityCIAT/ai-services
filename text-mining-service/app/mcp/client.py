import os
import json
import uvicorn
from typing import Optional
from pydantic import BaseModel, Field
from mcp.client.stdio import stdio_client
from fastapi.middleware.cors import CORSMiddleware
from app.utils.s3.s3_util import upload_file_to_s3
from app.utils.logger.logger_util import get_logger
from mcp import ClientSession, StdioServerParameters, types
from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form


logger = get_logger()

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
    prompt: Optional[str] = Field(
        "Extract key points from this document", description="Specific instructions for document processing", examples=["Extract capacity development activities and their impact metrics"])


class UploadResponse(BaseModel):
    bucket: str = Field(..., description="S3 bucket where the file was uploaded")
    key: str = Field(..., description="Key (path) of the uploaded file in S3")
    status: str = Field(..., description="Status of the upload operation")
    message: str = Field(..., description="Detailed message about the upload operation")


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
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://d3djd7q7g7v7di.cloudfront.net", "description": "Production server"}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def handle_sampling_message(message: types.CreateMessageRequestParams) -> types.CreateMessageResult:
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            content="Processed by mock model", type="text"),
        model="mock-model",
        stopReason="endTurn"
    )


@app.post("/process",
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
        None, description="Object key in the S3 bucket. Optional if file is provided", examples=["reports/training-report-2024.pdf"]),
    file: Optional[UploadFile] = File(
        None, description="Document file to upload and process. Optional if key is provided", examples=["training-report-2024.pdf"]),
    prompt: Optional[str] = Form(
        "Extract key points from this document", description="Custom processing instructions for the AI model", examples=["Extract all capacity development activities, participant demographics, and training outcomes"]),
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
    - prompt: Specific instructions for document processing
    - environmentUrl: Environment for the service (e.g., production, test)

    Returns:
        dict: Result of the document processing
    """
    # Validate that at least one of key or file is provided
    if key is None and file is None:
        raise HTTPException(
            status_code=400,
            detail="Either 'key' or 'file' must be provided"
        )

    # If file is provided, upload it to S3 first
    if file is not None:
        try:
            # Read file content
            file_content = await file.read()

            # Use the filename as the key in S3
            filename = file.filename
            key = filename

            # Determine content type from file
            content_type = file.content_type

            # Upload file to S3
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

    # Process the document using the key (either provided or generated from file upload)
    logger.info(
        f"Processing document with key: {key} from bucket {bucketName}")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                await session.initialize()

                result = await session.call_tool(
                    "process_document",
                    arguments={
                        "bucket": bucketName,
                        "key": key,
                        "token": token,
                        "prompt": prompt,
                        "environmentUrl": environmentUrl
                    }
                )
                return result

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/prms/text_mining",
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
        None, description="Object key in the S3 bucket. Optional if file is provided", examples=["policies/climate-policy-2024.docx"]),
    file: Optional[UploadFile] = File(
        None, description="File to upload and process. Optional if key is provided", examples=["climate-policy-2024.docx"]),
    prompt: Optional[str] = Form(
        "Extract key points from this document", description="Specific instructions for document processing", examples=["Analyze policy changes, innovation developments, and capacity building activities with stakeholder details"]),
    environmentUrl: str = Form(
        ..., description="Target environment URL for PRMS authentication"
    )
):
    """
    Process a document stored in S3 using text mining techniques for PRMS project.
    You can either provide a key to an existing document in S3 or upload a new file.

    - bucketName: Name of the S3 bucket where the document is/will be located
    - token: Authentication token
    - key: Object key in the S3 bucket (required if no file is provided)
    - file: File to upload and process (required if no key is provided)
    - prompt: Specific instructions for document processing
    - environmentUrl: Environment for the service (e.g., production, test)

    Returns:
        dict: Result of the document processing for PRMS
    """
    # Validate that at least one of key or file is provided
    if key is None and file is None:
        raise HTTPException(
            status_code=400,
            detail="Either 'key' or 'file' must be provided"
        )

    # If file is provided, upload it to S3 first
    if file is not None:
        try:
            # Read file content
            file_content = await file.read()

            # Use the filename as the key in S3
            filename = file.filename
            key = filename

            # Determine content type from file
            content_type = file.content_type

            # Upload file to S3
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

    # Process the document using the key (either provided or generated from file upload)
    logger.info(
        f"Processing document for PRMS with key: {key} from bucket {bucketName}")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                await session.initialize()

                result = await session.call_tool(
                    "process_document_prms",
                    arguments={
                        "bucket": bucketName,
                        "key": key,
                        "token": token,
                        "prompt": prompt,
                        "environmentUrl": environmentUrl
                    }
                )
                return result

    except Exception as e:
        logger.error(f"Error processing document for PRMS: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
