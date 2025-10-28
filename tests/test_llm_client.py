"""Tests for LLM client."""
import os
from unittest.mock import MagicMock, patch

import pytest

from src.integrations.llm_client import LLMClient


@pytest.fixture
def mock_label_config():
    """Sample label configuration for testing."""
    return {
        "labels": [
            {
                "name": "response-required",
                "description": "Emails requiring a response"
            },
            {
                "name": "fyi",
                "description": "Informational emails"
            },
            {
                "name": "transactional",
                "description": "Automated system emails"
            }
        ],
        "default_label": "fyi"
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set required environment variables for testing."""
    monkeypatch.setenv("LLM_BASE_URL", "http://test-server:8080/v1")


@patch("src.integrations.llm_client.OpenAI")
def test_llm_client_initialization(mock_openai_class, mock_env_vars):
    """Test LLM client initializes and verifies server connection."""
    # Mock OpenAI client instance
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    # Mock models.list() response
    mock_model = MagicMock()
    mock_model.id = "test-model"
    mock_client.models.list.return_value = MagicMock(data=[mock_model])

    client = LLMClient(model="test-model")

    assert client.model == "test-model"
    assert client.base_url == "http://test-server:8080/v1"
    mock_openai_class.assert_called_once_with(
        base_url="http://test-server:8080/v1",
        api_key="not-needed"
    )
    mock_client.models.list.assert_called_once()


def test_llm_client_missing_server_url():
    """Test LLM client raises error when LLM_BASE_URL not set."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="LLM_BASE_URL environment variable must be set"):
            LLMClient(model="test-model")


@patch("src.integrations.llm_client.OpenAI")
def test_llm_client_server_not_reachable(mock_openai_class, mock_env_vars):
    """Test LLM client raises error when server is not reachable."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.models.list.side_effect = Exception("Connection refused")

    with pytest.raises(RuntimeError, match="Cannot connect to LLM API"):
        LLMClient(model="test-model")


@patch("src.integrations.llm_client.OpenAI")
def test_classify_email_success(mock_openai_class, mock_label_config, mock_env_vars):
    """Test successful email classification."""
    # Mock OpenAI client
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    # Mock server verification
    mock_model = MagicMock()
    mock_model.id = "test-model"
    mock_client.models.list.return_value = MagicMock(data=[mock_model])

    # Mock classification response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "response-required"
    mock_client.chat.completions.create.return_value = mock_response

    client = LLMClient(model="test-model")
    result = client.classify_email(
        sender="boss@company.com",
        subject="Urgent: Need your input",
        content="Can you review this by EOD?",
        label_config=mock_label_config
    )

    assert result == "response-required"
    mock_client.chat.completions.create.assert_called_once()


@patch("src.integrations.llm_client.OpenAI")
def test_classify_email_invalid_label_uses_default(mock_openai_class, mock_label_config, mock_env_vars):
    """Test classification falls back to default when LLM returns invalid label."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    # Mock server verification
    mock_model = MagicMock()
    mock_model.id = "test-model"
    mock_client.models.list.return_value = MagicMock(data=[mock_model])

    # Mock invalid classification response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "invalid-label"
    mock_client.chat.completions.create.return_value = mock_response

    client = LLMClient(model="test-model")
    result = client.classify_email(
        sender="test@example.com",
        subject="Test",
        content="Test content",
        label_config=mock_label_config
    )

    assert result == "fyi"  # default_label


@patch("src.integrations.llm_client.OpenAI")
def test_classify_email_api_error(mock_openai_class, mock_label_config, mock_env_vars):
    """Test classification handles API errors gracefully."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    # Mock server verification
    mock_model = MagicMock()
    mock_model.id = "test-model"
    mock_client.models.list.return_value = MagicMock(data=[mock_model])

    # Mock API error
    mock_client.chat.completions.create.side_effect = Exception("API Error")

    client = LLMClient(model="test-model")

    with pytest.raises(RuntimeError, match="LLM classification failed"):
        client.classify_email(
            sender="test@example.com",
            subject="Test",
            content="Test content",
            label_config=mock_label_config
        )


@patch("src.integrations.llm_client.OpenAI")
def test_classify_email_truncates_long_content(mock_openai_class, mock_label_config, mock_env_vars):
    """Test classification truncates long email content."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    # Mock server verification
    mock_model = MagicMock()
    mock_model.id = "test-model"
    mock_client.models.list.return_value = MagicMock(data=[mock_model])

    # Mock classification response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "fyi"
    mock_client.chat.completions.create.return_value = mock_response

    client = LLMClient(model="test-model")

    # Create long content (over 1000 chars)
    long_content = "x" * 1500

    result = client.classify_email(
        sender="test@example.com",
        subject="Test",
        content=long_content,
        label_config=mock_label_config
    )

    assert result == "fyi"

    # Verify the prompt was truncated
    call_args = mock_client.chat.completions.create.call_args
    prompt = call_args[1]["messages"][1]["content"]
    assert "..." in prompt  # Truncation marker
    assert len(prompt) < len(long_content) + 500  # Significantly shorter than full content
