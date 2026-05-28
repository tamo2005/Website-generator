"""
main.py — FastAPI application entry point

Endpoints:
  GET  /api/health   — health check + model info
  POST /api/generate — SSE streaming HTML generation
    POST /api/export   — ZIP export with generated HTML + preview CSS
"""
import os
import time
import logging
import zipfile
from io import BytesIO
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, Response
from pydantic import BaseModel, Field

load_dotenv()

from llm_service import MODEL_ID, stream_html_tokens
from streaming import format_sse, format_sse_error, format_sse_done

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("ai-site-gen")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_allowed_origin_value = os.getenv("ALLOWED_ORIGIN", "http://localhost:3000,http://localhost:3001")
ALLOWED_ORIGINS = [origin.strip() for origin in _allowed_origin_value.split(",") if origin.strip()]
if "http://localhost:3000" in ALLOWED_ORIGINS and "http://localhost:3001" not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append("http://localhost:3001")
if "http://localhost:3001" in ALLOWED_ORIGINS and "http://localhost:3000" not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append("http://localhost:3000")
MAX_PROMPT_CHARS: int = int(os.getenv("MAX_PROMPT_CHARS", "8000"))
PREVIEW_CSS_PATH = Path(
    os.getenv(
        "PREVIEW_CSS_PATH",
        str(Path(__file__).resolve().parents[1] / "frontend" / "public" / "preview-tailwind.css"),
    )
)

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AI Website Generator backend starting …")
    logger.info(f"   Model  : {MODEL_ID}")
    logger.info(f"   CORS   : {', '.join(ALLOWED_ORIGINS)}")
    yield
    logger.info("🛑 Backend shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Website Generator API",
    description="FastAPI + OpenRouter streaming HTML generator",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    prompt: str = Field(
        min_length=3,
        max_length=MAX_PROMPT_CHARS,
        description="Natural-language description of the website to generate.",
        examples=["Build a SaaS landing page for a note-taking app"],
    )


class HealthResponse(BaseModel):
    status: str
    model: str
    max_prompt_chars: int


class ExportRequest(BaseModel):
    html: str = Field(min_length=1, description="Generated HTML to package into a ZIP archive.")


def _build_export_html(html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <link rel=\"stylesheet\" href=\"./preview-tailwind.css\" />
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

    logger.warning("Preview CSS not found at %s; exporting a minimal fallback stylesheet.", PREVIEW_CSS_PATH)
    return "html,body{margin:0;min-height:100%;background:#020617;color:#e2e8f0;font-family:system-ui,sans-serif;}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health", response_model=HealthResponse, tags=["utility"])
async def health() -> HealthResponse:
    """Simple health check that also exposes the active model name."""
    return HealthResponse(
        status="ok",
        model=MODEL_ID,
        max_prompt_chars=MAX_PROMPT_CHARS,
    )


@app.post("/api/generate", tags=["generation"])
async def generate(payload: GenerateRequest, request: Request) -> StreamingResponse:
    """
    Stream HTML tokens as Server-Sent Events.

    Each SSE event has the form:
        data: <token>\\n\\n

    A final `data: [DONE]\\n\\n` event signals completion.
    An `event: error\\ndata: <message>\\n\\n` event signals a failure.
    """
    prompt = payload.prompt.strip()
    start = time.perf_counter()
    logger.info(f"Generate request — prompt length {len(prompt)} chars")

    async def event_stream():
        try:
            token_count = 0
            async for token in stream_html_tokens(prompt):
                # Check if the client disconnected mid-stream
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
            # Prevent buffering by proxies / nginx
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/export", tags=["generation"])
async def export(payload: ExportRequest) -> Response:
    """Package generated HTML with the preview stylesheet into a ZIP download."""
    html = _build_export_html(payload.html.strip())
    preview_css = _read_preview_css()

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("index.html", html)
        archive.writestr("preview-tailwind.css", preview_css)

    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="generated-site.zip"'},
    )


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )
