"""
ai/providers/ollama.py — OllamaProvider

Connects to a local Ollama instance via its REST API.
Zero API cost, zero rate limits, works fully offline.
RTX 3050 compatible models: qwen2.5:7b, llama3.1:8b, deepseek-r1:7b
"""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator, Type

import httpx
from pydantic import BaseModel

from ai.providers.base import BaseProvider, GenerationConfig, ProviderCapabilities
from core.config import get_settings

logger = logging.getLogger("ai-site-gen")

settings = get_settings()

_CAPABILITIES = ProviderCapabilities(
    supports_streaming=True,
    supports_tools=False,        # Depends on model — conservative default
    supports_json=True,          # Ollama supports JSON mode natively
    supports_images=False,
    supports_vision=False,
    max_context_tokens=128_000,  # Depends on model; qwen2.5:7b = 32K
    models=(
        "qwen2.5:7b",
        "llama3.1:8b",
        "deepseek-r1:7b",
        "mistral:7b",
    ),
)


class OllamaProvider(BaseProvider):
    name = "ollama"
    capabilities = _CAPABILITIES

    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")

    async def generate(
        self,
        messages: list[dict],
        config: GenerationConfig,
    ) -> AsyncGenerator[str, None]:
        """Stream text tokens from Ollama's /api/chat endpoint."""
        payload = {
            "model": config.model,
            "messages": messages,   # Ollama accepts OpenAI-format messages
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "num_predict": config.max_tokens,
            },
        }
        if config.json_mode:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done", False):
                            return
                    except (json.JSONDecodeError, KeyError):
                        continue

    async def generate_structured(
        self,
        messages: list[dict],
        schema: Type[BaseModel],
        config: GenerationConfig,
    ) -> BaseModel:
        """Return a validated Pydantic model using Ollama's JSON format mode."""
        config = config.model_copy(update={"json_mode": True, "stream": False})
        payload = {
            "model": config.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        raw_content = data["message"]["content"]
        return schema.model_validate_json(raw_content)

    async def health_check(self) -> bool:
        """Check if Ollama is running at OLLAMA_BASE_URL."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
