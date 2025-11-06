"""Configuration management for the automation platform."""
import json
import logging
import os
from pathlib import Path
from typing import Any, cast

import yaml

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
    GMAIL_CREDENTIALS_FILE = PROJECT_ROOT / os.getenv(
        "GMAIL_CREDENTIALS_FILE",
        "config/gmail_credentials.json",
    )
    GMAIL_TOKEN_FILE = PROJECT_ROOT / os.getenv("GMAIL_TOKEN_FILE", "config/gmail_token.json")
    GMAIL_SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/gmail.modify"
    ]

    # LLM Configuration
    # LLM_MODEL should match the model loaded on the MLX server
    # MLX_SERVER_URL is read directly from environment by LLMClient
    LLM_MODEL = os.getenv("LLM_MODEL", "mlx-community/Llama-3.2-3B-Instruct-4bit")

    # Label Configuration
    LABEL_CONFIG_FILE = PROJECT_ROOT / os.getenv("LABEL_CONFIG_FILE", "config/labels.json")
    DETERMINISTIC_RULES_FILE = PROJECT_ROOT / os.getenv(
        "DETERMINISTIC_RULES_FILE",
        "config/deterministic_rules.yaml",
    )

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
    def load_deterministic_rules(cls) -> list[dict[str, Any]]:
        """Load deterministic rule configuration from YAML."""
        path = cls.DETERMINISTIC_RULES_FILE
        logger.debug("Loading deterministic rules from %s", path)

        if not path.exists():
            logger.warning(
                "Deterministic rule file not found at %s; proceeding without rules",
                path,
            )
            return []

        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        rules = data.get("rules", [])
        if not isinstance(rules, list):
            raise ValueError("Deterministic rule file must define a top-level 'rules' list.")

        logger.info("Loaded %s deterministic rules", len(rules))
        # Future enhancement: allow condition modules to inspect received date, attachments, etc.
        return rules

    @classmethod
    def get_triage_addresses(cls, primary_email: str | None = None) -> set[str]:
        """Return the set of addresses that represent the current user."""
        addresses: set[str] = set()
        if primary_email:
            addresses.add(primary_email.strip().lower())

        extra = os.getenv("TRIAGE_EMAILS")
        if extra:
            for entry in extra.split(","):
                normalized = entry.strip().lower()
                if normalized:
                    addresses.add(normalized)

        return addresses

    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug("Ensured all required directories exist")


# Ensure directories exist on import
Config.ensure_directories()
