"""LLM client for email classification using OpenAI-compatible APIs.

Supports multiple providers:
- MLX server (recommended for both development and production)
- OpenAI (alternative)
- Any OpenAI-compatible API
"""
import logging
import os
from typing import Any

from openai import OpenAI

from src.core.config import Config

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM providers via OpenAI-compatible API.

    Designed primarily for MLX deployments, but works with any OpenAI-compatible API.
    """

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None
    ):
        """Initialize LLM client.

        Args:
            model: Model name (defaults to Config.LLM_MODEL or LLM_MODEL env var)
            base_url: API base URL (defaults to LLM_BASE_URL env var)
            api_key: API key (defaults to LLM_API_KEY env var, or "not-needed" for local servers)

        Raises:
            ValueError: If LLM_BASE_URL is not set

        Environment Variables:
            LLM_BASE_URL: Base URL for LLM API
                - MLX server (local): http://localhost:8080/v1
                - MLX server (over Tailscale): http://<tailscale-host>:8080/v1
                - OpenAI: https://api.openai.com/v1
            LLM_MODEL: Model identifier
                - MLX: mlx-community/Llama-3.2-3B-Instruct-4bit
                - OpenAI: gpt-4o-mini
            LLM_API_KEY: API key (not needed for MLX server)
        """
        self.model = model or os.getenv("LLM_MODEL") or Config.LLM_MODEL
        self.base_url = base_url or os.getenv("LLM_BASE_URL")

        # Try multiple env var names for API key (fallback to "not-needed" for local servers)
        self.api_key = (
            api_key
            or os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "not-needed"
        )

        if not self.base_url:
            raise ValueError(
                "LLM_BASE_URL environment variable must be set.\n"
                "Examples:\n"
                "  MLX (local): export LLM_BASE_URL=http://localhost:8080/v1\n"
                "  MLX (over Tailscale): export LLM_BASE_URL=http://<tailscale-host>:8080/v1"
            )

        # Determine provider from base_url for logging
        provider = "Unknown"
        if "openai" in self.base_url.lower():
            provider = "OpenAI"
        elif "localhost" in self.base_url or "127.0.0.1" in self.base_url:
            provider = "MLX (local)"
        elif ".alpha" in self.base_url or ".ts.net" in self.base_url:
            provider = "MLX (Tailscale)"

        logger.info(f"Initialized LLM client: provider={provider}, model={self.model}")

        # Initialize OpenAI client
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

        # Verify server is reachable
        self._verify_server_available()

    def _verify_server_available(self) -> None:
        """Verify the LLM API is reachable.

        Raises:
            RuntimeError: If API is not reachable
        """
        try:
            logger.debug(f"Verifying LLM API at {self.base_url} is reachable")
            models = self.client.models.list()
            available_models = [m.id for m in models.data]
            logger.debug(f"LLM API is reachable. Available models: {available_models}")

            # Warn if requested model not in available models
            # (but don't fail - some providers don't list all models)
            if available_models and self.model not in available_models:
                logger.warning(
                    f"Requested model '{self.model}' not found in available models. "
                    f"Available: {available_models[:5]}... "
                    f"(This may be okay - some providers don't list all models)"
                )
        except Exception as e:
            logger.error(f"Cannot connect to LLM API at {self.base_url}: {e}")
            raise RuntimeError(
                f"Cannot connect to LLM API at {self.base_url}. "
                f"Ensure the service is running and accessible. "
                f"Check your LLM_BASE_URL and LLM_API_KEY settings. "
                f"Error: {e}"
            )

    def classify_email(
        self,
        sender: str,
        subject: str,
        content: str,
        label_config: dict[str, Any]
    ) -> str:
        """Classify an email into one of the configured labels.

        Args:
            sender: Email sender address
            subject: Email subject line
            content: Email body content (plain text)
            label_config: Label configuration dictionary from Config.load_label_config()

        Returns:
            Label name as string

        Raises:
            RuntimeError: If LLM classification fails
        """
        logger.debug(f"Classifying email from {sender} with subject: {subject[:50]}...")

        # Build prompt with label definitions
        prompt = self._build_classification_prompt(sender, subject, content, label_config)

        try:
            # Call LLM via OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an email classification system."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.0  # Deterministic classification
            )

            classification = (response.choices[0].message.content or "").strip().lower()
            logger.debug(f"Raw LLM output: {classification}")

            # Validate classification is one of the configured labels
            valid_labels = [label["name"] for label in label_config["labels"]]

            if classification not in valid_labels:
                logger.warning(
                    f"LLM returned invalid label '{classification}'. "
                    f"Valid labels: {valid_labels}. Using default."
                )
                classification = label_config.get("default_label", valid_labels[0])

            logger.info(f"Classified email as: {classification}")
            return classification

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            raise RuntimeError(f"LLM classification failed: {e}")

    def _build_classification_prompt(
        self,
        sender: str,
        subject: str,
        content: str,
        label_config: dict[str, Any]
    ) -> str:
        """Build classification prompt for LLM.

        Args:
            sender: Email sender address
            subject: Email subject line
            content: Email body content
            label_config: Label configuration dictionary

        Returns:
            Formatted prompt string
        """
        # Build label descriptions
        label_descriptions = "\n".join([
            f"- {label['name']}: {label['description']}"
            for label in label_config["labels"]
        ])

        # Truncate content if too long (keep first 1000 chars)
        content_preview = content[:1000] + ("..." if len(content) > 1000 else "")

        prompt = (
            "Classify the following email into exactly one of these categories:\n\n"
            f"{label_descriptions}\n\n"
            "Email Details:\n"
            f"From: {sender}\n"
            f"Subject: {subject}\n"
            f"Content: {content_preview}\n\n"
            "Respond with ONLY the category name, nothing else. "
            "Choose the single most appropriate category."
        )

        return prompt
