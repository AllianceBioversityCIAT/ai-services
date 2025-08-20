from mangum import Mangum
from app.api.main import app
from dotenv import load_dotenv

load_dotenv()

handler = Mangum(app)