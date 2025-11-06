# Development Environment Guide

## Architecture

Both development and production rely on the same MLX-backed LLM service running on an Apple Silicon
Mac. Development environments (e.g. GitHub Codespaces) route requests to that MLX server through a
secure mesh network such as Tailscale.

```
Codespace ──▶ Tailscale ──▶ macOS laptop ──▶ mlx_lm.server
```

This keeps data on trusted hardware, avoids hosted inference services, and ensures parity between
environments.

## Setup Checklist

1. **Provision access to the MLX host**
   - Install [Tailscale](https://tailscale.com/) (or another secure tunnel) on the Mac and on the
     development environment.
   - Verify you can reach the Mac from the development environment.

2. **Install MLX tooling on the Mac**
   ```bash
   python3 -m pip install mlx-lm
   ```

3. **Launch the MLX HTTP server**
   ```bash
   mlx_lm.server \
     --model mlx-community/Llama-3.2-3B-Instruct-4bit \
     --host 0.0.0.0 \
     --port 8080
   ```

4. **Configure the application environment**
   ```bash
   cp .env.example .env
   # Edit LLM_BASE_URL to point at the MLX host, e.g.
   LLM_BASE_URL=http://<tailscale-host>:8080/v1
   LLM_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit
   LLM_API_KEY=not-needed
   ```

5. **Confirm connectivity**
   ```bash
   curl http://<tailscale-host>:8080/v1/models
   python -c "from src.integrations.llm_client import LLMClient; LLMClient()"
   ```

## Local vs Remote Development

### Developing inside Codespaces / Containers

- Ensure the container joins the same Tailscale tailnet as the Mac.
- Store Tailscale auth details securely (e.g. use ephemeral auth keys).
- Update `.env` with the tailnet hostname or IP.
- Run tests normally; all LLM calls are proxied to the Mac.

### Developing directly on the Mac

- Use `LLM_BASE_URL=http://localhost:8080/v1`.
- Optionally keep Tailscale running for parity with remote environments.
- The rest of the workflow is identical.

## Operational Tips

- **Server persistence**: run the MLX server under LaunchAgents (see `docs/llm_configuration.md`).
- **Model selection**: start with `mlx-community/Llama-3.2-3B-Instruct-4bit`. Switch models by
  restarting `mlx_lm.server` and updating `.env`.
- **Security**: restrict MLX access to the tailnet; do not expose the port publicly.
- **Monitoring**: tail `mlx_lm.server` logs on the Mac to observe request volume and errors.

## Troubleshooting

- `Connection refused`: ensure the MLX server is running and the tunnel is active.
- `LLM classification failed`: confirms `LLM_BASE_URL` and `LLM_MODEL` match the server.
- `ImportError: libmlx.so`: indicates you attempted to run MLX natively on Linux—only the Mac should
  host MLX.

With this setup, every environment relies on the same inference infrastructure, simplifying testing,
compliance, and maintenance.
