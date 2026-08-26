import os
from dotenv import load_dotenv

load_dotenv()

BR = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID_BR"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY_BR")
}

RABBITMQ = {
    "url": os.getenv("RABBITMQ_URL"),
    "email_queue_name": os.getenv("EMAIL_QUEUE_NAME"),
    "auth_username": os.getenv("MS_AUTH_USER"),
    "auth_password": os.getenv("MS_AUTH_PASSWORD"),
    "from_email": os.getenv("EMAIL_SENDER"),
    "from_name": os.getenv("EMAIL_SENDER_NAME"),
}