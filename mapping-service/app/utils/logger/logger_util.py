import os
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler


def _resolve_logs_dir() -> Path:
    candidate_dirs = []
    env_dir = os.environ.get("LOGS_DIR")
    if env_dir:
        candidate_dirs.append(Path(env_dir))

    repo_logs_dir = Path(__file__).resolve().parents[3] / "data" / "logs"
    candidate_dirs.append(repo_logs_dir)
    candidate_dirs.append(Path("/tmp/mapping-service/logs"))

    for directory in candidate_dirs:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return directory
        except OSError:
            continue

    raise RuntimeError("Unable to create logs directory for mapping-service logger")


logs_dir = _resolve_logs_dir()

logger = logging.getLogger("mapping-service")
logger.setLevel(logging.DEBUG)

log_format = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)

if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        logs_dir / "app.log", maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)


def get_logger():
    return logger
