"""Tests for the email triage workflow."""
from unittest.mock import MagicMock, patch, call

import pytest

from src.workflows.email_triage import EmailTriageWorkflow


@pytest.fixture
def mock_emails():
    """Sample unread emails."""
    return [
        {
            "id": "msg_1",
            "sender": "boss@example.com",
            "sender_display": "Boss <boss@example.com>",
            "subject": "Need your input",
            "content": "Can you review this proposal?",
            "snippet": "Can you review...",
            "to": ["triager@example.com"],
            "cc": [],
            "bcc": [],
            "existing_labels": [],
        },
        {
            "id": "msg_2",
            "sender": "noreply@service.com",
            "sender_display": "Service <noreply@service.com>",
            "subject": "Your order shipped",
            "content": "Tracking number: 12345",
            "snippet": "Tracking number...",
            "to": ["triager@example.com"],
            "cc": [],
            "bcc": [],
            "existing_labels": [],
        },
    ]


@pytest.fixture
def mock_label_config():
    """Label configuration used by workflow."""
    return {
        "labels": [
            {"name": "VIP", "description": "High-priority senders"},
            {"name": "response-required", "description": "Needs response"},
            {"name": "fyi", "description": "Informational"},
            {"name": "transactional", "description": "Automated"},
        ],
        "default_label": "fyi",
    }


@pytest.fixture
def deterministic_rules():
    """Base deterministic rules used by most tests."""
    return []


def _configure_gmail_mock(mock_gmail_client_cls, emails):
    mock_gmail_client = MagicMock()
    mock_gmail_client.get_inbox_candidates.return_value = emails
    mock_gmail_client.get_primary_address.return_value = "triager@example.com"
    mock_gmail_client.get_user_addresses.return_value = {"triager@example.com"}
    mock_gmail_client.label_exists.return_value = True
    mock_gmail_client_cls.return_value = mock_gmail_client
    return mock_gmail_client


@patch("src.workflows.email_triage.Config.load_deterministic_rules")
@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_processes_emails(
    mock_llm_client_cls,
    mock_gmail_client_cls,
    mock_load_config,
    mock_load_rules,
    mock_emails,
    mock_label_config,
    deterministic_rules,
):
    """Workflow should classify emails and apply labels."""
    mock_load_config.return_value = mock_label_config
    mock_load_rules.return_value = deterministic_rules

    mock_gmail_client = _configure_gmail_mock(mock_gmail_client_cls, mock_emails)

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


@patch("src.workflows.email_triage.Config.load_deterministic_rules")
@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_applies_vip_label_before_llm(
    mock_llm_client_cls,
    mock_gmail_client_cls,
    mock_load_config,
    mock_load_rules,
    mock_label_config,
):
    """VIP sender rule should label email without consulting the LLM."""
    mock_load_config.return_value = mock_label_config
    mock_load_rules.return_value = [
        {
            "name": "vip",
            "when": {"sender": {"in": ["vip1@example.com"]}},
            "actions": {"add": ["VIP"], "exclude": []},
        }
    ]

    mock_gmail_client = _configure_gmail_mock(
        mock_gmail_client_cls,
        [
            {
                "id": "vip_1",
                "sender": "vip1@example.com",
                "sender_display": "VIP <vip1@example.com>",
                "subject": "Quarterly check-in",
                "content": "Let's meet tomorrow.",
                "snippet": "Let's meet...",
                "to": ["triager@example.com"],
                "cc": [],
                "bcc": [],
                "existing_labels": [],
            }
        ],
    )

    mock_llm_client = MagicMock()
    mock_llm_client.classify_email.return_value = "response-required"
    mock_llm_client_cls.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    stats = workflow.run(max_emails=1, dry_run=False)

    assert stats["processed"] == 1
    assert stats["succeeded"] == 1
    assert stats["classifications"]["VIP"] == 1
    assert stats["classifications"]["response-required"] == 1
    assert mock_gmail_client.apply_label.call_args_list == [
        call("vip_1", "VIP"),
        call("vip_1", "response-required"),
    ]
    assert mock_llm_client.classify_email.called


@patch("src.workflows.email_triage.Config.load_deterministic_rules")
@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_rule_can_exclude_llm_label(
    mock_llm_client_cls,
    mock_gmail_client_cls,
    mock_load_config,
    mock_load_rules,
    mock_emails,
    mock_label_config,
):
    """If a rule excludes a label, the LLM result should be ignored."""
    mock_load_config.return_value = mock_label_config
    mock_load_rules.return_value = [
        {
            "name": "drop-fyi",
            "when": {"subject": {"contains_any": ["Need your input"]}},
            "actions": {"add": [], "exclude": ["fyi"]},
        }
    ]

    mock_gmail_client = _configure_gmail_mock(mock_gmail_client_cls, [mock_emails[0]])

    mock_llm_client = MagicMock()
    mock_llm_client.classify_email.return_value = "fyi"
    mock_llm_client_cls.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    stats = workflow.run(max_emails=1, dry_run=False)

    assert stats["classifications"]["fyi"] == 0
    mock_gmail_client.apply_label.assert_not_called()


@patch("src.workflows.email_triage.Config.load_deterministic_rules")
@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_rule_errors_when_label_missing_in_gmail(
    mock_llm_client_cls,
    mock_gmail_client_cls,
    mock_load_config,
    mock_load_rules,
    mock_emails,
    mock_label_config,
):
    """Rules referencing non-existent Gmail labels should fail."""
    mock_load_config.return_value = mock_label_config
    mock_load_rules.return_value = [
        {
            "name": "delete-rule",
            "when": {"subject": {"contains_any": ["Need your input"]}},
            "actions": {"add": ["to-delete"], "exclude": []},
        }
    ]

    mock_gmail_client = _configure_gmail_mock(mock_gmail_client_cls, [mock_emails[0]])
    mock_gmail_client.label_exists.side_effect = lambda name: name != "to-delete"

    mock_llm_client = MagicMock()
    mock_llm_client_cls.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    stats = workflow.run(max_emails=1, dry_run=False)

    assert stats["processed"] == 1
    assert stats["failed"] == 1
    mock_gmail_client.apply_label.assert_not_called()


@patch("src.workflows.email_triage.Config.load_deterministic_rules")
@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_rule_can_terminate_processing(
    mock_llm_client_cls,
    mock_gmail_client_cls,
    mock_load_config,
    mock_load_rules,
    mock_emails,
    mock_label_config,
):
    """Rules can terminate processing before the LLM is called."""
    mock_load_config.return_value = mock_label_config
    mock_load_rules.return_value = [
        {
            "name": "auto-stop",
            "when": {"subject": {"contains_any": ["Need your input"]}},
            "actions": {"add": ["fyi"], "exclude": []},
            "terminate": True,
        }
    ]

    mock_gmail_client = _configure_gmail_mock(mock_gmail_client_cls, [mock_emails[0]])

    mock_llm_client = MagicMock()
    mock_llm_client_cls.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    workflow.run(max_emails=1, dry_run=False)

    mock_llm_client.classify_email.assert_not_called()
    mock_gmail_client.apply_label.assert_called_once_with("msg_1", "fyi")


@patch("src.workflows.email_triage.Config.load_deterministic_rules")
@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_dry_run_skips_label_application(
    mock_llm_client_cls,
    mock_gmail_client_cls,
    mock_load_config,
    mock_load_rules,
    mock_emails,
    mock_label_config,
    capsys: pytest.CaptureFixture[str],
    deterministic_rules,
) -> None:
    """Dry run should classify without applying labels."""
    mock_load_config.return_value = mock_label_config
    mock_load_rules.return_value = deterministic_rules

    gmail_mock = _configure_gmail_mock(mock_gmail_client_cls, [mock_emails[0]])

    mock_llm_client = MagicMock()
    mock_llm_client.classify_email.return_value = "response-required"
    mock_llm_client_cls.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    stats = workflow.run(max_emails=5, dry_run=True)

    assert stats["processed"] == 1
    assert stats["succeeded"] == 1
    gmail_mock.apply_label.assert_not_called()
    captured = capsys.readouterr().out
    assert "would be labeled" in captured


@patch("src.workflows.email_triage.Config.load_deterministic_rules")
@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_handles_email_failure(
    mock_llm_client_cls,
    mock_gmail_client_cls,
    mock_load_config,
    mock_load_rules,
    mock_emails,
    mock_label_config,
    deterministic_rules,
):
    """Failure processing one email should not stop the workflow."""
    mock_load_config.return_value = mock_label_config
    mock_load_rules.return_value = deterministic_rules

    _configure_gmail_mock(mock_gmail_client_cls, mock_emails)

    mock_llm_client = MagicMock()
    mock_llm_client.classify_email.side_effect = ["response-required", RuntimeError("LLM error")]
    mock_llm_client_cls.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    stats = workflow.run(max_emails=5, dry_run=False)

    assert stats["processed"] == 2
    assert stats["succeeded"] == 1
    assert stats["failed"] == 1


@patch("src.workflows.email_triage.Config.load_deterministic_rules")
@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_verbose_outputs_status(
    mock_llm_client_cls,
    mock_gmail_client_cls,
    mock_load_config,
    mock_load_rules,
    mock_emails,
    mock_label_config,
    capsys: pytest.CaptureFixture[str],
    deterministic_rules,
) -> None:
    """Verbose mode should print applied labels."""
    mock_load_config.return_value = mock_label_config
    mock_load_rules.return_value = deterministic_rules

    gmail_mock = _configure_gmail_mock(mock_gmail_client_cls, [mock_emails[0]])

    mock_llm_client = MagicMock()
    mock_llm_client.classify_email.return_value = "response-required"
    mock_llm_client_cls.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    workflow.run(max_emails=1, dry_run=False, verbose=True)

    captured = capsys.readouterr().out
    assert "labeled 'response-required'" in captured
    gmail_mock.apply_label.assert_called_once_with("msg_1", "response-required")


@patch("src.workflows.email_triage.Config.load_deterministic_rules")
@patch("src.workflows.email_triage.Config.load_label_config")
@patch("src.workflows.email_triage.GmailClient")
@patch("src.workflows.email_triage.LLMClient")
def test_workflow_double_verbose_outputs_llm_response(
    mock_llm_client_cls,
    mock_gmail_client_cls,
    mock_load_config,
    mock_load_rules,
    mock_emails,
    mock_label_config,
    capsys: pytest.CaptureFixture[str],
    deterministic_rules,
) -> None:
    """Double verbose mode should include raw LLM responses."""
    mock_load_config.return_value = mock_label_config
    mock_load_rules.return_value = deterministic_rules

    _configure_gmail_mock(mock_gmail_client_cls, [mock_emails[0]])

    mock_llm_client = MagicMock()
    mock_llm_client.classify_email.return_value = "response-required"
    mock_llm_client.get_last_response.return_value = "Response-required"
    mock_llm_client_cls.return_value = mock_llm_client

    workflow = EmailTriageWorkflow()
    workflow.run(max_emails=1, dry_run=False, verbose=True, verbosity=2)

    captured = capsys.readouterr().out
    assert "[LLM RESPONSE]" in captured
    assert "Response-required" in captured
