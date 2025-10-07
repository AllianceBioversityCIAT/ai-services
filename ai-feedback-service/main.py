"""
Entry point for AWS Lambda deployment of the AI Feedback Service.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# 1) Cargar .env temprano
DOTENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=DOTENV_PATH, override=False)

# 2) Quitar comillas accidentales en envs AWS
def _strip_quotes(var: str):
    v = os.environ.get(var)
    if v and len(v) >= 2 and (
        (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'"))
    ):
        os.environ[var] = v[1:-1]

for _k in [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
    "AWS_ACCESS_KEY_ID_BR",
    "AWS_SECRET_ACCESS_KEY_BR",
]:
    _strip_quotes(_k)

# 3) Normalizar región para boto3/SDKs
if not os.environ.get("AWS_DEFAULT_REGION") and os.environ.get("AWS_REGION"):
    os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

# 4) (Opcional) Depurar credenciales en runtime
if os.environ.get("DEBUG_AWS_CREDS") == "1":
    import boto3
    logger = logging.getLogger("bootstrap")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%Y-%m-%d %H:%M:%S %(levelname)s %(name)s - %(message)s"))
        logger.addHandler(h)

    try:
        sess = boto3.Session()
        creds = sess.get_credentials()
        logger.info("Cred provider: %s", getattr(creds, "method", "unknown"))
        sts = sess.client("sts", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        ident = sts.get_caller_identity()
        logger.info("CallerIdentity: %s", ident)
    except Exception as e:
        logger.error("AWS creds debug failed: %s", e)

# 5) Importar la app sólo después de preparar el entorno
from mangum import Mangum
from app.api.main import app

handler = Mangum(app)

# --- NOTA ---
# - Para Dynamo/S3/etc. boto3 usará AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN
#   y AWS_DEFAULT_REGION cargados arriba.
# - Para Bedrock, usa explícitamente las credenciales BR SIN contaminar las globales, por ejemplo:
#
#   import boto3
#   bedrock = boto3.client(
#       "bedrock-runtime",
#       region_name=os.environ["AWS_DEFAULT_REGION"],
#       aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID_BR"),
#       aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY_BR"),
#       aws_session_token=os.environ.get("AWS_SESSION_TOKEN_BR"),  # si aplica
#   )
