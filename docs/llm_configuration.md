# LLM Configuration Guide

## Overview

The automation platform supports multiple LLM providers through a unified OpenAI-compatible interface. Choose the configuration that best fits your environment.

## Dual-Environment Strategy

### Development Environment (Recommended: Together.ai)
- **Use Case**: Development in Codespaces or any Linux environment
- **Provider**: Together.ai hosted API
- **Cost**: ~$0.20 per 1M tokens (very affordable for email classification)
- **Latency**: Low (~100-300ms per request)
- **Setup**: 5 minutes

### Production Environment (Recommended: MLX)
- **Use Case**: Production deployment on macOS laptop
- **Provider**: Local MLX server
- **Cost**: Free
- **Latency**: Very low (~50-200ms per request)
- **Setup**: 15 minutes

## Configuration Options

### Option 1: Together.ai (Development)

**Best for**: Development, testing, Codespaces environments

#### Setup Steps

1. **Sign up for Together.ai**
   - Visit: https://api.together.xyz/
   - Create account (credit card required, but very cheap usage)

2. **Get API Key**
   - Go to: https://api.together.xyz/settings/api-keys
   - Click "Create API Key"
   - Copy the key

3. **Configure Environment**
   ```bash
   # In your .env file
   LLM_BASE_URL=https://api.together.xyz/v1
   LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
   LLM_API_KEY=your-together-api-key-here
   ```

4. **Verify Connection**
   ```python
   from src.integrations.llm_client import LLMClient
   from src.core.config import Config

   client = LLMClient()
   result = client.classify_email(
       sender="test@example.com",
       subject="Meeting tomorrow",
       content="Can you attend?",
       label_config=Config.load_label_config()
   )
   print(f"Classification: {result}")
   ```

#### Recommended Models

| Model | Speed | Quality | Cost (per 1M tokens) | Context |
|-------|-------|---------|---------------------|---------|
| Meta-Llama-3.1-8B-Instruct-Turbo | Very Fast | Good | $0.18 input / $0.18 output | 128K |
| Meta-Llama-3.1-70B-Instruct-Turbo | Fast | Excellent | $0.88 input / $0.88 output | 128K |
| Qwen/Qwen2.5-7B-Instruct-Turbo | Very Fast | Good | $0.20 input / $0.20 output | 32K |

For email classification, the 8B model is more than sufficient.

#### Cost Estimation

Typical email classification costs:
- Email size: ~500 tokens (sender, subject, content)
- Prompt overhead: ~150 tokens (label definitions, instructions)
- Response: ~10 tokens (just the label name)
- **Total per email**: ~660 tokens = $0.0001 (0.01 cents per email)

For 100 emails/day: **$0.01/day = $3.65/year**

### Option 2: Local MLX Server (Production)

**Best for**: Production on macOS with Apple Silicon

#### Prerequisites
- macOS with Apple Silicon (M1, M2, M3, or M4)
- Python 3.12+
- At least 4GB free RAM

#### Setup Steps

1. **Install MLX LM**
   ```bash
   # On your macOS laptop
   pip install mlx-lm
   ```

2. **Start MLX Server**
   ```bash
   mlx_lm.server \
     --model mlx-community/Llama-3.2-3B-Instruct-4bit \
     --host 0.0.0.0 \
     --port 8080
   ```

   The model will download automatically on first run (~1.5GB).

3. **Configure Environment**
   ```bash
   # In your .env file
   LLM_BASE_URL=http://localhost:8080/v1
   LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
   LLM_API_KEY=not-needed
   ```

4. **Run as Background Service** (Optional)

   Create `~/Library/LaunchAgents/com.user.mlx-server.plist`:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>Label</key>
       <string>com.user.mlx-server</string>
       <key>ProgramArguments</key>
       <array>
           <string>/path/to/venv/bin/mlx_lm.server</string>
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
   </dict>
   </plist>
   ```

   Load the service:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.user.mlx-server.plist
   ```

#### Recommended Models

| Model | Size | Speed | Quality | Memory |
|-------|------|-------|---------|--------|
| Llama-3.2-1B-Instruct-4bit | ~0.5GB | Very Fast | Good | ~1GB RAM |
| Llama-3.2-3B-Instruct-4bit | ~1.5GB | Fast | Better | ~2GB RAM |
| Mistral-7B-Instruct-v0.3-4bit | ~4GB | Medium | Best | ~5GB RAM |

All models are from `mlx-community` on Hugging Face and optimized for Apple Silicon.

### Option 3: OpenAI (Alternative)

**Best for**: Testing, comparison, when you need GPT-4 quality

#### Setup Steps

1. **Get API Key**
   - Visit: https://platform.openai.com/api-keys
   - Create API key

2. **Configure Environment**
   ```bash
   # In your .env file
   LLM_BASE_URL=https://api.openai.com/v1
   LLM_MODEL=gpt-4o-mini
   LLM_API_KEY=your-openai-api-key-here
   ```

#### Cost Comparison

OpenAI pricing (as of 2024):
- GPT-4o-mini: $0.15 input / $0.60 output per 1M tokens
- For 100 emails/day: ~$0.05/day = **$18/year**

About 5x more expensive than Together.ai, but still very affordable.

## Switching Between Providers

The application uses environment variables, so switching is easy:

### Development → Production
```bash
# Development (.env in Codespaces)
LLM_BASE_URL=https://api.together.xyz/v1
LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
LLM_API_KEY=your-api-key

# Production (.env on macOS laptop)
LLM_BASE_URL=http://localhost:8080/v1
LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
LLM_API_KEY=not-needed
```

Just copy your code to production and update the `.env` file. No code changes needed!

## Troubleshooting

### Together.ai Issues

**Error**: `Authentication failed`
- **Solution**: Check your API key is correct and has credits

**Error**: `Model not found`
- **Solution**: Verify model name. Get list at: https://docs.together.ai/docs/inference-models

**Error**: `Rate limit exceeded`
- **Solution**: Wait a moment or upgrade your Together.ai plan

### MLX Server Issues

**Error**: `Cannot connect to LLM API`
- **Solution**: Ensure MLX server is running: `curl http://localhost:8080/v1/models`

**Error**: `ImportError: libmlx.so: cannot open shared object file`
- **Solution**: MLX only works on macOS with Apple Silicon. Use Together.ai for development.

**Error**: `Slow inference`
- **Solution**: Use smaller model (1B instead of 3B) or close other apps

### General Issues

**Error**: `LLM_BASE_URL environment variable must be set`
- **Solution**: Copy `.env.example` to `.env` and configure it

**Error**: `Invalid label returned`
- **Solution**: Model may need better prompting. Edit label descriptions in `config/labels.json`

## Performance Comparison

| Provider | Latency | Cost/Email | Setup Time | Internet Required |
|----------|---------|------------|------------|-------------------|
| Together.ai | 100-300ms | $0.0001 | 5 min | Yes |
| MLX (local) | 50-200ms | Free | 15 min | No (after setup) |
| OpenAI | 200-500ms | $0.0005 | 5 min | Yes |

## Security Considerations

### Together.ai
- ✅ SOC 2 Type II certified
- ✅ Data not used for training
- ✅ HTTPS encryption
- ❌ Data leaves your infrastructure

### MLX (Local)
- ✅ All data stays on your laptop
- ✅ No internet required (after model download)
- ✅ Complete privacy
- ✅ No API key management

### OpenAI
- ✅ Industry standard security
- ✅ Data not used for training (as of March 2023)
- ✅ HTTPS encryption
- ❌ Data leaves your infrastructure

## Recommended Workflow

1. **Development Phase**: Use Together.ai
   - Fast setup
   - No local server management
   - Easy debugging
   - Low cost

2. **Testing Phase**: Test with both Together.ai and MLX
   - Verify consistency
   - Compare performance
   - Validate on production hardware

3. **Production Phase**: Use MLX on macOS laptop
   - Free operation
   - Complete privacy
   - Fast inference
   - Offline capable

## Next Steps

After configuring your LLM provider:

1. ✅ Verify connection works (see verification steps above)
2. ✅ Test email classification with sample emails
3. ✅ Proceed to Phase 3: Gmail Integration
4. ✅ Test end-to-end workflow in Phase 4

For more details on MLX server setup, see `docs/mlx_server_setup.md`.
