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
from schemas.generation import (
    AnimationPreset,
    ContentTone,
    GenerationRequest,
    ImageCounts,
    StylePreset,
    ThemeMode,
    WebsiteType,
)
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
    # Phase 6: Optional configuration from the frontend wizard
    website_type: Optional[str] = Field(default=None, description="Website type override")
    theme: Optional[str] = Field(default=None, description="Theme mode: dark/light/auto")
    style: Optional[str] = Field(default=None, description="Style preset: modern/minimal/glassmorphism/etc.")
    color: Optional[str] = Field(default=None, description="Color hint: blue/purple/green/etc.")
    animations: Optional[str] = Field(default=None, description="Animation preset: none/minimal/smooth/fancy")
    content_tone: Optional[str] = Field(default=None, description="Content tone: professional/marketing/casual/etc.")
    sections: Optional[list[str]] = Field(default=None, description="Explicit section selection")
    brand_name: Optional[str] = Field(default=None, description="Brand name override")
    image_counts: Optional[dict] = Field(default=None, description="Image counts per section type")


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
    """Stream HTML tokens as Server-Sent Events using GenerationPipelineV1 (Modules 1-9 + Evaluation Engine)."""
    prompt = payload.prompt.strip()
    start = time.perf_counter()
    logger.info(f"Generate request — user={user.id} prompt_len={len(prompt)}")

    async def event_stream():
        try:
            from ai.pipeline.runner import GenerationPipelineV1
            from ai.providers.openrouter import OpenRouterProvider
            from ai.providers.base import GenerationConfig

            provider = OpenRouterProvider()
            config = GenerationConfig(model=settings.OPENROUTER_MODEL)
            pipeline = GenerationPipelineV1(provider=provider, config=config)

            logger.info(f"Executing GenerationPipelineV1 for prompt: {prompt[:50]}...")

            # Phase 6: Build GenerationRequest from payload config
            gen_request = None
            if any([
                payload.website_type, payload.theme, payload.style,
                payload.color, payload.animations, payload.sections,
                payload.content_tone, payload.brand_name, payload.image_counts,
            ]):
                gen_request = GenerationRequest(
                    prompt=prompt,
                    website_type=WebsiteType(payload.website_type) if payload.website_type else None,
                    theme=ThemeMode(payload.theme) if payload.theme else None,
                    style=StylePreset(payload.style) if payload.style else None,
                    color=payload.color,
                    animations=AnimationPreset(payload.animations) if payload.animations else None,
                    content_tone=ContentTone(payload.content_tone) if payload.content_tone else None,
                    sections=payload.sections,
                    brand_name=payload.brand_name,
                    image_counts=ImageCounts(**payload.image_counts) if payload.image_counts else None,
                )
                logger.info(f"Phase 6 config: style={payload.style} theme={payload.theme} sections={payload.sections}")

            result = await pipeline.run(prompt, request=gen_request)

            if not result.success or not result.html:
                logger.warning("Pipeline V1 returned empty HTML or failed; falling back to legacy streaming")
                token_count = 0
                async for token in stream_html_tokens(prompt):
                    if await request.is_disconnected():
                        return
                    token_count += 1
                    yield format_sse(token)
            else:
                logger.info(
                    f"Pipeline V1 succeeded in {result.elapsed_seconds:.2f}s — "
                    f"Score: {result.evaluation.overall_score if result.evaluation else 'N/A'} "
                    f"({result.evaluation.grade if result.evaluation else 'N/A'}) — "
                    f"{result.component_count} components"
                )
                html = result.html
                chunk_size = 64
                for i in range(0, len(html), chunk_size):
                    if await request.is_disconnected():
                        return
                    chunk = html[i : i + chunk_size]
                    yield format_sse(chunk)

            elapsed = time.perf_counter() - start
            logger.info(f"Stream complete in {elapsed:.2f}s")
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
