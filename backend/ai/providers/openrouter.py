"""
ai/providers/openrouter.py — OpenRouterProvider

Refactored from services/llm_service.py. All streaming + structured output
logic now lives here, behind the BaseProvider interface.
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
    supports_tools=True,
    supports_json=True,
    supports_images=False,
    supports_vision=False,
    max_context_tokens=200_000,
    models=(
        "moonshotai/kimi-k2.6:free",
        "deepseek/deepseek-r1-0528:free",
        "qwen/qwen3-235b-a22b:free",
        "meta-llama/llama-3.3-70b-instruct:free",
    ),
)


class OpenRouterProvider(BaseProvider):
    name = "openrouter"
    capabilities = _CAPABILITIES

    def __init__(self) -> None:
        self._api_key = settings.OPENROUTER_API_KEY
        self._base_url = settings.OPENROUTER_BASE_URL
        self._site_url = settings.OPENROUTER_SITE_URL
        self._app_name = settings.OPENROUTER_APP_NAME

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": self._site_url,
            "X-Title": self._app_name,
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: list[dict],
        config: GenerationConfig,
        stream: bool = True,
    ) -> dict:
        payload: dict = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens,
            "stream": stream,
        }
        if config.json_mode and self.capabilities.supports_json:
            payload["response_format"] = {"type": "json_object"}
        if settings.OPENROUTER_REASONING_ENABLED:
            payload["reasoning"] = {"effort": "low", "exclude": False}
        return payload

    async def generate(
        self,
        messages: list[dict],
        config: GenerationConfig,
    ) -> AsyncGenerator[str, None]:
        """Stream text tokens from OpenRouter."""
        payload = self._build_payload(messages, config, stream=True)

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def generate_structured(
        self,
        messages: list[dict],
        schema: Type[BaseModel],
        config: GenerationConfig,
    ) -> BaseModel:
        """Return a validated Pydantic model using JSON mode."""
        config = config.model_copy(update={"json_mode": True, "stream": False})
        payload = self._build_payload(messages, config, stream=False)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        raw_content = data["choices"][0]["message"]["content"]
        return schema.model_validate_json(raw_content)

    async def health_check(self) -> bool:
        """Ping OpenRouter to verify connectivity."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self._base_url}/models",
                    headers=self._headers(),
                )
                return resp.status_code == 200
        except Exception:
            return False
