import os
from dotenv import load_dotenv

load_dotenv()

S3 = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "aws_region": os.getenv("AWS_REGION", "us-east-1")
}

BR = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID_BR"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY_BR")
}

RABBITMQ = {
    "username": os.getenv("RABBITMQ_USERNAME"),
    "password": os.getenv("RABBITMQ_PASSWORD"),
    "host": os.getenv("RABBITMQ_HOST"),
    "port": os.getenv("RABBITMQ_PORT"),
    "protocol": os.getenv("RABBITMQ_PROTOCOL", "amqps"),
    "queue": os.getenv("RABBITMQ_QUEUE", "cola_test_python")
}

MS_NAME = os.getenv("MS_NAME", "Mining Microservice")
