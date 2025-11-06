# Email Classification MVP - Phases 3-5 Implementation Plan

## Overview

Complete the Email Classification MVP by implementing Gmail integration, email triage workflow, and comprehensive testing. This plan builds on the completed Phases 1-2 (project foundation and LLM integration) to deliver a working end-to-end email classification system.

## Current State Analysis

### Completed (Phases 1-2) ✅

**Phase 1: Project Foundation**
- Project structure created (`src/`, `config/`, `tests/`, etc.)
- Configuration module (`src/core/config.py`) with environment variable management
- Logging utilities (`src/utils/logging.py`) following Unix philosophy
- Label configuration system (`config/labels.json`)
- All dependencies installed and verified

**Phase 2: LLM Integration**
- LLM client (`src/integrations/llm_client.py`) fully implemented
- Support for MLX (primary) and other OpenAI-compatible APIs via a unified client
- Email classification with structured prompts
- Label validation with fallback to default
- 7 comprehensive unit tests passing
- Production-ready error handling

**Key Files Exist:**
- `src/core/config.py` - Configuration management
- `src/integrations/llm_client.py` - LLM classification client
- `src/utils/logging.py` - Logging setup
- `tests/test_llm_client.py` - LLM client tests
- `config/labels.json` - Label definitions
- `.env.example` - Environment configuration template

### Not Yet Implemented (Phases 3-5) ⏭️

**Phase 3: Gmail Integration**
- Gmail API client (`src/integrations/gmail_client.py`)
- OAuth authentication flow
- Email fetching and parsing
- Label management

**Phase 4: Email Triage Workflow**
- Workflow orchestration (`src/workflows/email_triage.py`)
- CLI entry point
- End-to-end email processing

**Phase 5: Testing & Documentation**
- Configuration tests
- Integration tests
- Updated documentation
- Performance validation

## Desired End State

A working command-line MVP that:

1. ✅ Authenticates with Gmail API using OAuth (restricted scopes: `gmail.readonly` + `gmail.labels`)
2. ✅ Fetches unread emails from inbox
3. ✅ Classifies emails using an MLX-hosted LLM reachable from both development and production environments
4. ✅ Applies appropriate Gmail labels based on classification
5. ✅ Handles errors gracefully with comprehensive logging
6. ✅ Supports customizable label configurations

**Verification**: Running `python -m src.workflows.email_triage` successfully classifies and labels unread emails using the MLX server.

## What We're NOT Doing

Following the MVP-first philosophy, these features are explicitly deferred:

- ❌ Docker containerization
- ❌ macOS launchd scheduling
- ❌ FastAPI web interface
- ❌ Multiple workflow types
- ❌ Advanced retry logic
- ❌ Monitoring/alerting systems
- ❌ macOS notifications or menu bar integration
- ❌ Batch processing optimization
- ❌ Parallel email processing

**Focus**: Get email classification working end-to-end before adding infrastructure.

## Implementation Approach

Build in sequential phases where each phase is fully working before moving to the next:

1. **Phase 3**: Gmail Integration - OAuth, email fetching, label management
2. **Phase 4**: Email Triage Workflow - Orchestrate Gmail + LLM clients
3. **Phase 5**: Testing & Documentation - Polish and prepare for production

Each phase includes both automated and manual verification before proceeding.

---

## Phase 3: Gmail Integration

### Overview

Implement Gmail API client with OAuth authentication (restricted scopes), email fetching, and label management. This phase establishes the connection to Gmail and provides the data source for email classification.

### Changes Required:

#### 1. Gmail Client Implementation

**File**: `src/integrations/gmail_client.py`
**Changes**: Create Gmail API wrapper with restricted OAuth scopes

```python
"""Gmail API client with OAuth authentication."""
import base64
import logging
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.core.config import Config

logger = logging.getLogger(__name__)


class GmailClient:
    """Client for interacting with Gmail API with restricted scopes."""

    SCOPES = Config.GMAIL_SCOPES

    def __init__(self):
        """Initialize Gmail client with OAuth authentication."""
        self.creds = None
        self.service = None
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
                    return label["id"]

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
            return label["id"]

        except HttpError as e:
            logger.error(f"Gmail API error managing labels: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get or create label '{label_name}': {e}")
            raise
```

#### 2. Gmail Client Tests

**File**: `tests/test_gmail_client.py`
**Changes**: Create unit tests for Gmail client

```python
"""Tests for Gmail client."""
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.integrations.gmail_client import GmailClient


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service."""
    service = MagicMock()
    return service


@patch("src.integrations.gmail_client.build")
@patch("src.integrations.gmail_client.Credentials")
@patch("pathlib.Path.exists")
def test_gmail_client_uses_saved_token(mock_exists, mock_creds, mock_build):
    """Test client uses saved token if available."""
    mock_exists.return_value = True
    mock_creds.from_authorized_user_file.return_value = MagicMock(valid=True)

    client = GmailClient()

    assert client.service is not None
    mock_creds.from_authorized_user_file.assert_called_once()


@patch("src.integrations.gmail_client.build")
@patch("src.integrations.gmail_client.InstalledAppFlow")
@patch("pathlib.Path.exists")
def test_gmail_client_creates_new_token(mock_exists, mock_flow, mock_build):
    """Test client creates new token via OAuth flow."""
    # Token doesn't exist, credentials do
    def exists_side_effect():
        # First call checks token (doesn't exist), second checks credentials (exists)
        if mock_exists.call_count == 1:
            return False
        return True

    mock_exists.side_effect = exists_side_effect

    mock_flow_instance = MagicMock()
    mock_flow.from_client_secrets_file.return_value = mock_flow_instance
    mock_creds = MagicMock()
    mock_flow_instance.run_local_server.return_value = mock_creds

    with patch("builtins.open", mock_open()):
        client = GmailClient()

    assert client.service is not None
    mock_flow_instance.run_local_server.assert_called_once()


@patch("src.integrations.gmail_client.build")
@patch("src.integrations.gmail_client.Credentials")
@patch("pathlib.Path.exists")
def test_get_unread_emails(mock_exists, mock_creds, mock_build, mock_gmail_service):
    """Test fetching unread emails."""
    mock_exists.return_value = True
    mock_creds.from_authorized_user_file.return_value = MagicMock(valid=True)
    mock_build.return_value = mock_gmail_service

    # Mock API responses
    mock_gmail_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "123"}, {"id": "456"}]
    }

    mock_gmail_service.users().messages().get().execute.return_value = {
        "id": "123",
        "snippet": "Test snippet",
        "payload": {
            "headers": [
                {"name": "From", "value": "test@example.com"},
                {"name": "Subject", "value": "Test Subject"}
            ],
            "body": {"data": "VGVzdCBib2R5"}  # base64 "Test body"
        }
    }

    client = GmailClient()
    emails = client.get_unread_emails(max_results=10)

    assert len(emails) == 2
    assert emails[0]["subject"] == "Test Subject"


@patch("src.integrations.gmail_client.build")
@patch("src.integrations.gmail_client.Credentials")
@patch("pathlib.Path.exists")
def test_apply_label_creates_if_not_exists(mock_exists, mock_creds, mock_build, mock_gmail_service):
    """Test applying label creates it if it doesn't exist."""
    mock_exists.return_value = True
    mock_creds.from_authorized_user_file.return_value = MagicMock(valid=True)
    mock_build.return_value = mock_gmail_service

    # Mock label list (label doesn't exist)
    mock_gmail_service.users().labels().list().execute.return_value = {
        "labels": []
    }

    # Mock label creation
    mock_gmail_service.users().labels().create().execute.return_value = {
        "id": "Label_1",
        "name": "test-label"
    }

    client = GmailClient()
    client.apply_label("msg_123", "test-label")

    # Verify label was created
    mock_gmail_service.users().labels().create.assert_called_once()

    # Verify label was applied
    mock_gmail_service.users().messages().modify.assert_called_once()


@patch("src.integrations.gmail_client.build")
@patch("src.integrations.gmail_client.Credentials")
@patch("pathlib.Path.exists")
def test_get_unread_emails_returns_empty_list_when_no_emails(mock_exists, mock_creds, mock_build, mock_gmail_service):
    """Test fetching unread emails when none exist."""
    mock_exists.return_value = True
    mock_creds.from_authorized_user_file.return_value = MagicMock(valid=True)
    mock_build.return_value = mock_gmail_service

    # Mock empty response
    mock_gmail_service.users().messages().list().execute.return_value = {}

    client = GmailClient()
    emails = client.get_unread_emails(max_results=10)

    assert len(emails) == 0
```

#### 3. Gmail Setup Documentation

**File**: `docs/gmail_setup.md`
**Changes**: Create comprehensive Gmail API setup guide

```markdown
# Gmail API Setup Guide

## Prerequisites

- Google account with Gmail
- Access to Google Cloud Console

## Step-by-Step Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a Project" → "New Project"
3. Name it "Automation Platform" (or your preference)
4. Click "Create"
5. Wait for project creation to complete

### 2. Enable Gmail API

1. In the Cloud Console, navigate to "APIs & Services" → "Library"
2. Search for "Gmail API"
3. Click on "Gmail API"
4. Click "Enable"
5. Wait for API to be enabled

### 3. Configure OAuth Consent Screen

1. Navigate to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type (unless you have Google Workspace)
3. Click "Create"
4. Fill in required fields:
   - **App name**: "Automation Platform"
   - **User support email**: (your email)
   - **Developer contact**: (your email)
5. Click "Save and Continue"

6. Click "Add or Remove Scopes"
7. Add these scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.labels`
8. Click "Update" → "Save and Continue"

9. Add your email as a test user:
   - Click "Add Users"
   - Enter your Gmail address
   - Click "Add"
10. Click "Save and Continue"

11. Review and click "Back to Dashboard"

### 4. Create OAuth Credentials

1. Navigate to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: "Desktop app"
4. Name: "Automation Platform Desktop Client"
5. Click "Create"
6. Click "Download JSON" on the popup (or download from credentials list)
7. Save the file as `config/gmail_credentials.json` in your project

### 5. First-Time Authentication

When you run the email triage workflow for the first time:

1. A browser window will open automatically
2. Sign in with your Google account
3. You may see a warning "Google hasn't verified this app"
   - Click "Advanced"
   - Click "Go to Automation Platform (unsafe)"
4. Review the permissions (readonly + labels only)
5. Click "Allow"
6. You should see "The authentication flow has completed"
7. Close the browser window
8. The token is saved to `config/gmail_token.json` for future use

## Security Notes

**Restricted Scopes**: The application only has permission to:
- ✅ Read your emails (cannot modify or delete)
- ✅ Manage labels (create and apply labels)

**No Send Permission**: The application CANNOT:
- ❌ Send emails on your behalf
- ❌ Delete emails
- ❌ Modify email content
- ❌ Access gmail.compose or gmail.send

**Local Storage**:
- Credentials stored locally in `config/` directory
- Never committed to git (listed in `.gitignore`)
- Token automatically refreshes when expired

## Troubleshooting

### "Access blocked: This app's request is invalid"

**Cause**: OAuth consent screen configuration issue

**Solution**:
1. Ensure app is in "Testing" mode (not "Production")
2. Verify your email is added as a test user
3. Confirm both required scopes are added
4. Try clearing browser cache and retrying

### "Credentials file not found"

**Cause**: OAuth credentials not in correct location

**Solution**:
1. Download OAuth credentials JSON from Google Cloud Console
2. Rename to `gmail_credentials.json` (exact name)
3. Place in `config/` directory (not project root)
4. Verify path: `config/gmail_credentials.json`

### "Redirect URI mismatch"

**Cause**: Wrong OAuth client type

**Solution**:
1. Delete existing OAuth credential
2. Create new credential
3. Select "Desktop app" (not "Web application")

### Browser doesn't open during authentication

**Cause**: Running in headless environment (SSH, Codespaces without port forwarding)

**Solution** for GitHub Codespaces:
1. The OAuth flow will print a URL to the terminal
2. Copy the URL
3. Open it in your local browser
4. Complete authentication
5. The token will be saved automatically

### "Token refresh failed"

**Cause**: Saved token is invalid or revoked

**Solution**:
1. Delete `config/gmail_token.json`
2. Run workflow again to re-authenticate
3. Complete OAuth flow in browser

## Revoking Access

To revoke the application's access to your Gmail:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Scroll to "Third-party apps with account access"
3. Find "Automation Platform"
4. Click "Remove Access"
5. Delete `config/gmail_token.json` from your project

## Rate Limits

Gmail API has quotas:
- **Free tier**: 1 billion quota units per day
- **Cost per operation**:
  - Read message: 5 units
  - List messages: 5 units
  - Modify message: 5 units

**For reference**: Processing 100 emails = ~1,500 units (well within free tier)

## Next Steps

After completing Gmail setup:
1. ✅ Configure MLX server connection in `.env`
2. ✅ Test Phase 3 success criteria
3. ✅ Proceed to Phase 4 (Email Triage Workflow)
```

### Success Criteria:

#### Automated Verification:
- [x] Gmail client imports successfully: `python -c "from src.integrations.gmail_client import GmailClient"`
- [x] All tests pass: `pytest tests/test_gmail_client.py -v`
- [x] Type checking passes: `mypy src/integrations/gmail_client.py`
- [x] No linting errors: `ruff check src/integrations/gmail_client.py`

#### Manual Verification:

**Prerequisites Setup:**
- [ ] Google Cloud project created
- [ ] Gmail API enabled
- [ ] OAuth consent screen configured (External, Testing mode)
- [ ] Your email added as test user
- [ ] OAuth credentials downloaded to `config/gmail_credentials.json`

**Authentication Testing:**
- [ ] Can instantiate `GmailClient()` without errors
- [ ] OAuth flow opens browser automatically
- [ ] Can complete authentication (click "Allow" after viewing permissions)
- [ ] Token saved to `config/gmail_token.json`
- [ ] Subsequent runs use saved token (no browser popup)

**Functionality Testing:**
- [ ] Can fetch unread emails:
  ```python
  from src.integrations.gmail_client import GmailClient
  client = GmailClient()
  emails = client.get_unread_emails(max_results=5)
  print(f"Found {len(emails)} emails")
  for email in emails:
      print(f"- {email['subject']}")
  ```
- [ ] Email data structure is correct (id, sender, subject, content, snippet)
- [ ] Can create and apply labels:
  ```python
  if emails:
      client.apply_label(emails[0]['id'], 'test-label')
      print("Label applied successfully")
  ```
- [ ] Label appears in Gmail web interface
- [ ] Token automatically refreshes when expired (test after several days)

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation that Gmail integration works correctly with your account before proceeding to Phase 4.

---

## Phase 4: Email Triage Workflow

### Overview

Orchestrate Gmail and LLM clients into a working end-to-end email classification workflow. This phase connects all components and provides the command-line interface for running email triage.

### Changes Required:

#### 1. Email Triage Workflow

**File**: `src/workflows/email_triage.py`
**Changes**: Create main workflow orchestration

```python
"""Email triage workflow - classifies and labels Gmail emails using LLM."""
import logging
import sys
from typing import Any

from src.core.config import Config
from src.integrations.gmail_client import GmailClient
from src.integrations.llm_client import LLMClient
from src.utils.logging import setup_logging

logger = logging.getLogger(__name__)


class EmailTriageWorkflow:
    """Workflow for triaging emails with LLM classification."""

    def __init__(self):
        """Initialize workflow components."""
        logger.info("Initializing Email Triage Workflow")

        try:
            # Load label configuration
            self.label_config = Config.load_label_config()
            logger.debug(f"Loaded {len(self.label_config['labels'])} label definitions")

            # Initialize clients
            self.gmail_client = GmailClient()
            self.llm_client = LLMClient()

            logger.info("Email Triage Workflow initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize workflow: {e}")
            raise

    def run(self, max_emails: int = 10, dry_run: bool = False) -> dict[str, Any]:
        """Run the email triage workflow.

        Args:
            max_emails: Maximum number of emails to process
            dry_run: If True, classify but don't apply labels

        Returns:
            Dictionary with statistics:
                - processed: Number of emails processed
                - succeeded: Number successfully classified and labeled
                - failed: Number that failed
                - classifications: Dict mapping label names to counts

        Raises:
            Exception: If workflow encounters fatal error
        """
        logger.info(f"Starting email triage (max_emails={max_emails}, dry_run={dry_run})")

        stats = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "classifications": {label["name"]: 0 for label in self.label_config["labels"]}
        }

        try:
            # Fetch unread emails
            logger.info("Fetching unread emails from Gmail")
            emails = self.gmail_client.get_unread_emails(max_results=max_emails)

            if not emails:
                logger.info("No unread emails found")
                return stats

            logger.info(f"Processing {len(emails)} unread emails")

            # Process each email
            for email in emails:
                stats["processed"] += 1

                try:
                    success = self._process_email(email, dry_run=dry_run)

                    if success:
                        stats["succeeded"] += 1
                        # Track classification stats
                        classification = email.get("classification")
                        if classification:
                            stats["classifications"][classification] = \
                                stats["classifications"].get(classification, 0) + 1
                    else:
                        stats["failed"] += 1

                except Exception as e:
                    logger.error(f"Failed to process email {email['id']}: {e}")
                    stats["failed"] += 1
                    continue

            # Log summary
            logger.info(
                f"Email triage complete: "
                f"{stats['succeeded']}/{stats['processed']} succeeded, "
                f"{stats['failed']} failed"
            )

            for label, count in stats["classifications"].items():
                if count > 0:
                    logger.info(f"  {label}: {count} emails")

            return stats

        except Exception as e:
            logger.error(f"Email triage workflow failed: {e}")
            raise

    def _process_email(self, email: dict[str, Any], dry_run: bool = False) -> bool:
        """Process a single email: classify and apply label.

        Args:
            email: Email dictionary from GmailClient
            dry_run: If True, don't actually apply labels

        Returns:
            True if successful, False otherwise
        """
        email_id = email["id"]
        sender = email["sender"]
        subject = email["subject"]

        logger.debug(f"Processing email {email_id}: {subject[:50]}...")

        try:
            # Classify email
            classification = self.llm_client.classify_email(
                sender=sender,
                subject=subject,
                content=email["content"],
                label_config=self.label_config
            )

            email["classification"] = classification
            logger.info(f"Email {email_id} classified as: {classification}")

            # Apply label (unless dry run)
            if not dry_run:
                self.gmail_client.apply_label(email_id, classification)
                logger.debug(f"Applied label '{classification}' to email {email_id}")
            else:
                logger.debug(f"Dry run: would apply label '{classification}' to email {email_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to process email {email_id}: {e}")
            return False


def main() -> int:
    """Main entry point for email triage workflow.

    Returns:
        Exit code (0 for success, 1 for failure, 130 for interrupt)
    """
    # Setup logging
    setup_logging()

    logger.info("=" * 60)
    logger.info("Email Triage Workflow - Starting")
    logger.info("=" * 60)

    try:
        # Create and run workflow
        workflow = EmailTriageWorkflow()
        stats = workflow.run(max_emails=10, dry_run=False)

        # Success - exit quietly per Unix philosophy
        logger.info("Email triage completed successfully")
        return 0

    except KeyboardInterrupt:
        logger.warning("Workflow interrupted by user")
        return 130  # Standard Unix exit code for SIGINT

    except Exception as e:
        # Error - fail loudly to stderr
        logger.error(f"Email triage workflow failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

#### 2. Module Entry Point

**File**: `src/workflows/__main__.py`
**Changes**: Make workflows package executable

```python
"""Make workflows package executable."""
from src.workflows.email_triage import main

if __name__ == "__main__":
    exit(main())
```

#### 3. Workflow Tests

**File**: `tests/test_email_triage.py`
**Changes**: Create integration tests for workflow

```python
"""Tests for email triage workflow."""
from unittest.mock import MagicMock, patch

import pytest

from src.workflows.email_triage import EmailTriageWorkflow


@pytest.fixture
def mock_gmail_client():
    """Mock Gmail client."""
    client = MagicMock()
    client.get_unread_emails.return_value = [
        {
            "id": "msg_1",
            "sender": "boss@company.com",
            "subject": "Need your input ASAP",
            "content": "Can you review this proposal?",
            "snippet": "Can you review..."
        },
        {
            "id": "msg_2",
            "sender": "noreply@service.com",
            "subject": "Your order has shipped",
            "content": "Tracking number: 12345",
            "snippet": "Tracking number..."
        }
    ]
    return client


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = MagicMock()
    client.classify_email.side_effect = [
        "response-required",
        "transactional"
    ]
    return client


@pytest.fixture
def mock_label_config():
    """Mock label configuration."""
    return {
        "labels": [
            {"name": "response-required", "description": "Needs response"},
            {"name": "fyi", "description": "Info only"},
            {"name": "transactional", "description": "Automated"}
        ],
        "default_label": "fyi"
    }


@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_processes_emails_successfully(
    mock_llm_class,
    mock_gmail_class,
    mock_config,
    mock_gmail_client,
    mock_llm_client,
    mock_label_config
):
    """Test workflow successfully processes emails."""
    mock_config.return_value = mock_label_config
    mock_gmail_class.return_value = mock_gmail_client
    mock_llm_class.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    stats = workflow.run(max_emails=10, dry_run=False)

    assert stats["processed"] == 2
    assert stats["succeeded"] == 2
    assert stats["failed"] == 0
    assert stats["classifications"]["response-required"] == 1
    assert stats["classifications"]["transactional"] == 1

    # Verify labels were applied
    assert mock_gmail_client.apply_label.call_count == 2


@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_dry_run_doesnt_apply_labels(
    mock_llm_class,
    mock_gmail_class,
    mock_config,
    mock_gmail_client,
    mock_llm_client,
    mock_label_config
):
    """Test dry run mode doesn't apply labels."""
    mock_config.return_value = mock_label_config
    mock_gmail_class.return_value = mock_gmail_client
    mock_llm_class.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    stats = workflow.run(max_emails=10, dry_run=True)

    assert stats["processed"] == 2
    assert stats["succeeded"] == 2

    # Verify no labels were applied
    mock_gmail_client.apply_label.assert_not_called()


@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_handles_no_unread_emails(
    mock_llm_class,
    mock_gmail_class,
    mock_config,
    mock_label_config
):
    """Test workflow handles case with no unread emails."""
    mock_config.return_value = mock_label_config
    mock_gmail_client = MagicMock()
    mock_gmail_client.get_unread_emails.return_value = []
    mock_gmail_class.return_value = mock_gmail_client
    mock_llm_class.return_value = MagicMock()

    workflow = EmailTriageWorkflow()
    stats = workflow.run()

    assert stats["processed"] == 0
    assert stats["succeeded"] == 0
    assert stats["failed"] == 0


@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_continues_on_single_email_failure(
    mock_llm_class,
    mock_gmail_class,
    mock_config,
    mock_gmail_client,
    mock_label_config
):
    """Test workflow continues processing if one email fails."""
    mock_config.return_value = mock_label_config
    mock_gmail_class.return_value = mock_gmail_client

    # First email fails, second succeeds
    mock_llm_client = MagicMock()
    mock_llm_client.classify_email.side_effect = [
        Exception("Classification failed"),
        "fyi"
    ]
    mock_llm_class.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    stats = workflow.run(max_emails=10)

    assert stats["processed"] == 2
    assert stats["succeeded"] == 1
    assert stats["failed"] == 1
```

#### 4. Environment Configuration Setup

**File**: `.env`
**Changes**: Create actual environment file with MLX configuration

```bash
# Copy from .env.example and configure with your MLX server details
cp .env.example .env

# Then edit .env and set:
LLM_BASE_URL=http://<tailscale-host>:8080/v1
LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
LLM_API_KEY=not-needed

# Gmail configuration (will be created during Phase 3)
GMAIL_CREDENTIALS_FILE=config/gmail_credentials.json
GMAIL_TOKEN_FILE=config/gmail_token.json

# Label configuration
LABEL_CONFIG_FILE=config/labels.json

# Logging
LOG_LEVEL=INFO
LOG_FILE=data/logs/email_triage.log
```

### Success Criteria:

#### Automated Verification:
- [x] Workflow module imports: `python -c "from src.workflows.email_triage import EmailTriageWorkflow"`
- [x] All tests pass: `pytest tests/ -v`
- [x] Type checking passes: `mypy src/`
- [x] Linting passes: `ruff check src/`
- [x] Test coverage acceptable: `pytest --cov=src --cov-report=term-missing`

#### Manual Verification:

**Environment Setup:**
- [ ] `.env` file created with MLX server connection details
- [ ] `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` configured
- [ ] Gmail credentials from Phase 3 still valid

**Dry Run Testing:**
- [ ] Can run workflow in dry-run mode: `python -c "from src.workflows.email_triage import EmailTriageWorkflow; w = EmailTriageWorkflow(); stats = w.run(max_emails=5, dry_run=True); print(stats)"`
- [ ] Workflow initializes without errors
- [ ] Fetches unread emails from Gmail
- [ ] LLM classifies emails (check logs for classifications)
- [ ] No labels applied in dry-run mode
- [ ] Statistics returned correctly

**Production Testing:**
- [ ] Can run full workflow: `python -m src.workflows.email_triage`
- [ ] Workflow processes emails end-to-end
- [ ] Labels are created in Gmail if they don't exist
- [ ] Labels are applied to emails correctly
- [ ] Can verify labels in Gmail web interface
- [ ] Logs contain appropriate info/debug messages
- [ ] Errors appear on stderr with clear messages
- [ ] Successful runs are quiet (no stdout output)
- [ ] Subsequent runs use saved Gmail token (no browser popup)

**Error Handling Testing:**
- [ ] Individual email failures don't stop workflow (test by temporarily breaking one classification)
- [ ] Workflow handles "no unread emails" gracefully
- [ ] KeyboardInterrupt (Ctrl+C) exits cleanly with code 130

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation that the complete end-to-end workflow works before proceeding to Phase 5.

---

## Phase 5: Testing & Documentation

### Overview

Comprehensive test coverage, documentation updates, and preparation for production use. This phase ensures the MVP is production-ready and maintainable.

### Changes Required:

#### 1. Configuration Tests

**File**: `tests/test_config.py`
**Changes**: Create tests for configuration module

```python
"""Tests for configuration management."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config import Config


def test_config_has_required_attributes():
    """Test Config has all required attributes."""
    assert hasattr(Config, "GMAIL_SCOPES")
    assert hasattr(Config, "LLM_MODEL")
    assert hasattr(Config, "LABEL_CONFIG_FILE")
    assert hasattr(Config, "LOG_LEVEL")


def test_gmail_scopes_are_restricted():
    """Test Gmail scopes are correctly restricted."""
    assert "gmail.readonly" in Config.GMAIL_SCOPES[0]
    assert "gmail.labels" in Config.GMAIL_SCOPES[1]
    # Ensure no send/compose permissions
    for scope in Config.GMAIL_SCOPES:
        assert "send" not in scope.lower()
        assert "compose" not in scope.lower()


def test_load_label_config_success():
    """Test loading valid label configuration."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config = {
            "labels": [
                {"name": "test-label", "description": "Test"}
            ],
            "default_label": "test-label"
        }
        json.dump(config, f)
        temp_path = Path(f.name)

    try:
        with patch.object(Config, "LABEL_CONFIG_FILE", temp_path):
            result = Config.load_label_config()
            assert len(result["labels"]) == 1
            assert result["labels"][0]["name"] == "test-label"
            assert result["default_label"] == "test-label"
    finally:
        temp_path.unlink()


def test_load_label_config_file_not_found():
    """Test loading label config raises error if file missing."""
    with patch.object(Config, "LABEL_CONFIG_FILE", Path("/nonexistent/file.json")):
        with pytest.raises(FileNotFoundError):
            Config.load_label_config()


def test_ensure_directories_creates_directories():
    """Test ensure_directories creates required directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.object(Config, "CONFIG_DIR", Path(tmpdir) / "config"):
            with patch.object(Config, "LOGS_DIR", Path(tmpdir) / "data" / "logs"):
                Config.ensure_directories()

                assert (Path(tmpdir) / "config").exists()
                assert (Path(tmpdir) / "data" / "logs").exists()
```

#### 2. Logging Tests

**File**: `tests/test_logging.py`
**Changes**: Create tests for logging setup

```python
"""Tests for logging configuration."""
import logging
import tempfile
from pathlib import Path

from src.utils.logging import setup_logging


def test_setup_logging_creates_log_file():
    """Test logging setup creates log file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"

        setup_logging(log_level="INFO", log_file=log_file, include_stderr=False)

        logger = logging.getLogger("test")
        logger.info("Test message")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content


def test_setup_logging_stderr_handler_only_errors():
    """Test stderr handler only logs ERROR and above."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"

        setup_logging(log_level="DEBUG", log_file=log_file, include_stderr=True)

        root_logger = logging.getLogger()

        # Check stderr handler exists and has ERROR level
        stderr_handlers = [
            h for h in root_logger.handlers
            if hasattr(h, "stream") and h.stream.name == "<stderr>"
        ]
        assert len(stderr_handlers) == 1
        assert stderr_handlers[0].level == logging.ERROR
```

#### 3. README Updates

**File**: `README.md`
**Changes**: Add comprehensive usage and troubleshooting sections

Add these sections to the existing README:

```markdown
## Quick Start

### 1. Point the app at your MLX server

```bash
# Create .env file
cp .env.example .env

# Edit .env and set the MLX host (for example, http://<tailscale-host>:8080/v1)
LLM_BASE_URL=http://localhost:8080/v1
LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
LLM_API_KEY=not-needed
```

### 2. Set up Gmail API

Follow the detailed guide in `docs/gmail_setup.md`:
1. Create Google Cloud project
2. Enable Gmail API
3. Configure OAuth consent screen
4. Download credentials to `config/gmail_credentials.json`

### 3. Run Email Triage

```bash
# Activate virtual environment
source venv/bin/activate

# Run email classification
python -m src.workflows.email_triage
```

First run will open a browser for Gmail OAuth authentication.

## Customizing Labels

Edit `config/labels.json` to define your own classification categories:

```json
{
  "labels": [
    {
      "name": "urgent",
      "description": "Time-sensitive emails requiring immediate attention or response within 24 hours"
    },
    {
      "name": "important",
      "description": "Significant emails that need attention but aren't time-critical"
    },
    {
      "name": "routine",
      "description": "Standard operational emails, updates, and regular communications"
    }
  ],
  "default_label": "routine"
}
```

**Tips for good label descriptions:**
- Be specific and detailed
- Include examples of what qualifies
- Distinguish clearly between similar categories
- The LLM uses these descriptions to classify emails

## Troubleshooting

### Gmail Authentication Issues

**Problem**: "Credentials file not found"
- **Solution**: Download OAuth credentials from Google Cloud Console and save as `config/gmail_credentials.json`
- See `docs/gmail_setup.md` for detailed instructions

**Problem**: "Access blocked: This app's request is invalid"
- **Solution**:
  1. Ensure OAuth consent screen is in "Testing" mode
  2. Add your email as a test user
  3. Verify both scopes are configured (gmail.readonly + gmail.labels)

**Problem**: Browser doesn't open for OAuth
- **Solution** (Codespaces): Copy the URL from terminal and open in your local browser

### LLM Classification Issues

**Problem**: "Cannot connect to LLM API"
- **Solution**: Ensure the MLX server is reachable and `.env` points at the correct host
- **Test**: `curl http://<tailscale-host>:8080/v1/models`

**Problem**: "Invalid label returned by LLM"
- **Solution**: LLM returned a label not in your config
  - Check `config/labels.json` has the expected labels
  - Make label descriptions more specific
  - Default label will be used as fallback

**Problem**: Classifications seem inaccurate
- **Solution**: Improve label descriptions in `config/labels.json`
  - Add more specific examples
  - Clarify distinctions between categories
  - Test with `dry_run=True` to iterate without applying labels

### General Issues

**Problem**: Import errors
- **Solution**: Ensure virtual environment is activated
  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```

**Problem**: No emails being processed
- **Solution**:
  - Verify you have unread emails in Gmail inbox
  - Workflow only processes `is:unread in:inbox` emails
  - Check logs: `tail -f data/logs/email_triage.log`

## Logging

Logs are written to `data/logs/email_triage.log` by default.

**Change log level:**
```bash
export LOG_LEVEL=DEBUG
python -m src.workflows.email_triage
```

**View logs in real-time:**
```bash
tail -f data/logs/email_triage.log
```

**Log levels:**
- `DEBUG`: Detailed information for diagnosing problems
- `INFO`: Confirmation that things are working (default)
- `WARNING`: Indication of potential issues
- `ERROR`: Serious problems (also output to stderr)

## Advanced Usage

### Dry Run Mode

Test classification without applying labels:

```python
from src.workflows.email_triage import EmailTriageWorkflow

workflow = EmailTriageWorkflow()
stats = workflow.run(max_emails=5, dry_run=True)
print(stats)
```

### Custom Email Limit

Process specific number of emails:

```python
workflow = EmailTriageWorkflow()
stats = workflow.run(max_emails=20)
```

### Programmatic Usage

```python
from src.integrations.gmail_client import GmailClient
from src.integrations.llm_client import LLMClient
from src.core.config import Config

# Initialize clients
gmail = GmailClient()
llm = LLMClient()
labels = Config.load_label_config()

# Fetch and classify
emails = gmail.get_unread_emails(max_results=10)
for email in emails:
    classification = llm.classify_email(
        sender=email['sender'],
        subject=email['subject'],
        content=email['content'],
        label_config=labels
    )
    gmail.apply_label(email['id'], classification)
```

## Next Steps (Post-MVP)

After the MVP is working, consider:

1. **Scheduling**: Set up macOS launchd for automatic email processing
2. **Production LLM**: Switch to local MLX server on macOS for free, private inference
3. **Multiple Labels**: Support applying multiple labels per email
4. **Email Actions**: Mark as read, archive, or star based on classification
5. **Web Interface**: Add FastAPI dashboard for configuration and monitoring
6. **Additional Workflows**: Expand beyond email classification

See `docs/spec.md` for the full roadmap.
```

#### 4. Pytest Configuration

**File**: `pytest.ini`
**Changes**: Create pytest configuration

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
    --disable-warnings
markers =
    integration: Integration tests requiring real services
    slow: Slow tests that take significant time
```

### Success Criteria:

#### Automated Verification:
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Test coverage >80%: `pytest --cov=src --cov-report=term-missing --cov-report=html`
- [ ] No typing errors: `mypy src/`
- [ ] No linting errors: `ruff check src/ tests/`
- [ ] All modules import cleanly: `python -c "import src.workflows.email_triage; import src.integrations.gmail_client; import src.integrations.llm_client"`

#### Manual Verification:

**Documentation Quality:**
- [ ] README instructions are complete and accurate
- [ ] Quick start guide works from scratch
- [ ] Troubleshooting section addresses common issues discovered during testing
- [ ] Gmail setup documentation (`docs/gmail_setup.md`) is clear
- [ ] Label customization guide is easy to follow

**End-to-End Validation:**
- [ ] Complete fresh setup following README from scratch:
  1. Clone repo
  2. Create venv
  3. Install dependencies
  4. Configure MLX connection
  5. Set up Gmail OAuth
  6. Customize labels
  7. Run workflow successfully
- [ ] Process at least 10 real emails successfully
- [ ] Verify classification accuracy (>80% correct labels)
- [ ] Test error scenarios (invalid credentials, network issues, etc.)
- [ ] Confirm all error messages are clear and actionable

**Production Readiness:**
- [ ] Logs provide adequate debugging information
- [ ] No secrets committed to git (verify `.gitignore`)
- [ ] Performance is acceptable (<30 seconds for 10 emails)
- [ ] Workflow can run multiple times without issues
- [ ] OAuth token refreshes automatically (test after several days)

**Implementation Note**: After all verification passes, the MVP is complete and production-ready. Document any improvements or enhancements discovered during testing for future iterations.

---

## Testing Strategy

### Unit Tests Coverage

Each module has comprehensive unit tests:

| Module | Test File | Coverage Areas |
|--------|-----------|----------------|
| Config | `test_config.py` | Environment loading, label config, directory creation |
| Logging | `test_logging.py` | Log file creation, stderr handling, log levels |
| LLM Client | `test_llm_client.py` | Classification, prompt building, error handling, validation |
| Gmail Client | `test_gmail_client.py` | OAuth flow, email fetching, label management |
| Workflow | `test_email_triage.py` | Orchestration, statistics, dry-run, error handling |

### Manual Testing Checklist

After completing all phases, perform these manual tests:

#### 1. Fresh Setup Test
```bash
# Clean environment
rm -rf venv config/gmail_token.json .env

# Follow README from scratch
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with MLX base URL (e.g. http://<tailscale-host>:8080/v1)

# Set up Gmail OAuth
# Follow docs/gmail_setup.md

# Run workflow
python -m src.workflows.email_triage
```

#### 2. Classification Accuracy Test
1. Send yourself test emails covering each label category
2. Run workflow: `python -m src.workflows.email_triage`
3. Verify classifications in Gmail web interface
4. Calculate accuracy: (correct classifications / total emails) * 100
5. Target: >80% accuracy
6. If <80%, refine label descriptions in `config/labels.json` and retest

#### 3. Error Handling Test
- **Invalid Credentials**: Delete `config/gmail_credentials.json` and verify error message
- **Network Failure**: Disconnect internet and verify error handling
- **MLX Unavailable**: Stop `mlx_lm.server` and verify error message
- **Empty Inbox**: Mark all emails as read and verify workflow handles gracefully

#### 4. Long-term Reliability Test
- Run workflow daily for one week
- Monitor for:
  - Token refresh issues
  - Memory leaks
  - Classification drift
  - API quota concerns

### Performance Targets

**MVP Performance Goals:**
- Process 10 emails in <30 seconds
- LLM classification per email <3 seconds
- Gmail API calls <5 seconds total
- Total workflow overhead <5 seconds

**Monitoring:**
```bash
# Time the workflow
time python -m src.workflows.email_triage

# Check logs for timing details
grep "seconds" data/logs/email_triage.log
```

## Migration Notes

No data migration required (greenfield project).

### First-Time Setup Checklist

Complete these steps in order:

- [ ] Clone repository
- [ ] Create Python 3.12+ virtual environment
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Create `.env` file from `.env.example`
- [ ] Provision access to MLX host (e.g. join Tailscale tailnet)
- [ ] Start `mlx_lm.server` on Apple Silicon laptop
- [ ] Point `.env` at the MLX server (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`)
- [ ] Create Google Cloud project
- [ ] Enable Gmail API
- [ ] Configure OAuth consent screen
- [ ] Download OAuth credentials to `config/gmail_credentials.json`
- [ ] (Optional) Customize labels in `config/labels.json`
- [ ] Run first authentication (OAuth flow)
- [ ] Test with dry run mode
- [ ] Run production workflow
- [ ] Verify labels in Gmail

## References

- **Original Spec**: `docs/spec.md`
- **Gmail Setup Guide**: `docs/gmail_setup.md`
- **MLX Server Setup**: `docs/mlx_server_setup.md` (for production)
- **Development Environment**: `docs/development_environment.md`
- **Phase 1-2 Plan**: `thoughts/shared/plans/2025-10-08-email-classification-mvp.md`
- **Phase 2 Handoff**: `thoughts/shared/handoffs/general/2025-10-09_02-04-50_phase2-llm-integration.md`
- **Consolidated Research**: `thoughts/shared/research/2025-10-28-project-plan-consolidation.md`

## External Resources

- **Tailscale**: https://tailscale.com/
- **Gmail API Docs**: https://developers.google.com/gmail/api/guides
- **Google Cloud Console**: https://console.cloud.google.com/
- **Python 3.12 Docs**: https://docs.python.org/3.12/

## Summary

This implementation plan provides a complete roadmap to finish the Email Classification MVP:

**Phase 3: Gmail Integration** (2-3 days)
- OAuth authentication with restricted scopes
- Email fetching and parsing
- Label management
- Comprehensive testing

**Phase 4: Email Triage Workflow** (1-2 days)
- Orchestrate Gmail + LLM clients
- Command-line interface
- Statistics and error handling
- Dry-run mode

**Phase 5: Testing & Documentation** (1-2 days)
- Complete test coverage (>80%)
- Production-ready documentation
- Performance validation
- Long-term reliability testing

**Total Estimated Effort**: 4-7 days

**Key Success Metric**: Can run `python -m src.workflows.email_triage` and successfully classify and label real Gmail emails using the MLX-hosted LLM.

**Next Step**: Begin Phase 3 by setting up Gmail API credentials in Google Cloud Console, then implement `GmailClient` class.
