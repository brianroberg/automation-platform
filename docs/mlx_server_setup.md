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
