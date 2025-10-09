"""Logging configuration for the automation platform."""
import logging
import sys
from pathlib import Path

from src.core.config import Config


def setup_logging(
    log_level: str | None = None,
    log_file: Path | None = None,
    include_stderr: bool = True
) -> None:
    """Configure logging for the application.

    Follows Unix philosophy:
    - Errors go to stderr (always)
    - Info/debug go to file only (unless debugging)
    - Quiet on success, loud on failure

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Defaults to Config.LOG_LEVEL
        log_file: Path to log file. Defaults to Config.LOG_FILE
        include_stderr: Whether to include stderr handler for ERROR+ messages
    """
    log_level = log_level or Config.LOG_LEVEL
    log_file = log_file or Config.LOG_FILE

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # File handler - all levels based on LOG_LEVEL
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Stderr handler - ERROR and above only (Unix philosophy: fail loudly)
    if include_stderr:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.ERROR)
        stderr_formatter = logging.Formatter('ERROR: %(message)s')
        stderr_handler.setFormatter(stderr_formatter)
        root_logger.addHandler(stderr_handler)

    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")
