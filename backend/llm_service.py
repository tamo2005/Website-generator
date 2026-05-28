"""
llm_service.py — Transformers streaming integration for QwQ

Uses the latest Transformers chat-template path recommended by the QwQ model
card so the backend can format prompts correctly and stream generated HTML.
"""
import asyncio
import os
import re
import threading
from typing import AsyncGenerator

from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

from streaming import sanitize_token

# ---------------------------------------------------------------------------
# Configuration (read fresh on each module load after --reload)
# ---------------------------------------------------------------------------
def _get_config() -> dict:
    return {
        "model_id": os.getenv("MODEL_ID", "Qwen/QwQ-32B"),
        "hf_token": os.getenv("HF_TOKEN"),
        "temperature": float(os.getenv("TEMPERATURE", "0.6")),
        "top_p": float(os.getenv("TOP_P", "0.95")),
        "top_k": int(os.getenv("TOP_K", "40")),
        "repetition_penalty": float(os.getenv("REPETITION_PENALTY", "1.05")),
        "max_new_tokens": int(os.getenv("MAX_NEW_TOKENS", "2048")),
    }


MODEL_ID = _get_config()["model_id"]


_MODEL = None
_TOKENIZER = None
_MODEL_LOCK = threading.Lock()


def _load_model_and_tokenizer():
    global _MODEL, _TOKENIZER

    if _MODEL is not None and _TOKENIZER is not None:
        return _MODEL, _TOKENIZER

    with _MODEL_LOCK:
        if _MODEL is None or _TOKENIZER is None:
            cfg = _get_config()
            tokenizer = AutoTokenizer.from_pretrained(cfg["model_id"])
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            model = AutoModelForCausalLM.from_pretrained(
                cfg["model_id"],
                torch_dtype="auto",
                device_map="auto",
                token=cfg["hf_token"],
            )
            model.eval()

            _MODEL = model
            _TOKENIZER = tokenizer

    return _MODEL, _TOKENIZER


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
9. Do not expose reasoning or <think> blocks in the final output."""


# ---------------------------------------------------------------------------
# Streaming generator
# ---------------------------------------------------------------------------
async def stream_html_tokens(prompt: str) -> AsyncGenerator[str, None]:
    """
    Async generator that yields sanitized HTML token strings.

    QwQ expects a chat-template formatted prompt. We render the messages with
    apply_chat_template, then stream generation from Transformers using a
    TextIteratorStreamer.
    """
    cfg = _get_config()
    model, tokenizer = _load_model_and_tokenizer()

    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": prompt},
    ]

    chat_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    model_inputs = tokenizer([chat_text], return_tensors="pt")
    model_inputs = model_inputs.to(model.device)

    streamer = TextIteratorStreamer(
        tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
    )

    generation_kwargs = {
        **model_inputs,
        "streamer": streamer,
        "max_new_tokens": cfg["max_new_tokens"],
        "do_sample": True,
        "temperature": cfg["temperature"],
        "top_p": cfg["top_p"],
        "top_k": cfg["top_k"],
        "repetition_penalty": cfg["repetition_penalty"],
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def _run_generation():
        try:
            model.generate(**generation_kwargs)
        except Exception as exc:
            asyncio.run_coroutine_threadsafe(queue.put(f"__ERROR__:{exc}"), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    def _stream_to_queue():
        try:
            for chunk in streamer:
                if chunk:
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
        except Exception as exc:
            asyncio.run_coroutine_threadsafe(queue.put(f"__ERROR__:{exc}"), loop)

    generation_thread = threading.Thread(target=_run_generation, daemon=True)
    stream_thread = threading.Thread(target=_stream_to_queue, daemon=True)
    generation_thread.start()
    stream_thread.start()

    found_html_start = False
    raw_buffer = ""
    emitted_visible = ""

    while True:
        token_raw = await queue.get()

        if token_raw is None:
            break

        if isinstance(token_raw, str) and token_raw.startswith("__ERROR__:"):
            raise RuntimeError(token_raw[len("__ERROR__:"):])

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
