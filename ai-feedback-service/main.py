# main.py
"""
Entry point for AWS Lambda deployment of the AI Feedback Service.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# --- Cargar .env muy temprano ---
DOTENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=DOTENV_PATH, override=False)

# --- Normalizar región y limpiar comillas ---
def _strip_quotes(var: str):
    v = os.environ.get(var)
    if v and len(v) >= 2 and ((v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'"))):
        os.environ[var] = v[1:-1]

for k in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_REGION", "AWS_DEFAULT_REGION"]:
    _strip_quotes(k)

if not os.environ.get("AWS_DEFAULT_REGION") and os.environ.get("AWS_REGION"):
    os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

# --- (Opcional) Debug de credenciales, ANTES de importar la app ---
if os.environ.get("DEBUG_AWS_CREDS") == "1":
    import boto3
    try:
        sess = boto3.Session(region_name=os.environ["AWS_DEFAULT_REGION"])
        creds = sess.get_credentials()
        print("Cred provider:", getattr(creds, "method", "unknown"))
        sts = sess.client("sts")
        print("CallerIdentity:", sts.get_caller_identity())
    except Exception as e:
        print("AWS creds debug failed:", repr(e))

# --- Recién ahora importamos la app (que usa boto3) ---
from mangum import Mangum
from app.api.main import app

handler = Mangum(app)
