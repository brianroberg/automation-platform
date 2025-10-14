"""Configuration management for the automation platform."""
import json
import logging
import os
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv  # type: ignore[import-not-found]

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Application configuration."""

    # Paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    CONFIG_DIR = PROJECT_ROOT / "config"
    DATA_DIR = PROJECT_ROOT / "data"
    LOGS_DIR = DATA_DIR / "logs"

    # Gmail API
    GMAIL_CREDENTIALS_FILE = PROJECT_ROOT / os.getenv("GMAIL_CREDENTIALS_FILE", "config/gmail_credentials.json")
    GMAIL_TOKEN_FILE = PROJECT_ROOT / os.getenv("GMAIL_TOKEN_FILE", "config/gmail_token.json")
    GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.labels"
    ]

    # LLM Configuration
    # LLM_MODEL should match the model loaded on the MLX server
    # MLX_SERVER_URL is read directly from environment by LLMClient
    LLM_MODEL = os.getenv("LLM_MODEL", "mlx-community/Llama-3.2-3B-Instruct-4bit")

    # Label Configuration
    LABEL_CONFIG_FILE = PROJECT_ROOT / os.getenv("LABEL_CONFIG_FILE", "config/labels.json")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = PROJECT_ROOT / os.getenv("LOG_FILE", "data/logs/email_triage.log")

    @classmethod
    def load_label_config(cls) -> dict[str, Any]:
        """Load label configuration from JSON file.

        Returns:
            Dictionary containing label definitions

        Raises:
            FileNotFoundError: If label config file doesn't exist
            json.JSONDecodeError: If label config is invalid JSON
        """
        logger.debug(f"Loading label configuration from {cls.LABEL_CONFIG_FILE}")

        if not cls.LABEL_CONFIG_FILE.exists():
            raise FileNotFoundError(
                f"Label configuration file not found: {cls.LABEL_CONFIG_FILE}"
            )

        with open(cls.LABEL_CONFIG_FILE, "r") as f:
            config = cast(dict[str, Any], json.load(f))

        logger.info(f"Loaded {len(config.get('labels', []))} label definitions")
        return config

    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug("Ensured all required directories exist")


# Ensure directories exist on import
Config.ensure_directories()
