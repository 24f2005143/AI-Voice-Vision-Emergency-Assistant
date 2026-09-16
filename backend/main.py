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

logger = logging.getLogger(__name__)

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
