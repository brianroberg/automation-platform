# Development Environment Guide

## Architecture Overview

This project uses a **dual-environment strategy** for LLM inference:

- **Development**: Together.ai hosted API (or other OpenAI-compatible providers)
- **Production**: MLX server running locally on macOS laptop
- **Interface**: Unified OpenAI-compatible client library

This enables fast, flexible development while maintaining production performance on Apple Silicon.

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

### The Solution: Dual Environment

Instead of complex network setups, we use **different providers for different environments**:

#### Development (Codespaces/Linux)
- **Provider**: Together.ai (recommended) or OpenAI
- **Setup**: 5 minutes (just get an API key)
- **Cost**: ~$0.0001 per email (~$4/year for 100 emails/day)
- **Benefits**:
  - No local server management
  - Works anywhere
  - Fast and reliable
  - Easy debugging

#### Production (macOS Laptop)
- **Provider**: MLX server (localhost)
- **Setup**: 15 minutes (install and start server)
- **Cost**: Free
- **Benefits**:
  - Complete privacy
  - No ongoing costs
  - Fast inference
  - Offline capable

This approach:
- ✅ No complex networking (Tailscale not needed)
- ✅ Fast development iteration
- ✅ Low cost for development
- ✅ Free production operation
- ✅ No code changes between environments

## Quick Start

### For Development (Codespaces/Linux)

**Recommended**: Use Together.ai

1. **Sign up for Together.ai**
   - Visit: https://api.together.xyz/
   - Create account (requires credit card, but very cheap)

2. **Get API Key**
   - Go to: https://api.together.xyz/settings/api-keys
   - Create new API key
   - Copy the key

3. **Configure Environment**
   ```bash
   # Create .env file
   cp .env.example .env

   # Edit .env (or use these commands)
   cat > .env << 'EOF'
   # LLM Configuration
   LLM_BASE_URL=https://api.together.xyz/v1
   LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
   LLM_API_KEY=your-together-api-key-here

   # Gmail Configuration
   GMAIL_CREDENTIALS_FILE=config/gmail_credentials.json
   GMAIL_TOKEN_FILE=config/gmail_token.json
   LABEL_CONFIG_FILE=config/labels.json

   # Logging
   LOG_LEVEL=INFO
   LOG_FILE=data/logs/email_triage.log
   EOF
   ```

4. **Test Connection**
   ```python
   from src.integrations.llm_client import LLMClient
   from src.core.config import Config

   # This will connect to Together.ai
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

### For Production (macOS Laptop)

1. **Install MLX Server**
   ```bash
   pip install mlx-lm
   ```

2. **Start Server**
   ```bash
   mlx_lm.server \
     --model mlx-community/Llama-3.2-3B-Instruct-4bit \
     --port 8080
   ```

3. **Configure Environment**
   ```bash
   # In .env on macOS laptop
   LLM_BASE_URL=http://localhost:8080/v1
   LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
   LLM_API_KEY=not-needed
   ```

See `docs/mlx_server_setup.md` for detailed setup instructions.

## Environment Configuration

### Required Environment Variables

```bash
# Development (.env in Codespaces)
LLM_BASE_URL=https://api.together.xyz/v1
LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
LLM_API_KEY=your-together-api-key-here

# Production (.env on macOS)
LLM_BASE_URL=http://localhost:8080/v1
LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
LLM_API_KEY=not-needed
```

### How It Works

The `LLMClient` automatically adapts based on environment variables:

```python
# In src/integrations/llm_client.py
self.base_url = os.getenv("LLM_BASE_URL")
self.api_key = os.getenv("LLM_API_KEY") or "not-needed"
self.model = os.getenv("LLM_MODEL")

client = OpenAI(base_url=self.base_url, api_key=self.api_key)
```

No code changes needed between environments!

## Development Workflows

### Scenario 1: Developing in Codespaces (Recommended)

**Prerequisites**:
- Together.ai API key

**Workflow**:
1. Open project in Codespaces
2. Create `.env` file with Together.ai configuration
3. Develop and test normally - LLM calls go to Together.ai API

**Architecture**:
```
Codespaces (Linux)
    ↓ HTTPS API calls
Together.ai (hosted)
    ↓
LLM Model (hosted)
```

**Benefits**:
- ✅ No server management
- ✅ Works immediately
- ✅ Fast iteration
- ✅ Low cost (~$0.0001/email)

### Scenario 2: Developing on macOS Locally

Two options when developing on your macOS laptop:

**Option A: Use Together.ai (same as Codespaces)**
- Keeps configuration consistent with Codespaces
- Doesn't require running MLX server
- Good for early development

**Option B: Use MLX locally**
- Tests production configuration
- Requires running MLX server
- Good for final testing before deployment

### Scenario 3: Production Deployment

Production runs on macOS laptop with local MLX server:

```bash
# In production .env on macOS laptop
LLM_BASE_URL=http://localhost:8080/v1
LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
LLM_API_KEY=not-needed
```

**Architecture**:
```
Email Triage Script
    ↓ HTTP (localhost)
MLX Server (port 8080)
    ↓
Local LLM Model
```

**Benefits**:
- ✅ Free operation
- ✅ Complete privacy
- ✅ Fast inference
- ✅ Works offline

## Troubleshooting

### Together.ai Issues

**Error**: `Cannot connect to LLM API`
- **Solution**: Check your API key is correct and has credits
- **Test**: `curl https://api.together.xyz/v1/models -H "Authorization: Bearer your-key"`

**Error**: `Authentication failed`
- **Solution**: Verify API key in `.env` file matches your Together.ai dashboard

**Error**: `Rate limit exceeded`
- **Solution**: Wait a moment or upgrade your Together.ai plan
- **Note**: Free tier has generous limits for email classification

**Error**: `Model not found`
- **Solution**: Verify model name. See available models at: https://docs.together.ai/docs/inference-models
- **Recommended**: Use `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo`

### MLX Server Issues

**Error**: `Cannot connect to LLM API at http://localhost:8080`
- **Solution**: Ensure MLX server is running
- **Test**: `curl http://localhost:8080/v1/models`
- **Start server**: `mlx_lm.server --model mlx-community/Llama-3.2-3B-Instruct-4bit`

**Error**: `ImportError: libmlx.so: cannot open shared object file`
- **Solution**: MLX only works on macOS with Apple Silicon
- **For development**: Use Together.ai instead (see above)

**Error**: `Server returns errors`
- **Solution**: Check server logs in terminal where server is running
- **Solution**: Verify model name matches what server has loaded
- **Solution**: Try restarting MLX server

**Error**: `Model download fails`
- **Solution**: Check internet connection
- **Solution**: Clear cache: `rm -rf ~/.cache/huggingface/`
- **Solution**: Try downloading manually: `huggingface-cli download mlx-community/Llama-3.2-3B-Instruct-4bit`

### Performance Issues

**Problem**: Slow classification (Together.ai)
- **Expected**: 100-300ms per email
- **Solution**: Check your internet connection
- **Solution**: Try different region if available

**Problem**: Slow classification (MLX)
- **Expected**: 50-200ms per email
- **Solution**: Use smaller model (1B instead of 3B)
- **Solution**: Close other applications to free RAM
- **Solution**: Ensure Mac isn't in low-power mode

### Configuration Issues

**Error**: `LLM_BASE_URL environment variable must be set`
- **Solution**: Copy `.env.example` to `.env` and configure it
- **Check**: Environment file exists and is named `.env` (not `.env.txt`)

**Error**: `Invalid label returned by LLM`
- **Problem**: Model not following classification instructions
- **Solution**: Edit label descriptions in `config/labels.json` to be more specific
- **Solution**: Try different model (GPT-4o-mini on OpenAI is more reliable)

## Alternative Providers

The LLMClient supports any OpenAI-compatible API. Here are more options:

### OpenAI

```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=your-openai-api-key
```

**Pros**: Highest quality, most reliable
**Cons**: More expensive (~5x Together.ai cost)

### Anthropic (via proxy)

Requires OpenAI-compatible proxy like LiteLLM:

```bash
# First, run LiteLLM proxy locally
# pip install litellm
# litellm --model claude-3-sonnet-20240229

LLM_BASE_URL=http://localhost:8000/v1
LLM_MODEL=claude-3-sonnet-20240229
LLM_API_KEY=your-anthropic-api-key
```

### Ollama (local, alternative to MLX)

```bash
# First, install and start Ollama
# curl -fsSL https://ollama.com/install.sh | sh
# ollama serve
# ollama pull llama3.2

LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2
LLM_API_KEY=not-needed
```

**Pros**: Free, works on Linux/macOS/Windows
**Cons**: Slower than MLX on Apple Silicon

## Security Considerations

### Together.ai (Development)

- ✅ SOC 2 Type II certified
- ✅ Data not used for model training
- ✅ HTTPS encryption in transit
- ✅ API key authentication
- ⚠️ Data leaves your infrastructure
- ⚠️ Subject to provider's terms of service

**Best Practices**:
- Store API keys in `.env` file (never commit to git)
- Use separate API keys for development and production (if using Together.ai in prod)
- Rotate API keys periodically
- Monitor usage and costs

### MLX Server (Production)

- ✅ All data stays on your laptop
- ✅ No internet required after model download
- ✅ Complete privacy
- ✅ No API key needed
- ⚠️ Server not hardened for public exposure (fine for localhost)

**Best Practices**:
- Only bind to `localhost` (not `0.0.0.0`) unless needed
- Don't expose port 8080 to internet
- Keep macOS firewall enabled
- Regular OS security updates

### Data Privacy Comparison

| Provider | Data Location | Training Usage | Internet Required | Privacy Level |
|----------|---------------|----------------|-------------------|---------------|
| Together.ai | Third-party servers | No | Yes | Medium |
| OpenAI | Third-party servers | No (as of Mar 2023) | Yes | Medium |
| MLX (local) | Your laptop only | N/A | No* | High |

*Internet required only for initial model download

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

**Q: Do I need a Together.ai account for development?**
A: Yes, for the recommended setup. Alternatively, use OpenAI or run MLX server locally.

**Q: How much does Together.ai cost?**
A: Very cheap! About $0.0001 per email (~$4/year for 100 emails/day).

**Q: Can I develop without any API costs?**
A: Yes, if you have a Mac with Apple Silicon. Run MLX server locally and use it for development too.

**Q: What if I don't have a Mac for production?**
A: Use Together.ai or OpenAI for both development and production. Just set the same config in both environments.

**Q: Can I use this in CI/CD?**
A: Yes! The tests mock the LLM client, so no API key or server needed for automated testing.

**Q: What about data privacy?**
A: Development (Together.ai): Data sent to third-party. Production (MLX): All data stays on your laptop.

**Q: Can I switch providers later?**
A: Yes! Just update the `.env` file. No code changes needed. The LLMClient works with any OpenAI-compatible API.

**Q: Do I need Tailscale?**
A: No! The new dual-environment approach doesn't require Tailscale. Just use Together.ai for dev and MLX for prod.

## Next Steps

### For Development (Recommended Path)

1. ✅ Sign up for Together.ai account
2. ✅ Get API key from dashboard
3. ✅ Create `.env` file with Together.ai configuration
4. ✅ Test connection (see Quick Start section above)
5. ✅ Proceed with Phase 3: Gmail Integration

### For Production (Later)

1. ✅ Install MLX server on macOS laptop
2. ✅ Download and test model
3. ✅ Update `.env` for production
4. ✅ Test end-to-end workflow

See `docs/llm_configuration.md` for comprehensive setup guide.

## Additional Resources

- **Together.ai Documentation**: https://docs.together.ai/
- **Together.ai Pricing**: https://www.together.ai/pricing
- **MLX Documentation**: https://ml-explore.github.io/mlx/
- **mlx-lm Server**: https://github.com/ml-explore/mlx-lm
- **OpenAI API Reference**: https://platform.openai.com/docs/api-reference (our API is compatible)
