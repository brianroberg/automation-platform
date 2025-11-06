# LLM Configuration Guide

## Overview

The automation platform communicates with an OpenAI-compatible HTTP endpoint for email
classification. The recommended and supported configuration for both development and production is a
locally hosted MLX server running on an Apple Silicon Mac. Development environments (such as
Codespaces) reach that server across a private network tunnel like Tailscale.

```
Codespace ──▶ Tailscale ──▶ macOS laptop running mlx_lm.server
```

This keeps all email content on hardware you control while preserving a consistent setup between
development and production.

## MLX Server Configuration

### 1. Prerequisites

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.12+
- [mlx-lm](https://github.com/ml-explore/mlx-examples) installed on the laptop
- Optional: Tailscale (or another secure mesh/VPN) connecting the laptop and development environment

Install MLX tooling on the laptop:

```bash
python3 -m pip install mlx-lm
```

### 2. Launch the Server

Run the MLX HTTP server on your laptop:

```bash
mlx_lm.server \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --host 0.0.0.0 \
  --port 8080
```

Notes:

- Models download on first launch; ensure sufficient disk space (≈1.5 GB for the 3B 4-bit model).
- `--host 0.0.0.0` allows remote connections. Restrict access via firewall rules and your mesh/VPN.
- Smaller models (e.g. `mlx-community/Llama-3.2-1B-Instruct-4bit`) reduce memory usage if needed.

### 3. Connect from Development

Verify that the development environment can reach the MLX server:

```bash
curl http://<tailscale-host>:8080/v1/models
```

If the request succeeds, update `.env` in the repo:

```bash
LLM_BASE_URL=http://<tailscale-host>:8080/v1
LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
LLM_API_KEY=not-needed
```

When working directly on the laptop, `LLM_BASE_URL=http://localhost:8080/v1` is sufficient.

### 4. Optional LaunchDaemon (macOS)

Keep the MLX server running in the background by creating `~/Library/LaunchAgents/com.user.mlx-server.plist`:

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

Load it with:

```bash
launchctl load ~/Library/LaunchAgents/com.user.mlx-server.plist
```

## Optional Providers

While MLX is the project default, any OpenAI-compatible API works. Override the `.env` values to use
another provider:

```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=your-openai-api-key
```

Ensure you comply with your provider’s data handling policies before sending email content.

## Troubleshooting

### Unable to Reach MLX Server
- Confirm the server is running (`ps aux | grep mlx_lm.server`).
- Check that Tailscale or your VPN is connected on both machines.
- Verify firewall rules allow inbound connections on port 8080.
- Use `curl http://localhost:8080/v1/models` on the laptop to ensure the server is responsive.

### Invalid Model Errors
- `mlx_lm.server` must be started with the same model configured in `.env`.
- Restart the server after changing models to ensure the new configuration is active.

### Authentication Failures
- MLX does not require an API key. Remove stale `LLM_API_KEY` values or set it to `not-needed`.
- If another provider is used, double-check the key and base URL.

### Performance Tuning
- Smaller quantized models reduce memory but may lower accuracy.
- Use `mlx-community/Llama-3.2-3B-Instruct-4bit` as the baseline and adjust based on accuracy needs.
- Enable caching at the VPN/mesh level if latency is high.

## Security Considerations

- All inference traffic stays on hardware you control.
- Restrict MLX access to the mesh network; do not expose it to the public internet.
- Rotate mesh/VPN credentials regularly and monitor access logs.

This configuration keeps development and production aligned, simplifies testing, and avoids reliance on
third-party hosted LLM services.
