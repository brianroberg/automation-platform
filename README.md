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

### 3. Start MLX LLM Server

Run an MLX server on your macOS laptop (or another Apple Silicon host) and expose it to this environment (for example with [Tailscale](https://tailscale.com/)):

```bash
mlx_lm.server \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --host 0.0.0.0 \
  --port 8080
```

Ensure the development environment can reach the server via the chosen network tunnel.

### 4. Configure Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials JSON
6. Save as `config/gmail_credentials.json`

### 5. Configure Environment

```bash
cp .env.example .env
# Edit .env to point LLM_BASE_URL at your MLX server (e.g. http://<tailscale-host>:8080/v1)
```

### 6. Configure Labels

Edit `config/labels.json` to customize email classification categories and their definitions.

## Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run email classification
python -m src.workflows.email_triage

# Examples
# Preview classifications without applying labels
python -m src.workflows.email_triage --dry-run -n 5

# Verbose logging for each processed email
python -m src.workflows.email_triage -v -n 3
```

First run will open browser for Gmail OAuth authentication.

## Development

```bash
# Run tests
pytest

# Run integration tests (requires MLX server)
pytest --integration

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
