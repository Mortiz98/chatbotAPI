import logging
import sys
from pythonjsonlogger import jsonlogger
from core.config import settings


def setup_logging():
    """Configure JSON logging for production."""
    log_handler = logging.StreamHandler(sys.stdout)

    # JSON formatter for structured logging
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"levelname": "level", "asctime": "timestamp"},
    )
    log_handler.setFormatter(formatter)

    # Configure root logger
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)

    return logger


# Global logger instance
logger = setup_logging()
