"""
main.py — FastAPI application entry point

Endpoints:
  GET  /api/health   — health check + model info
  POST /api/generate — SSE streaming HTML generation
"""
import os
import time
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
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
ALLOWED_ORIGIN: str = os.getenv("ALLOWED_ORIGIN", "http://localhost:3000")
MAX_PROMPT_CHARS: int = int(os.getenv("MAX_PROMPT_CHARS", "8000"))

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AI Website Generator backend starting …")
    logger.info(f"   Model  : {MODEL_ID}")
    logger.info(f"   CORS   : {ALLOWED_ORIGIN}")
    yield
    logger.info("🛑 Backend shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Website Generator API",
    description="FastAPI + LangChain + HuggingFace streaming HTML generator",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
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
