import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

from core.config import settings

LOG_DIR = os.environ.get("LOG_DIR", "/logs")
LOG_LEVEL = getattr(logging, settings.log_level.upper(), logging.WARNING)


def setup_logging() -> None:
    """Configure centralized logging with daily file rotation + stdout."""
    os.makedirs(LOG_DIR, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    # Clear existing handlers to avoid duplicates on reload
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Stdout handler (for docker logs / dev console)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(LOG_LEVEL)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    # Daily rotating file handler
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, "aihelms.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(file_handler)

    # Error-only file (easier to spot issues)
    error_handler = TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, "error.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(error_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
