from mangum import Mangum
from dotenv import load_dotenv
load_dotenv()

from api.main import app

handler = Mangum(app)