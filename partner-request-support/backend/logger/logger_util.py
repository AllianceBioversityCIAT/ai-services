import os
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

# In Lambda use only stdout (CloudWatch Logs). Locally also write to data/logs.
IS_LAMBDA = bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
log_format = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)

logger = logging.getLogger("pr_support")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)

if not IS_LAMBDA:
    logs_dir = Path(__file__).parent.parent / "data" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        logs_dir / "app.log", maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)


def get_logger():
    return logger