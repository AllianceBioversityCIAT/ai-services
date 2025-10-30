from mangum import Mangum
from dotenv import load_dotenv
load_dotenv()

from app.mcp.client import app

handler = Mangum(app)