import os
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from fastapi import FastAPI, HTTPException
import uvicorn
import json
from app.utils.logger.logger_util import get_logger

logger = get_logger()

server_params = StdioServerParameters(
    command="python",
    args=[os.path.join(os.path.dirname(__file__), "server.py")],
    cwd=os.path.dirname(os.path.abspath(__file__)),
    env={"PYTHONPATH": os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))}
)

app = FastAPI()


async def handle_sampling_message(message: types.CreateMessageRequestParams) -> types.CreateMessageResult:
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            content="Processed by mock model", type="text"),
        model="mock-model",
        stopReason="endTurn"
    )


@app.post("/process")
async def process_document_endpoint(data: dict):
    bucket = data.get("bucketName")
    key = data.get("key")
    credentials = data.get("credentials")
    prompt = data.get("prompt", "Extract key points from this document")

    if not bucket or not key or not credentials:
        raise HTTPException(
            status_code=400,
            detail="Missing 'bucketName', 'key', or 'credentials'"
        )

    logger.info(f"Received request to process {key} from bucket {bucket}")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                await session.initialize()

                result = await session.call_tool(
                    "process_document",
                    arguments={
                        "bucket": bucket,
                        "key": key,
                        "credentials": json.dumps(credentials),
                        "prompt": prompt
                    }
                )
                return result

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
