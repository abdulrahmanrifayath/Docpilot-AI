import logging
import sys
from typing import Optional


def setup_logging(log_level: Optional[str] = "INFO") -> logging.Logger:
    """Configures structured application logging."""
    numeric_level = getattr(logging, (log_level or "INFO").upper(), logging.INFO)

    log_format = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # DocPilot application logger
    app_logger = logging.getLogger("docpilot")
    app_logger.setLevel(numeric_level)

    return app_logger


logger = setup_logging()
