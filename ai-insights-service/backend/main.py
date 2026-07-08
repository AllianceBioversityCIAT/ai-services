from mangum import Mangum
from dotenv import load_dotenv

load_dotenv()

# Strip static AWS keys before app imports create boto3 clients (Lambda uses IAM role).
from utils.config.config_util import clear_static_aws_credentials_from_environ

clear_static_aws_credentials_from_environ()

from api.main import app

handler = Mangum(app)