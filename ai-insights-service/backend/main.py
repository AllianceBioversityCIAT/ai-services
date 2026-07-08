from mangum import Mangum
from dotenv import load_dotenv

load_dotenv()

# Drop INSIGHTS_AWS_* from env if present; Lambda IAM creds stay in AWS_ACCESS_KEY_ID (runtime-injected).
from utils.config.config_util import clear_static_aws_credentials_from_environ

clear_static_aws_credentials_from_environ()

from api.main import app

handler = Mangum(app)