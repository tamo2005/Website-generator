"""
llm_service.py — OpenRouter streaming integration

Uses the OpenRouter OpenAI-compatible streaming API so the backend can stay
lightweight and avoid local model loading issues.
"""
import json
import os
import re
from typing import AsyncGenerator

import httpx

from streaming import sanitize_token


# ---------------------------------------------------------------------------
# Configuration (read fresh on each module load after --reload)
# ---------------------------------------------------------------------------
def _get_config() -> dict:
    return {
        "model_id": os.getenv("OPENROUTER_MODEL", os.getenv("MODEL_ID", "moonshotai/kimi-k2.6:free")),
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "site_url": os.getenv("OPENROUTER_SITE_URL", "http://localhost:3000"),
        "app_name": os.getenv("OPENROUTER_APP_NAME", "AI Website Generator"),
        "temperature": float(os.getenv("TEMPERATURE", "0.6")),
        "top_p": float(os.getenv("TOP_P", "0.95")),
        "max_new_tokens": int(os.getenv("MAX_NEW_TOKENS", "2048")),
        "reasoning_enabled": os.getenv("OPENROUTER_REASONING_ENABLED", "true").lower() in {"1", "true", "yes", "on"},
    }


MODEL_ID = _get_config()["model_id"]


def _strip_think_blocks(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<think>.*$", "", text, flags=re.IGNORECASE | re.DOTALL)
    return text


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """\
You are an expert senior frontend engineer specializing in beautiful, modern UI design.

CRITICAL RULES — follow them exactly:
1. Return ONLY valid HTML. Nothing else.
2. Do NOT include markdown code fences (no ``` or ```html).
3. Do NOT add explanations, comments, or any prose outside HTML tags.
4. Do NOT include <script> tags.
5. Use Tailwind CSS utility classes for ALL styling (they will be loaded via CDN).
6. Make the design visually stunning, responsive, and production-ready.
7. Include realistic placeholder content — no lorem ipsum.
8. Start your response directly with an HTML tag, no preamble.
9. Do not expose reasoning or <think> blocks in the final output.
"""


# ---------------------------------------------------------------------------
# Streaming generator
# ---------------------------------------------------------------------------
async def stream_html_tokens(prompt: str) -> AsyncGenerator[str, None]:
    """
    Async generator that yields sanitized HTML token strings.

    OpenRouter exposes an OpenAI-compatible streaming API, so we send the
    same system/user messages and forward each streamed delta into SSE.
    """
    cfg = _get_config()

    if not cfg["api_key"]:
        raise RuntimeError("OPENROUTER_API_KEY is not configured.")

    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": prompt},
    ]

    payload = {
        "model": cfg["model_id"],
        "messages": messages,
        "stream": True,
        "temperature": cfg["temperature"],
        "top_p": cfg["top_p"],
        "max_tokens": cfg["max_new_tokens"],
        "reasoning": {
            "enabled": cfg["reasoning_enabled"],
        },
    }

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
        "HTTP-Referer": cfg["site_url"],
        "X-Title": cfg["app_name"],
    }

    raw_buffer = ""
    emitted_visible = ""
    found_html_start = False

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            f"{cfg['base_url'].rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue

                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices") or []
                if not choices:
                    continue

                delta = choices[0].get("delta") or {}
                token_raw = delta.get("content") or ""
                if not token_raw:
                    continue

                raw_buffer += sanitize_token(token_raw)
                visible = _strip_think_blocks(raw_buffer)

                if not found_html_start:
                    idx = visible.find("<")
                    if idx == -1:
                        continue
                    visible = visible[idx:]
                    found_html_start = True

                if len(visible) <= len(emitted_visible):
                    continue

                new_text = visible[len(emitted_visible):]
                emitted_visible = visible

                if new_text:
                    yield new_text
