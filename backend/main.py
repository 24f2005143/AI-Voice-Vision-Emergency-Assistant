"""FastAPI application for the AI Voice + Vision Emergency Assistant.

Milestone M2: the frontend can complete a full round trip using a typed
description and the deterministic agent. Voice transcription (Speechmatics)
and image analysis are not wired up yet and are not faked.

Run locally from the repository root:

    uvicorn backend.main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.routes.emergency import router as emergency_router
from vision.image_analysis import MAX_IMAGE_BYTES
from voice.speech_to_text import MAX_AUDIO_BYTES

logger = logging.getLogger(__name__)

# A request may legitimately carry one recording, one photo and a short
# description, plus multipart overhead. Anything beyond that is refused before
# the body is parsed, so an oversized upload costs almost nothing.
MAX_REQUEST_BYTES = MAX_AUDIO_BYTES + MAX_IMAGE_BYTES + (1024 * 1024)

REQUEST_TOO_LARGE_MESSAGE = (
    "That upload is too large. Please use a recording under 25 MB and a photo "
    "under 10 MB, or type a short description instead."
)

# The Vite dev server is reached under both hostnames depending on how the
# developer opens it, and browsers treat them as separate origins. A wildcard
# is deliberately not used.
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

BAD_REQUEST_MESSAGE = (
    "That request could not be read. Please try again."
)

UNEXPECTED_MESSAGE = (
    "We could not analyze this right now. Please try again."
)

app = FastAPI(
    title="AI Voice + Vision Emergency Assistant",
    version="0.2.0",
)

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Refuse an oversized body before Starlette parses the multipart form.

    Content-Length is advisory, so the per-file caps in the route remain the
    authoritative check. This only avoids the parsing cost in the obvious case.
    """
    declared = request.headers.get("content-length")

    if declared and declared.isdigit() and int(declared) > MAX_REQUEST_BYTES:
        logger.info("Rejected a request declaring %s bytes", declared)

        return JSONResponse(
            status_code=413, content={"detail": REQUEST_TOO_LARGE_MESSAGE}
        )

    return await call_next(request)


# Registered last so it sits outermost: every response, including the 413
# above, then carries the right CORS headers for the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(emergency_router)


# frontend/src/services/api.js calls response.json() on every response and
# reads `detail`, so each handler below guarantees JSON with a single
# human-readable sentence. Starlette's defaults would return plain text for a
# 500 and a list for a validation error, and both would break the frontend.

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else BAD_REQUEST_MESSAGE

    return JSONResponse(status_code=exc.status_code, content={"detail": detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # The default body is a list of field errors that exposes internal
    # locations; collapse it to one safe sentence.
    logger.info("Rejected a malformed request to %s", request.url.path)

    return JSONResponse(status_code=400, content={"detail": BAD_REQUEST_MESSAGE})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error while serving %s", request.url.path)

    return JSONResponse(status_code=500, content={"detail": UNEXPECTED_MESSAGE})


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check used to confirm the frontend can reach the backend."""
    return {"status": "ok"}
