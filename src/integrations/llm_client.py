"""LLM client for email classification using OpenAI-compatible MLX server."""
import logging
import os
from typing import Any

from openai import OpenAI

from src.core.config import Config

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with MLX LLM server via OpenAI-compatible API."""

    def __init__(self, model: str | None = None, base_url: str | None = None):
        """Initialize LLM client.

        Args:
            model: Model name (defaults to Config.LLM_MODEL)
            base_url: MLX server URL (defaults to MLX_SERVER_URL env var)

        Raises:
            ValueError: If MLX_SERVER_URL is not set
        """
        self.model = model or Config.LLM_MODEL
        self.base_url = base_url or os.getenv("MLX_SERVER_URL")

        if not self.base_url:
            raise ValueError(
                "MLX_SERVER_URL environment variable must be set. "
                "Example: export MLX_SERVER_URL=http://100.64.0.123:8080"
            )

        logger.info(f"Initialized LLM client with model={self.model}, server={self.base_url}")

        # Initialize OpenAI client pointing to MLX server
        self.client = OpenAI(
            base_url=f"{self.base_url}/v1",
            api_key="not-needed"  # MLX server doesn't require authentication
        )

        # Verify server is reachable
        self._verify_server_available()

    def _verify_server_available(self) -> None:
        """Verify the MLX server is reachable.

        Raises:
            RuntimeError: If server is not reachable
        """
        try:
            logger.debug(f"Verifying MLX server at {self.base_url} is reachable")
            models = self.client.models.list()
            logger.debug(f"MLX server is reachable. Available models: {[m.id for m in models.data]}")
        except Exception as e:
            logger.error(f"Cannot connect to MLX server at {self.base_url}: {e}")
            raise RuntimeError(
                f"Cannot connect to MLX server at {self.base_url}. "
                f"Ensure the server is running and accessible. Error: {e}"
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
