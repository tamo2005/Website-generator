"""
api/generation/router.py — Website generation and export endpoints

Moved from main.py. Auth-guarded with consistent API envelope.
All paths prefixed with /api/v1.
"""

import logging
import os
import time
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.dependencies import get_current_verified_user
from core.responses import api_response
from db.session import get_db
from models.user import User
from services.llm_service import MODEL_ID, stream_html_tokens
from utils.streaming import format_sse, format_sse_done, format_sse_error

logger = logging.getLogger("ai-site-gen")
settings = get_settings()

router = APIRouter(prefix="/api/v1", tags=["generation"])


# ── Request / Response schemas ───────────────────────────────


class GenerateRequest(BaseModel):
    prompt: str = Field(
        min_length=3,
        max_length=settings.MAX_PROMPT_CHARS,
        description="Natural-language description of the website to generate.",
        examples=["Build a SaaS landing page for a note-taking app"],
    )


class ExportRequest(BaseModel):
    html: str = Field(
        min_length=1,
        description="Generated HTML to package into a ZIP archive.",
    )


# ── Helpers ──────────────────────────────────────────────────

PREVIEW_CSS_PATH = Path(
    os.getenv(
        "PREVIEW_CSS_PATH",
        str(
            Path(__file__).resolve().parents[2]
            / "frontend"
            / "public"
            / "preview-tailwind.css"
        ),
    )
)


def _build_export_html(html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="./preview-tailwind.css" />
  <style>
    html, body {{ margin: 0; min-height: 100%; background: #020617; }}
    body {{ color: #e2e8f0; }}
  </style>
</head>
<body>
{html}
</body>
</html>"""


def _read_preview_css() -> str:
    if PREVIEW_CSS_PATH.exists():
        return PREVIEW_CSS_PATH.read_text(encoding="utf-8")
    logger.warning("Preview CSS not found at %s; using fallback.", PREVIEW_CSS_PATH)
    return "html,body{margin:0;min-height:100%;background:#020617;color:#e2e8f0;font-family:system-ui,sans-serif;}"


# ── Endpoints ────────────────────────────────────────────────


@router.get("/health")
async def health(request: Request):
    """Health check — also exposes active model name."""
    return api_response(
        data={
            "status": "ok",
            "model": get_settings().OPENROUTER_MODEL,
            "max_prompt_chars": settings.MAX_PROMPT_CHARS,
        },
        request=request,
    )


@router.post("/generate")
async def generate(
    payload: GenerateRequest,
    request: Request,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream HTML tokens as Server-Sent Events. Requires auth + verified email."""
    prompt = payload.prompt.strip()
    start = time.perf_counter()
    logger.info(f"Generate request — user={user.id} prompt_len={len(prompt)}")

    async def event_stream():
        try:
            token_count = 0
            async for token in stream_html_tokens(prompt):
                if await request.is_disconnected():
                    logger.info("Client disconnected — aborting stream")
                    return
                token_count += 1
                yield format_sse(token)

            elapsed = time.perf_counter() - start
            logger.info(
                f"Stream complete — {token_count} tokens in {elapsed:.2f}s "
                f"({token_count / elapsed:.1f} tok/s)"
            )
            yield format_sse_done()
        except Exception as exc:
            logger.error(f"Generation error: {exc}", exc_info=True)
            yield format_sse_error(str(exc))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/export")
async def export(
    payload: ExportRequest,
    request: Request,
    user: User = Depends(get_current_verified_user),
) -> Response:
    """Package generated HTML with the preview stylesheet into a ZIP download."""
    html = _build_export_html(payload.html.strip())
    preview_css = _read_preview_css()

    zip_buffer = BytesIO()
    with zipfile.ZipFile(
        zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr("index.html", html)
        archive.writestr("preview-tailwind.css", preview_css)

    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="generated-site.zip"',
        },
    )
