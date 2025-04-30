import os
from dotenv import load_dotenv

load_dotenv()

is_prod = os.getenv('IS_PROD', 'false').lower() == 'true'

if is_prod:
    from app.mcp.client import app
    from mangum import Mangum

    handler = Mangum(app)
else:
    import uvicorn

    if __name__ == "__main__":
        uvicorn.run("app.mcp.client:app", host="0.0.0.0",
                    port=8000, reload=True)
