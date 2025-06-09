import os
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import json
from app.utils.logger.logger_util import get_logger
from app.utils.s3.s3_util import upload_file_to_s3
from typing import Optional

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
        ..., description="Name of the S3 bucket where the document is located")
    key: Optional[str] = Field(
        None, description="Object key in the S3 bucket. Optional if file is provided")
    token: str = Field(..., description="Authentication token")
    environmentUrl: str = Field(
                    ..., description="Environment for the service (e.g., production, test)")
    prompt: Optional[str] = Field("Extract key points from this document",
                                  description="Specific instructions for document processing")


class UploadResponse(BaseModel):
    bucket: str = Field(...,
                        description="S3 bucket where the file was uploaded")
    key: str = Field(..., description="Key (path) of the uploaded file in S3")
    status: str = Field(..., description="Status of the upload operation")
    message: str = Field(...,
                         description="Detailed message about the upload operation")


app = FastAPI(
    title="CGIAR Text Mining Service API",
    description="API for processing and text mining of documents stored in S3",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
          summary="Process document",
          description="Process a document stored in S3 using text mining techniques. You can either provide an S3 key for an existing document or upload a new file",
          responses={
              200: {"description": "Document processed successfully"},
              400: {"description": "Missing or invalid parameters"},
              500: {"description": "Error processing document"}
          })
async def process_document_endpoint(
    bucketName: str = Form(
        ..., description="Name of the S3 bucket where the document is/will be located"),
    token: str = Form(..., description="Authentication token"),
    key: Optional[str] = Form(
        None, description="Object key in the S3 bucket. Optional if file is provided"),
    file: Optional[UploadFile] = File(
        None, description="File to upload and process. Optional if key is provided"),
    prompt: Optional[str] = Form("Extract key points from this document",
                                 description="Specific instructions for document processing"),
    environmentUrl: str = Form(
        ..., description="Environment for the service (e.g., production, test)"
    )
):
    """
    Process a document stored in S3 using text mining techniques.
    You can either provide a key to an existing document in S3 or upload a new file.

    - **bucketName**: Name of the S3 bucket where the document is/will be located
    - **token**: Authentication token
    - **key**: Object key in the S3 bucket (required if no file is provided)
    - **file**: File to upload and process (required if no key is provided)
    - **prompt**: Specific instructions for document processing
    - **environmentUrl**: Environment for the service (e.g., production, test)

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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
