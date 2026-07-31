"""
utils/streaming.py — SSE formatting and token sanitization utilities

Moved from the project root to the layered architecture.
"""
import re


# Characters / sequences that should never be sent as part of HTML tokens
_FENCE_PATTERN = re.compile(r"```(?:html|css|javascript|tsx?|jsx?)?", re.IGNORECASE)
_TRAILING_FENCE = re.compile(r"```\s*$")


def sanitize_token(token: str) -> str:
    """
    Strip LLM artefacts from a single streaming token before forwarding
    to the client.

    Removes:
    - Opening markdown code fences  (```html, ``` etc.)
    - Closing fences                (```)
    - Bare backtick triples that sometimes leak through
    """
    token = _FENCE_PATTERN.sub("", token)
    token = _TRAILING_FENCE.sub("", token)
    # Collapse any lone triple-backtick remnant
    token = token.replace("```", "")
    return token


def format_sse(data: str) -> str:
    """
    Wrap *data* in the Server-Sent Events wire format.

    The spec requires each event to end with a blank line (\\n\\n).
    Newlines inside *data* are escaped to keep each event on a logical
    single line so the client parser stays simple.
    """
    # Encode newlines so the SSE frame stays valid
    escaped = data.replace("\n", "\\n")
    return f"data: {escaped}\n\n"


def format_sse_error(message: str) -> str:
    """Emit a special SSE error event the client can detect."""
    return f"event: error\ndata: {message}\n\n"


def format_sse_done() -> str:
    """Emit the conventional SSE stream-complete sentinel."""
    return "data: [DONE]\n\n"
