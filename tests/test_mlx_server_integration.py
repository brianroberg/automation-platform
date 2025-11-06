"""Integration test that exercises a real MLX server."""
import os
from urllib.parse import urlparse, urlunparse

import pytest
from openai import APIConnectionError, APITimeoutError, OpenAI

from src.core.config import Config


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("LLM_BASE_URL"),
    reason="LLM_BASE_URL must be set to run MLX connectivity test",
)
def test_mlx_server_connectivity():
    """Send a minimal prompt to the MLX server to verify connectivity."""
    base_url = os.environ["LLM_BASE_URL"].rstrip("/") + "/"
    api_key = os.getenv("LLM_API_KEY") or "not-needed"
    model = os.getenv("LLM_MODEL") or Config.LLM_MODEL

    def _with_host(url: str, host: str) -> str:
        parsed = urlparse(url)
        netloc = host
        if parsed.port:
            netloc = f"{host}:{parsed.port}"
        raw_path = parsed.path or "/"
        rebuilt = parsed._replace(netloc=netloc, path=raw_path if raw_path.endswith("/") else raw_path + "/")
        return urlunparse(rebuilt)

    candidate_urls: list[str] = []

    override_host = os.getenv("LLM_TEST_HOST")
    if override_host:
        candidate_urls.append(_with_host(base_url, override_host))

    candidate_urls.append(base_url)

    parsed = urlparse(base_url)
    hostname = parsed.hostname or ""
    if hostname and "." not in hostname:
        candidate_urls.append(_with_host(base_url, f"{hostname}.local"))

    errors: list[tuple[str, Exception]] = []

    for target_url in candidate_urls:
        client = OpenAI(base_url=target_url, api_key=api_key)
        try:
            models = client.models.list()
            assert models.data, f"MLX server at {target_url} returned no models"

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a connectivity test harness."},
                    {"role": "user", "content": "Reply with the single word PONG."},
                ],
                max_tokens=3,
                temperature=0.0,
            )

            assert response.choices, f"MLX server at {target_url} returned no choices"

            message = response.choices[0].message.content
            assert message, f"MLX server at {target_url} returned empty message"
            return
        except (APIConnectionError, APITimeoutError) as exc:
            errors.append((target_url, exc))

    formatted_errors = ", ".join(f"{url} -> {err}" for url, err in errors)
    pytest.fail(f"Unable to reach MLX server. Tried: {formatted_errors}")
