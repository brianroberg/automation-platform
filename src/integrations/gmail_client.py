"""Gmail API client with OAuth authentication."""
import base64
import logging
from typing import Any, Optional

from google.auth.transport.requests import Request  # type: ignore[import-untyped]
from google.oauth2.credentials import Credentials  # type: ignore[import-untyped]
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-untyped]
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

from src.core.config import Config

logger = logging.getLogger(__name__)


class GmailClient:
    """Client for interacting with Gmail API with restricted scopes."""

    SCOPES = Config.GMAIL_SCOPES

    def __init__(self) -> None:
        """Initialize Gmail client with OAuth authentication."""
        self.creds: Optional[Credentials] = None
        self.service: Any = None  # googleapiclient.discovery.Resource type is not easily importable
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Gmail API using OAuth.

        Uses restricted scopes:
        - gmail.readonly: Read emails only
        - gmail.labels: Manage labels only

        No permission to send, delete, or modify email content.

        Raises:
            FileNotFoundError: If credentials file not found
            Exception: If authentication fails
        """
        logger.debug("Authenticating with Gmail API")

        # Check if we have saved credentials
        if Config.GMAIL_TOKEN_FILE.exists():
            logger.debug(f"Loading saved credentials from {Config.GMAIL_TOKEN_FILE}")
            self.creds = Credentials.from_authorized_user_file(
                str(Config.GMAIL_TOKEN_FILE),
                self.SCOPES
            )

        # If no valid credentials, authenticate
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired credentials")
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}. Starting new OAuth flow.")
                    self.creds = None

            if not self.creds:
                if not Config.GMAIL_CREDENTIALS_FILE.exists():
                    logger.error(f"Credentials file not found: {Config.GMAIL_CREDENTIALS_FILE}")
                    raise FileNotFoundError(
                        f"Gmail credentials not found at {Config.GMAIL_CREDENTIALS_FILE}. "
                        "Please download OAuth credentials from Google Cloud Console."
                    )

                logger.info("Starting OAuth flow (browser will open)")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(Config.GMAIL_CREDENTIALS_FILE),
                    self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save credentials for next run
            logger.debug(f"Saving credentials to {Config.GMAIL_TOKEN_FILE}")
            with open(Config.GMAIL_TOKEN_FILE, "w") as token:
                token.write(self.creds.to_json())

        # Build service
        logger.info("Building Gmail API service")
        self.service = build("gmail", "v1", credentials=self.creds)
        logger.info("Successfully authenticated with Gmail API")

    def get_unread_emails(self, max_results: int = 10) -> list[dict[str, Any]]:
        """Fetch unread emails from inbox.

        Args:
            max_results: Maximum number of emails to fetch

        Returns:
            List of email dictionaries with keys:
                - id: Email ID
                - sender: Sender email address
                - subject: Email subject
                - content: Email body (plain text)
                - snippet: Short preview

        Raises:
            HttpError: If API call fails
        """
        logger.info(f"Fetching up to {max_results} unread emails")

        try:
            # Search for unread emails in inbox
            results = self.service.users().messages().list(
                userId="me",
                q="is:unread in:inbox",
                maxResults=max_results
            ).execute()

            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} unread emails")

            if not messages:
                return []

            # Fetch full details for each message
            emails = []
            for msg in messages:
                email = self._get_email_details(msg["id"])
                emails.append(email)
                logger.debug(f"Fetched email {msg['id']}: {email['subject'][:50]}...")

            return emails

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch unread emails: {e}")
            raise

    def _get_email_details(self, msg_id: str) -> dict[str, Any]:
        """Get detailed information for a specific email.

        Args:
            msg_id: Gmail message ID

        Returns:
            Dictionary with email details
        """
        msg = self.service.users().messages().get(
            userId="me",
            id=msg_id,
            format="full"
        ).execute()

        # Extract headers
        headers = {
            header["name"]: header["value"]
            for header in msg["payload"]["headers"]
        }

        sender = headers.get("From", "Unknown")
        subject = headers.get("Subject", "(No Subject)")

        # Extract body
        content = self._extract_body(msg["payload"])
        snippet = msg.get("snippet", "")

        return {
            "id": msg_id,
            "sender": sender,
            "subject": subject,
            "content": content,
            "snippet": snippet
        }

    def _extract_body(self, payload: dict[str, Any]) -> str:
        """Extract plain text body from email payload.

        Args:
            payload: Email payload from Gmail API

        Returns:
            Plain text email body
        """
        # Check if body is directly in payload
        if "body" in payload and "data" in payload["body"]:
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        # Check parts for text/plain
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part["body"]:
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")

                # Recursively check nested parts
                if "parts" in part:
                    result = self._extract_body(part)
                    if result:
                        return result

        return ""

    def apply_label(self, msg_id: str, label_name: str) -> None:
        """Apply a label to an email.

        Creates the label if it doesn't exist.

        Args:
            msg_id: Gmail message ID
            label_name: Name of label to apply

        Raises:
            HttpError: If API call fails
        """
        logger.debug(f"Applying label '{label_name}' to message {msg_id}")

        try:
            # Get or create label
            label_id = self._get_or_create_label(label_name)

            # Apply label
            self.service.users().messages().modify(
                userId="me",
                id=msg_id,
                body={"addLabelIds": [label_id]}
            ).execute()

            logger.info(f"Applied label '{label_name}' to message {msg_id}")

        except HttpError as e:
            logger.error(f"Gmail API error applying label: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to apply label '{label_name}' to message {msg_id}: {e}")
            raise

    def _get_or_create_label(self, label_name: str) -> str:
        """Get label ID, creating it if it doesn't exist.

        Args:
            label_name: Name of label

        Returns:
            Label ID
        """
        try:
            # List existing labels
            results = self.service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])

            # Check if label exists
            for label in labels:
                if label["name"] == label_name:
                    logger.debug(f"Found existing label '{label_name}' with ID {label['id']}")
                    return str(label["id"])

            # Create new label
            logger.info(f"Creating new label '{label_name}'")
            label = self.service.users().labels().create(
                userId="me",
                body={
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show"
                }
            ).execute()

            logger.info(f"Created label '{label_name}' with ID {label['id']}")
            return str(label["id"])

        except HttpError as e:
            logger.error(f"Gmail API error managing labels: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get or create label '{label_name}': {e}")
            raise
