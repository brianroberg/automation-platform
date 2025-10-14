# Development Environment Guide

## Architecture Overview

This project uses a **client-server architecture** for LLM inference:

- **Server**: MLX server (`mlx-lm.server`) runs on your macOS laptop with Apple Silicon
- **Client**: Python application (in Codespaces or local) connects to server via Tailscale
- **Communication**: OpenAI-compatible HTTP API over encrypted Tailscale network

This enables development in Linux environments (Codespaces, devcontainers) while leveraging MLX's Apple Silicon optimization.

## Why This Architecture?

### The MLX Constraint

**MLX only works on macOS with Apple Silicon.** It will **not run** in:
- GitHub Codespaces (Linux)
- VS Code devcontainers (Linux)
- Docker containers on Linux hosts
- CI/CD pipelines on Linux

If you try to run MLX on Linux, you'll see:
```
ImportError: libmlx.so: cannot open shared object file: No such file or directory
```

### The Solution

Instead of running MLX locally in development environments, we:

1. Run an MLX server on your macOS laptop (where MLX works)
2. Use Tailscale to create a secure network between your devices
3. Connect from Codespaces to the laptop-hosted MLX server via HTTP

This approach:
- ✅ Enables development in Codespaces while using production-grade MLX
- ✅ Maintains development-production parity (same deployment target)
- ✅ Leverages Tailscale's built-in encryption and authentication
- ✅ No code changes needed between development and production

## Quick Start

### 1. Set Up MLX Server (On macOS Laptop)

See the comprehensive guide: `docs/mlx_server_setup.md`

**TL;DR**:
```bash
# Install
pip install mlx-lm

# Install Tailscale
brew install tailscale
tailscale up

# Get your Tailscale IP
tailscale ip -4
# Example: 100.64.0.123

# Start server
mlx_lm.server \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --host 0.0.0.0 \
  --port 8080
```

Keep this terminal running.

### 2. Connect from Codespaces

```bash
# Install Tailscale in Codespaces
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Test connection (replace with your laptop's IP)
curl http://100.64.0.123:8080/v1/models

# Configure environment
echo "MLX_SERVER_URL=http://100.64.0.123:8080" >> .env
echo "LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit" >> .env
```

### 3. Test the Connection

```python
from src.integrations.llm_client import LLMClient
from src.core.config import Config

# This will connect to your laptop via Tailscale
client = LLMClient()

# Test classification
result = client.classify_email(
    sender="test@example.com",
    subject="Team meeting tomorrow at 3pm",
    content="Please confirm you can attend",
    label_config=Config.load_label_config()
)

print(f"Classified as: {result}")
```

## Environment Configuration

### Required Environment Variables

```bash
# .env file
MLX_SERVER_URL=http://100.64.0.123:8080  # Your laptop's Tailscale IP
LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
```

### Config.py Changes

No changes needed! The `LLMClient` reads `MLX_SERVER_URL` from environment:

```python
# In src/integrations/llm_client.py
base_url = os.getenv("MLX_SERVER_URL")
```

## Development Workflows

### Scenario 1: Developing in Codespaces

**Prerequisites**:
- MLX server running on macOS laptop
- Tailscale connected on both laptop and Codespaces

**Workflow**:
1. Start MLX server on laptop (can run in background)
2. Open project in Codespaces
3. Ensure Tailscale is running: `sudo tailscale status`
4. Configure `.env` with laptop's Tailscale IP
5. Develop and test normally - LLM calls go over Tailscale

**Network diagram**:
```
Codespaces (Linux)
    ↓ Tailscale (encrypted)
macOS Laptop
    ↓ localhost
MLX Server (port 8080)
    ↓
Local LLM Model
```

### Scenario 2: Developing Directly on macOS

If you're developing directly on the macOS laptop:

**Option A: Use localhost**
```bash
# .env
MLX_SERVER_URL=http://localhost:8080
```

**Option B: Use Tailscale IP (recommended)**
```bash
# .env
MLX_SERVER_URL=http://100.64.0.123:8080  # Your own Tailscale IP
```

This keeps configuration consistent across environments.

### Scenario 3: Production Deployment

Production runs on the same macOS laptop as development:

```bash
# In production .env
MLX_SERVER_URL=http://localhost:8080
```

Or keep using Tailscale IP - works the same!

## Troubleshooting

### Cannot connect to MLX server

**Error**: `Cannot connect to MLX server at http://100.64.0.123:8080`

**Solutions**:
1. Check MLX server is running on laptop
2. Verify Tailscale is connected on both devices: `tailscale status`
3. Test with curl: `curl http://100.64.0.123:8080/v1/models`
4. Check firewall isn't blocking (macOS firewall should allow Tailscale)

### Server returns errors

**Error**: Various HTTP errors from MLX server

**Solutions**:
1. Check server logs on macOS laptop (in terminal where server is running)
2. Verify model name matches what server has loaded
3. Try restarting MLX server
4. Check if model downloaded successfully: `ls ~/.cache/huggingface/`

### Tailscale authentication issues

**Error**: `sudo: tailscale: command not found` or connection fails

**Solutions**:
```bash
# Reinstall Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate (opens browser)
sudo tailscale up

# Verify
tailscale status
tailscale ip -4
```

### Slow responses

**Problem**: LLM takes too long to respond

**Solutions**:
1. Use smaller model (Llama-3.2-1B instead of 3B)
2. Check laptop isn't in low-power mode
3. Close other applications on laptop
4. Network latency (Tailscale should be <10ms on same network)

## Alternative Development Approaches

### Option 1: Use OpenAI During Development

If you have an OpenAI API key:

```python
# Temporary: just for testing without MLX server
from openai import OpenAI

client = OpenAI(api_key="your-key")
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "test"}]
)
```

**Pros**: Works anywhere, fast
**Cons**: Costs money, not production environment

### Option 2: Mock in Tests

For unit testing without network dependency:

```python
@patch("src.integrations.llm_client.OpenAI")
def test_classification(mock_openai):
    # Mock the OpenAI client
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    # Test without network
    # ... your test code
```

Our existing tests already do this!

## Security Considerations

### Tailscale Security

- **Encryption**: All traffic is encrypted via WireGuard
- **Authentication**: Only devices in your Tailscale network can connect
- **No Public Exposure**: Server is not accessible from internet
- **Zero Trust**: Each device authenticates independently

### MLX Server Security

- **No API Key**: Server doesn't require authentication (relies on Tailscale)
- **Read-Only**: Server only performs inference, doesn't modify data
- **Local Models**: All data stays within your Tailscale network
- **Not Production-Ready**: mlx-lm.server documentation warns it's not hardened for public exposure (but fine for Tailscale use)

### Best Practices

1. ✅ **Always use Tailscale**: Don't expose port 8080 to public internet
2. ✅ **Keep Tailscale updated**: `tailscale update`
3. ✅ **Monitor access**: Check who's connected: `tailscale status`
4. ✅ **Use ACLs**: Configure Tailscale ACLs for fine-grained access control
5. ❌ **Don't**: Bind to `0.0.0.0` without Tailscale (security risk)

## Performance Considerations

### Expected Latency

- **Localhost** (macOS dev): ~50-200ms per classification
- **Tailscale (same network)**: ~100-300ms per classification
- **Tailscale (remote)**: Varies by connection

### Throughput

MLX server handles requests sequentially:
- **Single request**: Fast (see latency above)
- **Multiple requests**: Queued (may be slow for batch operations)

For production at scale, consider:
- Running multiple MLX server instances on different ports
- Using a load balancer
- Implementing request queuing in your application

### Model Performance

| Model | Load Time | Speed | Memory |
|-------|-----------|-------|--------|
| Llama-3.2-1B-4bit | ~2s | Very Fast | ~1GB |
| Llama-3.2-3B-4bit | ~5s | Fast | ~2GB |
| Mistral-7B-4bit | ~10s | Medium | ~4GB |

## FAQ

**Q: Do I need to keep the MLX server running all the time?**
A: Only when developing. You can stop it when not working on the project. For production, set up as a launchd service (see `docs/mlx_server_setup.md`).

**Q: Can multiple people share one MLX server?**
A: Yes, if they're all on your Tailscale network. The server handles one request at a time, so it may be slower with multiple users.

**Q: What if my laptop goes to sleep?**
A: The server will stop responding. Wake your laptop or configure it to not sleep while plugged in.

**Q: Can I use this architecture in production?**
A: Yes! The production deployment is the same macOS laptop. Just use `localhost` instead of Tailscale IP in production config.

**Q: What about CI/CD?**
A: Mock the LLM client in tests (we already do this). CI doesn't need the actual MLX server.

**Q: Can I use a different LLM provider?**
A: Yes! Just change the `MLX_SERVER_URL` to point to any OpenAI-compatible API (OpenAI, Anthropic, Ollama, etc.). The code is provider-agnostic.

## Next Steps

1. ✅ Set up MLX server on macOS laptop (see `docs/mlx_server_setup.md`)
2. ✅ Configure Tailscale on both devices
3. ✅ Update `.env` with Tailscale IP
4. ✅ Test connection with provided Python snippet
5. ✅ Proceed with development!

## Additional Resources

- **MLX Documentation**: https://ml-explore.github.io/mlx/
- **mlx-lm Server**: https://github.com/ml-explore/mlx-lm
- **Tailscale Docs**: https://tailscale.com/kb/
- **OpenAI API Reference**: https://platform.openai.com/docs/api-reference (our API is compatible)
