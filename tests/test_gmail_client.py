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

    # Verify label was created with correct parameters
    mock_gmail_service.users().labels().create.assert_called_with(
        userId="me",
        body={
            "name": "test-label",
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show"
        }
    )

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
