"""Logging configuration shared by the application."""

import logging

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(log_level: str) -> None:
    """Configure the AgriGuard logger without adding duplicate handlers."""

    logger = logging.getLogger("agriguard")
    logger.setLevel(log_level)
    logger.propagate = False

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(console_handler)

    for existing_handler in logger.handlers:
        existing_handler.setLevel(log_level)
