"""
services/llm_service.py — OpenRouter streaming integration

Moved from the project root to the layered architecture.
Import path for sanitize_token updated to utils.streaming.
"""
import json
import os
import re
from typing import AsyncGenerator

import httpx
import logging

from utils.streaming import sanitize_token

from core.config import get_settings

logger = logging.getLogger("ai-site-gen")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def _get_config() -> dict:
    settings = get_settings()
    return {
        "model_id": settings.OPENROUTER_MODEL,
        "api_key": settings.OPENROUTER_API_KEY,
        "base_url": settings.OPENROUTER_BASE_URL,
        "site_url": settings.OPENROUTER_SITE_URL,
        "app_name": settings.OPENROUTER_APP_NAME,
        "temperature": settings.TEMPERATURE,
        "top_p": settings.TOP_P,
        "max_new_tokens": settings.MAX_NEW_TOKENS,
        "reasoning_enabled": settings.OPENROUTER_REASONING_ENABLED,
    }


MODEL_ID = _get_config()["model_id"]


def _strip_think_blocks(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<think>.*$", "", text, flags=re.IGNORECASE | re.DOTALL)
    return text


def _chunk_text(text: str, size: int = 160) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def _title_from_prompt(prompt: str) -> str:
    lowered = prompt.lower()
    if any(keyword in lowered for keyword in ["dashboard", "analytics", "stats", "admin"]):
        return "Neon Control"
    if any(keyword in lowered for keyword in ["portfolio", "developer", "designer", "freelance"]):
        return "Studio Profile"
    if any(keyword in lowered for keyword in ["shop", "store", "product", "e-commerce", "ecommerce"]):
        return "Orbital Store"
    if any(keyword in lowered for keyword in ["blog", "article", "magazine", "newsletter"]):
        return "Signal Journal"
    return "Pulse Landing"


def _fallback_html(prompt: str) -> str:
    title = _title_from_prompt(prompt)
    summary = (
        "A premium dark interface with bold contrast, glassy panels, sharp metrics, and a deliberate neon accent system."
        if len(prompt) < 140
        else prompt[:140].rstrip() + "\u2026"
    )
    return f"""<main class="min-h-screen bg-slate-950 text-slate-100">
    <section class="mx-auto max-w-7xl px-6 py-8">
        <div class="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl shadow-cyan-500/10 backdrop-blur-xl">
            <div class="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
                <div class="max-w-3xl">
                    <p class="mb-3 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.3em] text-cyan-300">Generated fallback</p>
                    <h1 class="text-4xl font-black tracking-tight text-white md:text-6xl">{title}</h1>
                    <p class="mt-4 max-w-2xl text-sm leading-7 text-slate-300 md:text-base">{summary}</p>
                </div>
            </div>
        </div>
    </section>
</main>"""


async def _emit_fallback(prompt: str) -> AsyncGenerator[str, None]:
    for chunk in _chunk_text(_fallback_html(prompt), 180):
        yield chunk


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """\
You are an elite product designer and frontend engineer.

Return one complete, production-ready HTML document body that is visually striking, responsive, and easy to export.

CRITICAL RULES:
1. Return ONLY HTML. No markdown, no code fences, no commentary.
2. Do NOT include <script> tags.
3. Use Tailwind CSS utility classes for all visual styling.
4. Prefer clean layout structure, strong hierarchy, deliberate spacing, and polished copy.
5. Make the design feel premium, modern, and purposeful.
6. Include realistic placeholder content and useful UI details.
7. Keep components self-contained and export-friendly.
8. Start with a valid HTML tag immediately.
9. Do not expose reasoning or <think> blocks in the final output.
10. Avoid empty sections, generic lorem ipsum, or filler text.
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

    if not cfg["api_key"] or cfg["api_key"] in ("your_openrouter_key", "CHANGE_ME"):
        logger.warning("OPENROUTER_API_KEY is not configured or using placeholder; using fallback renderer.")
        async for chunk in _emit_fallback(prompt):
            yield chunk
        return

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

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
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
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning(f"OpenRouter API error ({exc}); using fallback renderer.")
            async for chunk in _emit_fallback(prompt):
                yield chunk
            return
