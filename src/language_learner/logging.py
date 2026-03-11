"""Logging configuration for Language Learner Assistant.

This module sets up structured logging for the application.
"""

import logging
import sys


def setup_logging(level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    """Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("language_learner")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        try:
            from logging.handlers import RotatingFileHandler

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
            )
            file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except ImportError:
            logger.warning(
                "RotatingFileHandler not available, using regular FileHandler"
            )
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logging()


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Optional logger name

    Returns:
        logging.Logger: Logger instance
    """
    if name:
        return logger.getChild(name)
    return logger
