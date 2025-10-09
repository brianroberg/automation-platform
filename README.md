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
