"""Tests for the email triage workflow."""
from unittest.mock import MagicMock, patch

import pytest

from src.workflows.email_triage import EmailTriageWorkflow


@pytest.fixture
def mock_emails():
    """Sample unread emails."""
    return [
        {
            "id": "msg_1",
            "sender": "boss@example.com",
            "subject": "Need your input",
            "content": "Can you review this proposal?",
            "snippet": "Can you review...",
        },
        {
            "id": "msg_2",
            "sender": "noreply@service.com",
            "subject": "Your order shipped",
            "content": "Tracking number: 12345",
            "snippet": "Tracking number...",
        },
    ]


@pytest.fixture
def mock_label_config():
    """Label configuration used by workflow."""
    return {
        "labels": [
            {"name": "response-required", "description": "Needs response"},
            {"name": "fyi", "description": "Informational"},
            {"name": "transactional", "description": "Automated"},
        ],
        "default_label": "fyi",
    }


@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_processes_emails(
    mock_llm_client_cls,
    mock_gmail_client_cls,
    mock_load_config,
    mock_emails,
    mock_label_config,
):
    """Workflow should classify emails and apply labels."""
    mock_load_config.return_value = mock_label_config

    mock_gmail_client = MagicMock()
    mock_gmail_client.get_unread_emails.return_value = mock_emails
    mock_gmail_client_cls.return_value = mock_gmail_client

    mock_llm_client = MagicMock()
    mock_llm_client.classify_email.side_effect = ["response-required", "transactional"]
    mock_llm_client_cls.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    stats = workflow.run(max_emails=5, dry_run=False)

    assert stats["processed"] == 2
    assert stats["succeeded"] == 2
    assert stats["failed"] == 0
    assert stats["classifications"]["response-required"] == 1
    assert stats["classifications"]["transactional"] == 1
    mock_gmail_client.apply_label.assert_any_call("msg_1", "response-required")
    mock_gmail_client.apply_label.assert_any_call("msg_2", "transactional")


@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_dry_run_skips_label_application(
    mock_llm_client_cls,
    mock_gmail_client_cls,
    mock_load_config,
    mock_emails,
    mock_label_config,
):
    """Dry run should classify without applying labels."""
    mock_load_config.return_value = mock_label_config

    mock_gmail_client = MagicMock()
    mock_gmail_client.get_unread_emails.return_value = [mock_emails[0]]
    mock_gmail_client_cls.return_value = mock_gmail_client

    mock_llm_client = MagicMock()
    mock_llm_client.classify_email.return_value = "response-required"
    mock_llm_client_cls.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    stats = workflow.run(max_emails=5, dry_run=True)

    assert stats["processed"] == 1
    assert stats["succeeded"] == 1
    mock_gmail_client.apply_label.assert_not_called()


@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_handles_email_failure(
    mock_llm_client_cls,
    mock_gmail_client_cls,
    mock_load_config,
    mock_emails,
    mock_label_config,
):
    """Failure processing one email should not stop the workflow."""
    mock_load_config.return_value = mock_label_config

    mock_gmail_client = MagicMock()
    mock_gmail_client.get_unread_emails.return_value = mock_emails
    mock_gmail_client_cls.return_value = mock_gmail_client

    mock_llm_client = MagicMock()
    mock_llm_client.classify_email.side_effect = ["response-required", RuntimeError("LLM error")]
    mock_llm_client_cls.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    stats = workflow.run(max_emails=5, dry_run=False)

    assert stats["processed"] == 2
    assert stats["succeeded"] == 1
    assert stats["failed"] == 1
