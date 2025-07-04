import os
from dotenv import load_dotenv

load_dotenv()

BR = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID_BR"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY_BR")
}

CLARISA_API_URL = os.getenv('CLARISA_API_URL')

SUPABASE_URL = os.getenv('SUPABASE_URL')

CLARISA_BEARER_TOKEN = os.getenv("CLARISA_BEARER_TOKEN")