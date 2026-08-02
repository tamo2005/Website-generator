"""
ai/providers/gemini.py — GeminiProvider

Uses the Google Generative AI SDK (google-generativeai).
Gemini 2.5 Flash: free tier, 1M token context, JSON mode, vision.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator, Type

from pydantic import BaseModel

from ai.providers.base import BaseProvider, GenerationConfig, ProviderCapabilities
from core.config import get_settings

logger = logging.getLogger("ai-site-gen")

settings = get_settings()

_CAPABILITIES = ProviderCapabilities(
    supports_streaming=True,
    supports_tools=True,
    supports_json=True,
    supports_images=True,
    supports_vision=True,
    max_context_tokens=1_000_000,
    models=("gemini-2.5-flash", "gemini-2.5-pro"),
)


class GeminiProvider(BaseProvider):
    name = "gemini"
    capabilities = _CAPABILITIES

    def __init__(self) -> None:
        self._api_key = settings.GEMINI_API_KEY
        self._client = None

    def _get_client(self):
        """Lazy-load the Gemini client to avoid import errors if SDK not configured."""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._client = genai
            except ImportError:
                raise RuntimeError(
                    "google-generativeai package is required for GeminiProvider. "
                    "Run: pip install google-generativeai"
                )
        return self._client

    def _to_gemini_messages(self, messages: list[dict]) -> tuple[str, list]:
        """
        Convert OpenAI-format messages to Gemini format.
        Returns (system_instruction, history).
        """
        system_instruction = ""
        history = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_instruction = content
            elif role == "user":
                history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                history.append({"role": "model", "parts": [content]})

        return system_instruction, history

    async def generate(
        self,
        messages: list[dict],
        config: GenerationConfig,
    ) -> AsyncGenerator[str, None]:
        """Stream text tokens from Gemini."""
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is not configured. Add it to .env to use GeminiProvider.")

        genai = self._get_client()
        system_instruction, history = self._to_gemini_messages(messages)

        generation_config = {
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_output_tokens": config.max_tokens,
        }

        model = genai.GenerativeModel(
            model_name=config.model,
            system_instruction=system_instruction or None,
            generation_config=generation_config,
        )

        # Build the prompt from history
        if history:
            # Use last user message as the prompt
            last_user = next(
                (h["parts"][0] for h in reversed(history) if h["role"] == "user"),
                "",
            )
        else:
            last_user = ""

        # Use streaming generation
        response = await model.generate_content_async(
            last_user,
            stream=True,
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def generate_structured(
        self,
        messages: list[dict],
        schema: Type[BaseModel],
        config: GenerationConfig,
    ) -> BaseModel:
        """Return a validated Pydantic model using Gemini JSON mode."""
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        genai = self._get_client()
        system_instruction, history = self._to_gemini_messages(messages)

        generation_config = {
            "temperature": config.temperature,
            "max_output_tokens": config.max_tokens,
            "response_mime_type": "application/json",
        }

        model = genai.GenerativeModel(
            model_name=config.model,
            system_instruction=system_instruction or None,
            generation_config=generation_config,
        )

        last_user = next(
            (h["parts"][0] for h in reversed(history) if h["role"] == "user"),
            "",
        )
        response = await model.generate_content_async(last_user)
        return schema.model_validate_json(response.text)

    async def health_check(self) -> bool:
        """Verify the Gemini API key is configured and reachable."""
        if not self._api_key:
            return False
        try:
            genai = self._get_client()
            models = genai.list_models()
            return any(True for _ in models)
        except Exception:
            return False
