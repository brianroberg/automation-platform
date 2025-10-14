# Email Classification MVP Implementation Plan

## Overview

Build a working email classification system that connects to Gmail, classifies unread emails using a local MLX-powered LLM, and applies appropriate labels. This is a greenfield Python 3.12+ project with no existing code, following an MVP-first approach that prioritizes a working end-to-end solution over infrastructure complexity.

## Current State Analysis

**Existing Code:** None - greenfield project
**Repository State:** Initialized git repo with only `docs/spec.md` and `LICENSE`
**Infrastructure:** None yet - will use Python venv initially, defer Docker to Phase 3

### Key Specifications:
- **Target Platform**: macOS (Apple Silicon optimized)
- **Python Version**: 3.12+
- **LLM Model**: `mlx-community/gpt-oss-20b-MXFP4-Q8` (subject to experimentation)
- **Gmail OAuth Scopes**: `gmail.readonly` + `gmail.labels` (most restrictive)
- **Label Categories**: `response-required`, `fyi`, `transactional` (externally configurable)
- **Classification Inputs**: Sender, subject, body content
- **Error Philosophy**: Unix-style (fail loudly on errors, quiet on success, info/debug logging available)

## Desired End State

A working command-line tool that:
1. Authenticates with Gmail API using OAuth (restricted scopes)
2. Fetches unread emails from the user's inbox
3. Sends email data (sender/subject/content) to local MLX LLM for classification
4. Applies appropriate Gmail labels based on classification results
5. Logs all activity at appropriate levels (error/info/debug)
6. Fails loudly on errors but runs quietly when successful
7. Uses external configuration for label definitions (not hardcoded in Python)

**Verification**: Running `python -m src.workflows.email_triage` successfully classifies and labels unread emails.

## What We're NOT Doing (Deferred to Later Phases)

- Docker containerization
- macOS launchd scheduling
- FastAPI web interface
- Multiple LLM providers (Ollama, OpenAI, Anthropic)
- Workflow plugin system
- YAML configuration files (using .env and simple config files for MVP)
- Advanced retry logic beyond basic error handling
- Monitoring/alerting systems
- macOS notifications or menu bar integration
- Additional workflows beyond email classification
- Keychain credential storage (using .env initially)

## Implementation Approach

Build in sequential phases where each phase is fully working before moving to the next:
1. **Foundation** - Project structure, dependencies, basic configuration
2. **LLM Integration** - Get MLX working with LLM library
3. **Gmail Integration** - OAuth and email fetching
4. **Classification Logic** - Connect LLM to email data with configurable labels
5. **End-to-End Integration** - Wire everything together with proper error handling

Each phase includes automated tests and manual verification before proceeding.

---

## Phase 1: Project Foundation

### Overview
Set up the Python project structure, install dependencies, configure the development environment, and establish logging/configuration patterns.

### Changes Required:

#### 1. Project Structure
**Create directories and initial files**:

```bash
mkdir -p src/{core,integrations,workflows,utils}
mkdir -p config
mkdir -p data/logs
mkdir -p tests
touch src/__init__.py
touch src/core/__init__.py
touch src/integrations/__init__.py
touch src/workflows/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py
```

#### 2. Python Dependencies
**File**: `requirements.txt`
**Changes**: Create with initial dependencies

```txt
# Core dependencies
python-dotenv==1.1.1

# Gmail API
google-auth==2.41.1
google-auth-oauthlib==1.2.2
google-auth-httplib2==0.2.0
google-api-python-client==2.184.0

# LLM integration
llm==0.27.1
llm-mlx>=0.1.0

# Testing
pytest==8.4.2
pytest-mock==3.15.1
pytest-cov==7.0.0
```

#### 3. Development Dependencies
**File**: `requirements-dev.txt`
**Changes**: Create with development tools

```txt
-r requirements.txt

# Development tools
black==25.9.0
ruff==0.7.4
mypy==1.18.2
ipython==9.6.0
```

#### 4. Environment Configuration
**File**: `.env.example`
**Changes**: Create template for environment variables

```bash
# Gmail API Credentials
GMAIL_CREDENTIALS_FILE=config/gmail_credentials.json
GMAIL_TOKEN_FILE=config/gmail_token.json

# LLM Configuration
LLM_MODEL=gpt-oss-20b-MXFP4-Q8
LLM_PROVIDER=mlx

# Label Configuration
LABEL_CONFIG_FILE=config/labels.json

# Logging
LOG_LEVEL=INFO
LOG_FILE=data/logs/email_triage.log
```

#### 5. Label Configuration
**File**: `config/labels.json`
**Changes**: Create externally configurable label definitions

```json
{
  "labels": [
    {
      "name": "response-required",
      "description": "Emails that require a direct response or action from the recipient. Includes questions, requests, invitations requiring RSVP, or time-sensitive matters."
    },
    {
      "name": "fyi",
      "description": "Informational emails that don't require a response. Includes updates, announcements, reports, newsletters, or general information sharing."
    },
    {
      "name": "transactional",
      "description": "Automated system-generated emails like receipts, confirmations, password resets, shipping notifications, or account alerts."
    }
  ],
  "default_label": "fyi"
}
```

#### 6. Basic Configuration Module
**File**: `src/core/config.py`
**Changes**: Create configuration loader

```python
"""Configuration management for the automation platform."""
import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

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
    GMAIL_CREDENTIALS_FILE = CONFIG_DIR / os.getenv("GMAIL_CREDENTIALS_FILE", "config/gmail_credentials.json")
    GMAIL_TOKEN_FILE = CONFIG_DIR / os.getenv("GMAIL_TOKEN_FILE", "config/gmail_token.json")
    GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.labels"
    ]

    # LLM Configuration
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-oss-20b-MXFP4-Q8")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mlx")

    # Label Configuration
    LABEL_CONFIG_FILE = CONFIG_DIR / os.getenv("LABEL_CONFIG_FILE", "config/labels.json")

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
            config = json.load(f)

        logger.info(f"Loaded {len(config.get('labels', []))} label definitions")
        return config

    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug("Ensured all required directories exist")


# Ensure directories exist on import
Config.ensure_directories()
```

#### 7. Logging Setup
**File**: `src/utils/logging.py`
**Changes**: Create logging configuration following Unix philosophy

```python
"""Logging configuration for the automation platform."""
import logging
import sys
from pathlib import Path

from src.core.config import Config


def setup_logging(
    log_level: str | None = None,
    log_file: Path | None = None,
    include_stderr: bool = True
) -> None:
    """Configure logging for the application.

    Follows Unix philosophy:
    - Errors go to stderr (always)
    - Info/debug go to file only (unless debugging)
    - Quiet on success, loud on failure

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Defaults to Config.LOG_LEVEL
        log_file: Path to log file. Defaults to Config.LOG_FILE
        include_stderr: Whether to include stderr handler for ERROR+ messages
    """
    log_level = log_level or Config.LOG_LEVEL
    log_file = log_file or Config.LOG_FILE

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # File handler - all levels based on LOG_LEVEL
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Stderr handler - ERROR and above only (Unix philosophy: fail loudly)
    if include_stderr:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.ERROR)
        stderr_formatter = logging.Formatter('ERROR: %(message)s')
        stderr_handler.setFormatter(stderr_formatter)
        root_logger.addHandler(stderr_handler)

    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")
```

#### 8. Basic README
**File**: `README.md`
**Changes**: Create with setup instructions

```markdown
# Automation Platform

A modular Python automation framework for macOS with local LLM integration.

## MVP: Email Classification

Automatically classifies Gmail emails using local MLX-powered LLM and applies appropriate labels.

## Requirements

- macOS (Apple Silicon recommended for MLX)
- Python 3.12+
- Gmail account with API access

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### 2. Install LLM MLX Plugin

```bash
llm install llm-mlx
```

### 3. Configure Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials JSON
6. Save as `config/gmail_credentials.json`

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env if you need to change defaults
```

### 5. Configure Labels

Edit `config/labels.json` to customize email classification categories and their definitions.

## Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run email classification
python -m src.workflows.email_triage
```

First run will open browser for Gmail OAuth authentication.

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src

# Format code
black src tests

# Lint code
ruff src tests

# Type check
mypy src
```

## Project Structure

```
automation-platform/
├── src/
│   ├── core/           # Core configuration and utilities
│   ├── integrations/   # External service clients (Gmail, LLM)
│   ├── workflows/      # Workflow implementations
│   └── utils/          # Helper utilities
├── config/             # Configuration files
├── data/logs/          # Application logs
└── tests/              # Test suite
```

## License

See LICENSE file.
```

#### 9. Python Package Configuration
**File**: `pyproject.toml`
**Changes**: Create for modern Python packaging

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "automation-platform"
version = "0.1.0"
description = "Modular Python automation framework for macOS"
requires-python = ">=3.12"
dependencies = [
    "python-dotenv>=1.1.1",
    "google-auth>=2.41.1",
    "google-auth-oauthlib>=1.2.2",
    "google-auth-httplib2>=0.2.0",
    "google-api-python-client>=2.184.0",
    "llm>=0.27.1",
    "llm-mlx>=0.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.4.2",
    "pytest-mock>=3.15.1",
    "pytest-cov>=7.0.0",
    "black>=25.9.0",
    "ruff>=0.7.4",
    "mypy>=1.18.2",
    "ipython>=9.6.0",
]

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

#### 10. Git Configuration
**File**: `.gitignore`
**Changes**: Create to exclude sensitive/generated files

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Environment
.env

# Configuration (contains secrets)
config/gmail_credentials.json
config/gmail_token.json

# Data
data/logs/*.log
data/cache/
data/state/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/

# macOS
.DS_Store

# Distribution
dist/
build/
*.egg-info/
```

### Success Criteria:

#### Automated Verification:
- [x] All directories created: `ls -R src/ config/ data/ tests/`
- [x] Dependencies installable: `python3.12 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- [x] Config module imports successfully: `python -c "from src.core.config import Config; print(Config.LLM_MODEL)"`
- [x] Logging setup works: `python -c "from src.utils.logging import setup_logging; setup_logging()"`
- [x] Label config loads: `python -c "from src.core.config import Config; print(Config.load_label_config())"`
- [x] No syntax errors: `python -m py_compile src/**/*.py`

#### Manual Verification:
- [x] Virtual environment activates without errors
- [x] All required directories exist with correct structure
- [x] `.env.example` contains all necessary variables
- [x] `config/labels.json` contains the three required labels
- [x] README.md instructions are clear and complete

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation that the project structure is satisfactory before proceeding to Phase 2.

---

## Phase 2: LLM Integration

### Overview
Create an LLM client abstraction for email classification that connects to an MLX server running on the user's macOS laptop. This enables development in Linux environments (Codespaces) while leveraging MLX's Apple Silicon optimization in production.

### Architecture Change (October 2025)

**Original Plan**: Use Simon Willison's `llm` CLI tool via subprocess calls for direct model access.

**Revised Plan**: Use OpenAI Python client library to connect to an MLX server (mlx-lm) running on macOS laptop, accessible via Tailscale.

**Rationale for Change**:
1. **Platform Constraints**: MLX only works on macOS with Apple Silicon - cannot run in Linux development environments (Codespaces, devcontainers)
2. **Development-Production Parity**: The application's ultimate deployment target is the user's macOS laptop, so depending on laptop availability is acceptable
3. **Network Architecture**: Using Tailscale for secure, encrypted access to laptop-hosted MLX server enables development anywhere while maintaining production deployment model
4. **Better API Design**: Direct HTTP/OpenAI client library is more reliable than subprocess calls, with proper error handling and type safety
5. **Future Flexibility**: OpenAI-compatible API makes it easy to swap providers (OpenAI, Anthropic, etc.) later without code changes

**Implementation Details**:
- **Server**: Run `mlx-lm.server` on macOS laptop (official MLX server from Apple's team)
- **Client**: Use `openai` Python library in Codespaces to connect to server via Tailscale
- **Configuration**: Store Tailscale IP and model name in environment variables
- **Security**: Leverage Tailscale's built-in encryption and device authentication

### Changes Required:

#### 1. LLM Client Abstraction
**File**: `src/integrations/llm_client.py`
**Changes**: Create LLM wrapper that connects to MLX server via OpenAI client

```python
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
        """
        self.model = model or Config.LLM_MODEL
        self.base_url = base_url or os.getenv("MLX_SERVER_URL")

        if not self.base_url:
            raise ValueError(
                "MLX_SERVER_URL environment variable must be set. "
                "Example: export MLX_SERVER_URL=http://100.x.x.x:8080"
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
            logger.debug(f"Verifying MLX server at {self.base_url}")
            # Try to list models as a connectivity check
            models = self.client.models.list()
            logger.debug(f"MLX server is reachable, models available: {len(models.data)}")
        except Exception as e:
            logger.error(f"Failed to connect to MLX server at {self.base_url}: {e}")
            raise RuntimeError(
                f"Cannot connect to MLX server at {self.base_url}. "
                f"Ensure the server is running and Tailscale is connected. "
                f"Original error: {e}"
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
            # Call MLX server via OpenAI client
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an email classification assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50,  # Classification should be very short
                timeout=30.0  # 30 second timeout
            )

            classification = response.choices[0].message.content.strip().lower()
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

        prompt = f"""Classify the following email into exactly one of these categories:

{label_descriptions}

Email Details:
From: {sender}
Subject: {subject}
Content: {content_preview}

Respond with ONLY the category name, nothing else. Choose the single most appropriate category."""

        return prompt
```

#### 2. LLM Client Tests
**File**: `tests/test_llm_client.py`
**Changes**: Create unit tests for LLM client (mocking OpenAI client)

```python
"""Tests for LLM client."""
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


@patch.dict("os.environ", {"MLX_SERVER_URL": "http://100.64.0.1:8080"})
@patch("src.integrations.llm_client.OpenAI")
def test_llm_client_initialization(mock_openai_class):
    """Test LLM client initializes and verifies server."""
    mock_client = MagicMock()
    mock_client.models.list.return_value = MagicMock(data=[{"id": "test-model"}])
    mock_openai_class.return_value = mock_client

    client = LLMClient(model="mlx-community/Llama-3.2-3B-Instruct-4bit")

    assert client.model == "mlx-community/Llama-3.2-3B-Instruct-4bit"
    assert client.base_url == "http://100.64.0.1:8080"
    mock_client.models.list.assert_called_once()


@patch.dict("os.environ", {}, clear=True)
def test_llm_client_requires_server_url():
    """Test LLM client raises error when MLX_SERVER_URL not set."""
    with pytest.raises(ValueError, match="MLX_SERVER_URL"):
        LLMClient(model="test-model")


@patch.dict("os.environ", {"MLX_SERVER_URL": "http://100.64.0.1:8080"})
@patch("src.integrations.llm_client.OpenAI")
def test_llm_client_server_unreachable(mock_openai_class):
    """Test LLM client raises error when server is unreachable."""
    mock_client = MagicMock()
    mock_client.models.list.side_effect = Exception("Connection refused")
    mock_openai_class.return_value = mock_client

    with pytest.raises(RuntimeError, match="Cannot connect to MLX server"):
        LLMClient(model="test-model")


@patch.dict("os.environ", {"MLX_SERVER_URL": "http://100.64.0.1:8080"})
@patch("src.integrations.llm_client.OpenAI")
def test_classify_email_success(mock_openai_class, mock_label_config):
    """Test successful email classification."""
    # Mock OpenAI client
    mock_client = MagicMock()
    mock_client.models.list.return_value = MagicMock(data=[])

    # Mock classification response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "response-required"
    mock_client.chat.completions.create.return_value = mock_response

    mock_openai_class.return_value = mock_client

    client = LLMClient(model="test-model")
    result = client.classify_email(
        sender="boss@company.com",
        subject="Urgent: Need your input",
        content="Can you review this by EOD?",
        label_config=mock_label_config
    )

    assert result == "response-required"
    mock_client.chat.completions.create.assert_called_once()


@patch.dict("os.environ", {"MLX_SERVER_URL": "http://100.64.0.1:8080"})
@patch("src.integrations.llm_client.OpenAI")
def test_classify_email_invalid_label_uses_default(mock_openai_class, mock_label_config):
    """Test classification falls back to default when LLM returns invalid label."""
    mock_client = MagicMock()
    mock_client.models.list.return_value = MagicMock(data=[])

    # Mock invalid response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "invalid-label"
    mock_client.chat.completions.create.return_value = mock_response

    mock_openai_class.return_value = mock_client

    client = LLMClient(model="test-model")
    result = client.classify_email(
        sender="test@example.com",
        subject="Test",
        content="Test content",
        label_config=mock_label_config
    )

    assert result == "fyi"  # default_label


@patch.dict("os.environ", {"MLX_SERVER_URL": "http://100.64.0.1:8080"})
@patch("src.integrations.llm_client.OpenAI")
def test_classify_email_server_error(mock_openai_class, mock_label_config):
    """Test classification handles server errors gracefully."""
    mock_client = MagicMock()
    mock_client.models.list.return_value = MagicMock(data=[])
    mock_client.chat.completions.create.side_effect = Exception("Server error")

    mock_openai_class.return_value = mock_client

    client = LLMClient(model="test-model")

    with pytest.raises(RuntimeError, match="LLM classification failed"):
        client.classify_email(
            sender="test@example.com",
            subject="Test",
            content="Test content",
            label_config=mock_label_config
        )
```

#### 3. MLX Server Setup Documentation
**File**: `docs/mlx_server_setup.md`
**Changes**: Create comprehensive guide for setting up MLX server on macOS

```markdown
# MLX Server Setup Guide

## Overview

The application uses an MLX server running on your macOS laptop to perform email classification. This guide covers setting up the server and connecting to it from development environments via Tailscale.

## Prerequisites

- **macOS with Apple Silicon** (M1, M2, M3, or M4)
- **Python 3.12+**
- **Tailscale** installed on both laptop and development machine

## Part 1: Install MLX Server (On macOS Laptop)

### 1. Install mlx-lm

```bash
# Create/activate virtual environment (optional but recommended)
python3.12 -m venv ~/mlx-env
source ~/mlx-env/bin/activate

# Install mlx-lm
pip install mlx-lm
```

### 2. Download Model

```bash
# Start with a small model for testing
mlx_lm.server --model mlx-community/Llama-3.2-3B-Instruct-4bit

# The model will download automatically on first run
# This may take several minutes depending on your internet speed
```

**Note**: The server will download and cache the model in `~/.cache/huggingface/`. Subsequent starts will be much faster.

### 3. Configure Tailscale

If you haven't already:

```bash
# Install Tailscale
# Download from: https://tailscale.com/download/mac

# Or via Homebrew
brew install tailscale

# Start and authenticate
tailscale up
```

Get your Tailscale IP:

```bash
tailscale ip -4
# Example output: 100.64.0.123
```

### 4. Start MLX Server

```bash
# Start server accessible over Tailscale
mlx_lm.server \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --host 0.0.0.0 \
  --port 8080

# You should see:
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8080
```

**Keep this terminal window open** - the server must run continuously.

### 5. Test Server Locally

In a new terminal:

```bash
curl http://localhost:8080/v1/models
# Should return list of available models
```

## Part 2: Connect from Development Environment

### 1. Install Tailscale (Codespaces/Remote Machine)

```bash
# In GitHub Codespaces or remote Linux machine
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate
sudo tailscale up

# Verify connection
tailscale status
```

### 2. Test Connection to MLX Server

```bash
# Replace with your laptop's Tailscale IP
export MLX_IP=100.64.0.123

# Test connectivity
curl http://$MLX_IP:8080/v1/models

# Should return the same model list
```

### 3. Configure Environment

```bash
# In your project's .env file
echo "MLX_SERVER_URL=http://100.64.0.123:8080" >> .env
echo "LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit" >> .env
```

### 4. Test with Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://100.64.0.123:8080/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="mlx-community/Llama-3.2-3B-Instruct-4bit",
    messages=[{"role": "user", "content": "Say hello!"}],
    max_tokens=50
)

print(response.choices[0].message.content)
```

## Part 3: Production Setup

### Running as Background Service (Optional)

For continuous operation, use macOS launchd:

**File**: `~/Library/LaunchAgents/com.user.mlx-server.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.mlx-server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/mlx-env/bin/mlx_lm.server</string>
        <string>--model</string>
        <string>mlx-community/Llama-3.2-3B-Instruct-4bit</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8080</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/mlx-server.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/mlx-server-error.log</string>
</dict>
</plist>
```

Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.user.mlx-server.plist
```

## Troubleshooting

### Server won't start

**Error**: `ImportError: libmlx.so: cannot open shared object`
**Solution**: MLX only works on macOS. Ensure you're on Apple Silicon Mac.

**Error**: `Address already in use`
**Solution**: Another process is using port 8080. Kill it or use a different port.

### Can't connect from remote machine

**Problem**: `Connection refused`
**Solution**:
1. Verify Tailscale is running on both machines: `tailscale status`
2. Verify server is listening: `lsof -i :8080` on macOS
3. Check firewall settings (macOS firewall shouldn't block Tailscale traffic)
4. Verify you're using the correct Tailscale IP

### Slow inference

**Problem**: Model takes too long to respond
**Solution**:
1. Use a smaller model (e.g., Llama-3.2-1B instead of 3B)
2. Close other applications to free up RAM
3. Ensure your Mac isn't in low-power mode

### Model download fails

**Problem**: Download interrupted or fails
**Solution**:
1. Check internet connection
2. Clear cache: `rm -rf ~/.cache/huggingface/`
3. Try downloading manually: `huggingface-cli download mlx-community/Llama-3.2-3B-Instruct-4bit`

## Security Notes

- **Tailscale Security**: Tailscale provides WireGuard-encrypted connections between your devices
- **No Public Exposure**: The server is only accessible via your Tailscale network, not the public internet
- **No Authentication**: The MLX server doesn't require API keys (relies on Tailscale for access control)
- **Device Trust**: Only devices authenticated to your Tailscale network can access the server

## Model Recommendations

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| Llama-3.2-1B-Instruct-4bit | ~0.5GB | Very Fast | Good | Development/Testing |
| Llama-3.2-3B-Instruct-4bit | ~1.5GB | Fast | Better | Production |
| Mistral-7B-Instruct-v0.3-4bit | ~4GB | Medium | Best | High Accuracy |

All models are available from `mlx-community` on Hugging Face.

## Monitoring

### Check Server Status

```bash
# On macOS laptop
curl http://localhost:8080/health

# From remote machine
curl http://100.64.0.123:8080/health
```

### View Logs

```bash
# If running in terminal (Ctrl+C to stop)
# Logs appear in stdout

# If running as launchd service
tail -f ~/mlx-server.log
tail -f ~/mlx-server-error.log
```

## Alternative: Multiple Models

To run multiple models simultaneously, start multiple servers on different ports:

```bash
# Terminal 1
mlx_lm.server --model mlx-community/Llama-3.2-1B-Instruct-4bit --port 8080

# Terminal 2
mlx_lm.server --model mlx-community/Llama-3.2-3B-Instruct-4bit --port 8081
```

Then configure different `MLX_SERVER_URL` values for different use cases.
```

### Success Criteria:

#### Automated Verification:
- [ ] LLM client imports successfully: `python -c "from src.integrations.llm_client import LLMClient"`
- [ ] Tests pass: `pytest tests/test_llm_client.py -v`
- [ ] Type checking passes: `mypy src/integrations/llm_client.py`
- [ ] No linting errors: `ruff check src/integrations/llm_client.py`
- [ ] OpenAI dependency added: `pip install openai` (add to requirements.txt)

#### Manual Verification - Server Setup:
**On macOS Laptop (Server Host)**:
- [ ] Tailscale installed and authenticated
- [ ] MLX server (mlx-lm) installed: `pip install mlx-lm`
- [ ] Server starts successfully: `mlx_lm.server --model mlx-community/Llama-3.2-3B-Instruct-4bit --host 0.0.0.0 --port 8080`
- [ ] Server is reachable locally: `curl http://localhost:8080/v1/models`
- [ ] Get Tailscale IP: `tailscale ip -4`

**In Development Environment (Codespaces)**:
- [ ] Tailscale installed and authenticated: `sudo tailscale up`
- [ ] Can reach laptop via Tailscale: `curl http://TAILSCALE_IP:8080/v1/models`
- [ ] Environment configured: `MLX_SERVER_URL=http://TAILSCALE_IP:8080` in `.env`
- [ ] Test classification works:
  ```python
  from src.integrations.llm_client import LLMClient
  from src.core.config import Config

  client = LLMClient()
  result = client.classify_email(
      sender="test@example.com",
      subject="Meeting tomorrow",
      content="Can you make it?",
      label_config=Config.load_label_config()
  )
  print(f"Classification: {result}")
  ```

#### Documentation:
- [ ] `docs/mlx_server_setup.md` created with complete setup instructions
- [ ] `docs/development_environment.md` updated to reflect new architecture
- [ ] `.env.example` updated with MLX_SERVER_URL configuration
- [ ] README.md updated if necessary

**Implementation Note**: Phase 2 is considered complete when:
1. All automated tests pass (with mocked OpenAI client) ✅
2. Code is properly structured and typed ✅
3. MLX server can be accessed from development environment via Tailscale ⏳ (IN PROGRESS)
4. End-to-end email classification works over the network ⏳ (BLOCKED - depends on step 3)

This architecture enables development in Codespaces while using production-grade MLX on the macOS laptop.

---

## Phase 3: Gmail Integration

### Overview
Implement Gmail API client with OAuth authentication (restricted scopes), email fetching, and label management.

### Changes Required:

#### 1. Gmail Client
**File**: `src/integrations/gmail_client.py`
**Changes**: Create Gmail API wrapper with restricted scopes

```python
"""Gmail API client with OAuth authentication."""
import base64
import logging
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.core.config import Config

logger = logging.getLogger(__name__)


class GmailClient:
    """Client for interacting with Gmail API."""

    # Restricted scopes - read-only + labels only
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
                self.creds.refresh(Request())
            else:
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
            Exception: If API call fails
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
                logger.debug(f"Fetched email {msg['id']}: {email['subject'][:50]}")

            return emails

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
            Exception: If API call fails
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
    mock_exists.side_effect = lambda: mock_exists.call_count > 1

    mock_flow_instance = MagicMock()
    mock_flow.from_client_secrets_file.return_value = mock_flow_instance
    mock_flow_instance.run_local_server.return_value = MagicMock()

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
```

#### 3. Gmail Setup Documentation
**File**: `docs/gmail_setup.md`
**Changes**: Create detailed Gmail API setup guide

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

### 2. Enable Gmail API

1. In the Cloud Console, navigate to "APIs & Services" → "Library"
2. Search for "Gmail API"
3. Click on "Gmail API"
4. Click "Enable"

### 3. Configure OAuth Consent Screen

1. Navigate to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type (unless you have Google Workspace)
3. Click "Create"
4. Fill in required fields:
   - App name: "Automation Platform"
   - User support email: (your email)
   - Developer contact: (your email)
5. Click "Save and Continue"
6. Click "Add or Remove Scopes"
7. Add these scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.labels`
8. Click "Update" → "Save and Continue"
9. Add your email as a test user
10. Click "Save and Continue"

### 4. Create OAuth Credentials

1. Navigate to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: "Desktop app"
4. Name: "Automation Platform Desktop Client"
5. Click "Create"
6. Click "Download JSON" on the popup
7. Save the file as `config/gmail_credentials.json` in your project

### 5. First-Time Authentication

When you run the email triage workflow for the first time:

1. A browser window will open automatically
2. Sign in with your Google account
3. Review the permissions (readonly + labels only)
4. Click "Allow"
5. You should see "The authentication flow has completed"
6. The token is saved to `config/gmail_token.json` for future use

## Security Notes

- **Restricted Scopes**: The application only has permission to:
  - Read your emails (cannot modify or delete)
  - Manage labels (create and apply labels)
- **No Send Permission**: The application CANNOT send emails on your behalf
- **Local Storage**: Credentials are stored locally in `config/` directory
- **Token Expiry**: Tokens automatically refresh when expired

## Troubleshooting

### "Access blocked: This app's request is invalid"

Your OAuth consent screen might not be configured correctly. Verify:
- App is in "Testing" mode (allows test users)
- Your email is added as a test user
- Correct scopes are configured

### "Credentials file not found"

Make sure you:
1. Downloaded the OAuth credentials JSON
2. Renamed it to `gmail_credentials.json`
3. Placed it in the `config/` directory

### "Redirect URI mismatch"

This shouldn't happen with desktop apps, but if it does:
- Make sure you selected "Desktop app" not "Web application"
- Delete and recreate the OAuth credentials

## Revoking Access

To revoke the application's access to your Gmail:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Scroll to "Third-party apps with account access"
3. Find "Automation Platform"
4. Click "Remove Access"
5. Delete `config/gmail_token.json` from your project
```

### Success Criteria:

#### Automated Verification:
- [ ] Gmail client imports successfully: `python -c "from src.integrations.gmail_client import GmailClient"`
- [ ] Tests pass: `pytest tests/test_gmail_client.py -v`
- [ ] Type checking passes: `mypy src/integrations/gmail_client.py`
- [ ] No linting errors: `ruff src/integrations/gmail_client.py`

#### Manual Verification:
- [ ] OAuth credentials downloaded and saved to `config/gmail_credentials.json`
- [ ] Can instantiate client and complete OAuth flow (browser opens)
- [ ] Successfully authenticate with restricted scopes (readonly + labels)
- [ ] Token saved to `config/gmail_token.json` after authentication
- [ ] Can fetch unread emails: Test in Python REPL or with simple script
- [ ] Can create and apply labels to test email
- [ ] Subsequent runs use saved token without re-authenticating

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation that Gmail integration works correctly with your account before proceeding to Phase 4.

---

## Phase 4: Classification Workflow

### Overview
Connect all components into a working end-to-end email classification workflow with proper error handling and logging.

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
        Exit code (0 for success, 1 for failure)
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

#### 2. Command-line Interface
**File**: `src/workflows/__main__.py`
**Changes**: Make workflow executable as module

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

#### 4. Quick Start Script
**File**: `scripts/run_triage.sh`
**Changes**: Create convenience script for running workflow

```bash
#!/bin/bash
# Convenience script to run email triage workflow

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Run setup first."
    exit 1
fi

# Activate venv
source venv/bin/activate

# Run workflow
echo "Running email triage workflow..."
python -m src.workflows.email_triage

# Show recent log entries
echo ""
echo "Recent log entries:"
tail -n 20 data/logs/email_triage.log
```

### Success Criteria:

#### Automated Verification:
- [ ] Workflow module imports: `python -c "from src.workflows.email_triage import EmailTriageWorkflow"`
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Type checking passes: `mypy src/`
- [ ] Linting passes: `ruff src/`
- [ ] Test coverage acceptable: `pytest --cov=src --cov-report=term-missing`

#### Manual Verification:
- [ ] Can run workflow: `python -m src.workflows.email_triage`
- [ ] OAuth flow completes successfully on first run
- [ ] Workflow fetches unread emails from Gmail
- [ ] LLM classifies emails (check logs for classifications)
- [ ] Labels are created in Gmail if they don't exist
- [ ] Labels are applied to emails correctly
- [ ] Can verify labels in Gmail web interface
- [ ] Subsequent runs use saved token (no browser popup)
- [ ] Logs contain appropriate info/debug messages at configured level
- [ ] Errors appear on stderr with clear messages
- [ ] Successful runs are quiet (no stdout output)

**Implementation Note**: This is the final MVP phase. After all verification passes and manual testing confirms end-to-end functionality, the MVP is complete. Document any issues or improvements needed before proceeding to Phase 5.

---

## Phase 5: Testing & Documentation

### Overview
Comprehensive test coverage, documentation updates, and preparation for refinement phase.

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

#### 3. Integration Test
**File**: `tests/test_integration.py`
**Changes**: Create end-to-end integration test

```python
"""Integration tests for email triage workflow.

These tests require actual Gmail and LLM setup.
Mark as slow/integration for CI purposes.
"""
import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="Requires actual Gmail credentials and LLM setup")
def test_end_to_end_workflow():
    """End-to-end test with real Gmail and LLM.

    This test is skipped by default as it requires:
    - Valid Gmail OAuth credentials
    - LLM model downloaded and available
    - Actual unread emails in the test account

    To run manually:
        pytest tests/test_integration.py::test_end_to_end_workflow -v -s
    """
    from src.workflows.email_triage import EmailTriageWorkflow

    workflow = EmailTriageWorkflow()
    stats = workflow.run(max_emails=1, dry_run=True)

    # Basic smoke test - just verify it runs without crashing
    assert "processed" in stats
    assert "succeeded" in stats
    assert "failed" in stats
```

#### 4. Updated README
**File**: `README.md` (additions)
**Changes**: Add troubleshooting and next steps sections

```markdown
<!-- Add these sections to the existing README -->

## Troubleshooting

### Gmail Authentication Issues

**Problem**: "Credentials file not found"
- **Solution**: Download OAuth credentials from Google Cloud Console and save as `config/gmail_credentials.json`
- See `docs/gmail_setup.md` for detailed instructions

**Problem**: "Access blocked: This app's request is invalid"
- **Solution**: Ensure your OAuth consent screen is in "Testing" mode and your email is added as a test user

### LLM Issues

**Problem**: "Model not available"
- **Solution**: Install MLX plugin and download model:
  ```bash
  llm install llm-mlx
  llm mlx download gpt-oss-20b-MXFP4-Q8
  ```

**Problem**: "Classification timed out"
- **Solution**: Model may be too large for your hardware. Try a smaller model:
  ```bash
  llm mlx download mlx-community/Llama-3.2-1B-Instruct-4bit
  export LLM_MODEL=Llama-3.2-1B-Instruct-4bit
  ```

### General Issues

**Problem**: Import errors
- **Solution**: Ensure virtual environment is activated:
  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```

**Problem**: No emails being processed
- **Solution**: Check that you have unread emails in your inbox. Workflow only processes `is:unread in:inbox` emails.

## Label Configuration

Edit `config/labels.json` to customize classification categories:

```json
{
  "labels": [
    {
      "name": "your-label-name",
      "description": "Detailed description of when to use this label"
    }
  ],
  "default_label": "fallback-label-name"
}
```

The LLM will use these descriptions to determine the appropriate label for each email.

## Logging

Logs are written to `data/logs/email_triage.log` by default.

To change log level:
```bash
export LOG_LEVEL=DEBUG
python -m src.workflows.email_triage
```

To view logs in real-time:
```bash
tail -f data/logs/email_triage.log
```

## Next Steps (Post-MVP)

After the MVP is working, consider these enhancements:

1. **Scheduling**: Set up macOS launchd for automatic email processing
2. **Docker**: Containerize for cleaner isolation
3. **Web UI**: Add FastAPI interface for configuration and monitoring
4. **Multiple Providers**: Support OpenAI, Anthropic, Ollama as LLM providers
5. **Additional Workflows**: Expand beyond email classification
6. **Advanced Features**: Retry logic, monitoring, notifications

See `docs/spec.md` for the full roadmap.

## Contributing

This is currently a personal automation platform. If you'd like to contribute:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

See LICENSE file.
```

#### 5. Pytest Configuration
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
- [ ] Test coverage >80%: `pytest --cov=src --cov-report=term-missing`
- [ ] No typing errors: `mypy src/`
- [ ] No linting errors: `ruff src/ tests/`
- [ ] Code formatted: `black --check src/ tests/`
- [ ] All modules import cleanly: `python -c "import src.workflows.email_triage; import src.integrations.gmail_client; import src.integrations.llm_client"`

#### Manual Verification:
- [ ] README instructions are complete and accurate
- [ ] Troubleshooting section addresses common issues
- [ ] Gmail setup documentation is clear
- [ ] Label configuration is well-documented
- [ ] Logging behavior matches documentation
- [ ] All configuration files have examples

**Implementation Note**: After all verification passes, the MVP is complete and documented. Ready for real-world usage and iteration based on actual results.

---

## Testing Strategy

### Unit Tests
Each module has corresponding tests:
- `test_config.py` - Configuration loading and validation
- `test_logging.py` - Logging setup and behavior
- `test_llm_client.py` - LLM classification logic
- `test_gmail_client.py` - Gmail API interactions
- `test_email_triage.py` - Workflow orchestration

### Integration Tests
- `test_integration.py` - End-to-end workflow (skipped by default, requires real setup)

### Manual Testing Steps
After completing all phases:

1. **Fresh Setup Test**:
   ```bash
   # Clean environment
   rm -rf venv config/gmail_token.json

   # Follow README from scratch
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   llm install llm-mlx
   # ... etc
   ```

2. **Classification Accuracy Test**:
   - Send test emails to yourself covering each label category
   - Run workflow
   - Verify classifications are correct
   - Adjust label descriptions in `config/labels.json` if needed
   - Re-run and verify improvements

3. **Error Handling Test**:
   - Test with invalid credentials
   - Test with missing model
   - Test with invalid label config
   - Verify errors are clear and actionable

4. **Long-term Test**:
   - Run workflow multiple times over several days
   - Monitor for token refresh issues
   - Track classification accuracy
   - Note any improvements needed

## Performance Considerations

### MVP Performance Targets
- Process 10 emails in < 2 minutes
- LLM classification per email < 10 seconds
- Gmail API calls < 5 seconds total

### Known Limitations (Acceptable for MVP)
- No batch processing
- Sequential email processing (not parallel)
- Simple error handling (no sophisticated retry logic)
- No rate limiting protection
- Model loaded fresh each time

### Post-MVP Optimizations (Deferred)
- Batch LLM inference
- Parallel email processing
- Persistent model loading
- Rate limit handling
- Caching mechanisms

## Migration Notes

This is a greenfield project with no existing data or migrations needed.

### First-Time Setup Checklist
1. ✓ Clone repository
2. ✓ Create Python 3.12+ virtual environment
3. ✓ Install dependencies
4. ✓ Install LLM MLX plugin
5. ✓ Download LLM model
6. ✓ Set up Gmail OAuth credentials
7. ✓ Copy and configure `.env` file
8. ✓ Customize `config/labels.json`
9. ✓ Run first authentication (OAuth flow)
10. ✓ Test with dry run
11. ✓ Run production workflow

## References

- **Original Spec**: `docs/spec.md`
- **Gmail Setup Guide**: `docs/gmail_setup.md`
- **LLM Library Docs**: https://llm.datasette.io/en/stable/
- **MLX Plugin**: https://github.com/simonw/llm-mlx
- **Gmail API Docs**: https://developers.google.com/gmail/api/guides
- **Python 3.12 Docs**: https://docs.python.org/3.12/

## Summary

This implementation plan provides a complete roadmap from empty repository to working MVP in 5 phases:

1. **Foundation** - Project structure and configuration (Day 1-2)
2. **LLM Integration** - Local AI classification (Day 3-4)
3. **Gmail Integration** - OAuth and email access (Day 5-6)
4. **Classification Workflow** - End-to-end orchestration (Day 7)
5. **Testing & Documentation** - Polish and prepare for use (Day 8+)

Each phase is independently verifiable with both automated and manual checks. The plan follows the spec's MVP-first philosophy: build the core functionality first, defer infrastructure complexity until proven valuable.

**Key Success Metric**: Can run `python -m src.workflows.email_triage` and successfully classify and label real Gmail emails using local MLX LLM.
