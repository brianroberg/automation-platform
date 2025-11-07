"""Gmail API client with OAuth authentication."""
import base64
import logging
from email.utils import getaddresses
from typing import Any, Iterable, Optional

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
        self._primary_email: str = ""
        self._user_addresses: set[str] = set()
        self._label_id_to_name: dict[str, str] = {}
        self._label_name_to_id: dict[str, str] = {}
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
        self._load_profile()
        self._refresh_label_cache()

    def _load_profile(self) -> None:
        """Load the authenticated user's profile information."""
        profile = self.service.users().getProfile(userId="me").execute()
        self._primary_email = profile.get("emailAddress", "").lower()
        self._user_addresses = Config.get_triage_addresses(self._primary_email)
        logger.debug("Loaded Gmail profile for %s", self._primary_email or "unknown user")

    def _refresh_label_cache(self) -> None:
        """Populate the label cache for translating IDs <-> names."""
        response = self.service.users().labels().list(userId="me").execute()
        labels = response.get("labels", [])
        self._label_id_to_name = {label["id"]: label["name"] for label in labels}
        self._label_name_to_id = {label["name"]: label["id"] for label in labels}
        logger.debug("Cached %s Gmail labels", len(self._label_id_to_name))
    def label_exists(self, label_name: str) -> bool:
        """Return True if Gmail already has the given label name."""
        if not self._label_name_to_id:
            self._refresh_label_cache()
        return label_name in self._label_name_to_id

    def get_inbox_candidates(
        self,
        max_results: int = 10,
        exclude_labels: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch inbox emails that are not already labeled by the workflow.

        Args:
            max_results: Maximum number of emails to fetch
            exclude_labels: Gmail label names that indicate the workflow already processed a message.

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
        logger.info(
            "Fetching up to %s inbox emails excluding labels %s",
            max_results,
            exclude_labels,
        )

        try:
            query = self._build_inbox_query(exclude_labels)

            results = self.service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results,
            ).execute()

            messages = results.get("messages", [])
            logger.info("Found %s inbox candidates", len(messages))

            if not messages:
                return []

            emails = []
            for msg in messages:
                email = self._get_email_details(msg["id"])
                emails.append(email)
                logger.debug("Fetched email %s: %s...", msg["id"], email["subject"][:50])

            return emails

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch inbox emails: {e}")
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

        sender_display = headers.get("From", "Unknown")
        sender = self._extract_address(sender_display)
        subject = headers.get("Subject", "(No Subject)")

        to_recipients = self._extract_addresses(headers.get("To", ""))
        cc_recipients = self._extract_addresses(headers.get("Cc", ""))
        bcc_recipients = self._extract_addresses(headers.get("Bcc", ""))

        # Extract body
        content = self._extract_body(msg["payload"])
        snippet = msg.get("snippet", "")
        label_ids = msg.get("labelIds", [])
        label_names = self._label_names_from_ids(label_ids)

        return {
            "id": msg_id,
            "sender": sender,
            "sender_display": sender_display,
            "subject": subject,
            "content": content,
            "snippet": snippet,
            "to": to_recipients,
            "cc": cc_recipients,
            "bcc": bcc_recipients,
            "label_ids": label_ids,
            "existing_labels": label_names,
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

    @staticmethod
    def _build_inbox_query(exclude_labels: Iterable[str] | None) -> str:
        """Build Gmail search query for inbox messages without specified labels."""
        query_parts = ["in:inbox", "has:nouserlabels"]
        if exclude_labels:
            sanitized = sorted(
                {
                    label.strip()
                    for label in exclude_labels
                    if isinstance(label, str) and label.strip()
                },
                key=lambda value: value.lower(),
            )
            for label in sanitized:
                query_parts.append(f'-label:{GmailClient._quote_label_for_query(label)}')
        return " ".join(query_parts)

    @staticmethod
    def _quote_label_for_query(label: str) -> str:
        """Quote a Gmail label so it can be used safely in the search query."""
        escaped = label.replace('"', r"\"")
        return f'"{escaped}"'

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
            if not self._label_name_to_id:
                self._refresh_label_cache()

            if label_name in self._label_name_to_id:
                return self._label_name_to_id[label_name]

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
            label_id = str(label["id"])
            self._label_name_to_id[label_name] = label_id
            self._label_id_to_name[label_id] = label_name
            return label_id

        except HttpError as e:
            logger.error(f"Gmail API error managing labels: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get or create label '{label_name}': {e}")
            raise

    def _extract_address(self, value: str | None) -> str:
        """Parse the first email address from a header value."""
        if not value:
            return ""
        addresses = getaddresses([value])
        if not addresses:
            return value.strip().lower()
        return addresses[0][1].strip().lower()

    def _extract_addresses(self, value: str | None) -> list[str]:
        """Parse all email addresses from a header."""
        if not value:
            return []
        return [
            addr.strip().lower()
            for _, addr in getaddresses([value])
            if addr.strip()
        ]

    def _label_names_from_ids(self, label_ids: list[str]) -> list[str]:
        """Translate Gmail label IDs to human-readable names."""
        if not label_ids:
            return []
        if not self._label_id_to_name:
            self._refresh_label_cache()
        names: list[str] = []
        for label_id in label_ids:
            name = self._label_id_to_name.get(label_id)
            if name:
                names.append(name)
        return names

    def get_primary_address(self) -> str:
        """Return the authenticated user's primary email address."""
        return self._primary_email

    def get_user_addresses(self) -> set[str]:
        """Return the set of addresses that should be treated as 'me'."""
        return set(self._user_addresses)
