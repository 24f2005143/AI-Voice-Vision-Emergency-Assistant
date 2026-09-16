"""HTTP layer for emergency analysis.

Parses the multipart request the frontend sends, reads the uploads, delegates
to the orchestrator, and maps outcomes onto HTTP status codes. All error text
comes from the orchestrator's safe messages or the constants here — never from
an exception's own string.
"""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.models.schemas import EmergencyAssessment, ErrorResponse
from backend.services.orchestrator import (
    AnalysisUnavailableError,
    AudioUpload,
    EmergencyInputError,
    ImageUpload,
    analyze_emergency,
)
from vision.image_analysis import MAX_IMAGE_BYTES, ClaudeVisionAnalyzer
from voice.speech_to_text import MAX_AUDIO_BYTES, SpeechmaticsTranscriber

logger = logging.getLogger(__name__)

UNEXPECTED_MESSAGE = "We could not analyze this right now. Please try again."

# Limits are imported from the voice and vision modules rather than repeated,
# so there is a single source of truth: audio 25 MB, image 10 MB.
AUDIO_TOO_LARGE_MESSAGE = (
    "That recording is too large. Please use a recording under 25 MB, or type "
    "a short description instead."
)

IMAGE_TOO_LARGE_MESSAGE = (
    "That photo is too large. Please use a photo under 10 MB, or type a short "
    "description instead."
)

# Read in chunks so an oversized upload is rejected as soon as it passes the
# limit, instead of being held in memory in full and then handed to a provider.
UPLOAD_CHUNK_BYTES = 256 * 1024

router = APIRouter(prefix="/api/emergency", tags=["emergency"])


def get_vision_analyzer():
    """Provide the vision client.

    Exposed as a dependency so tests can override it with a stub and never
    touch the network.
    """
    return ClaudeVisionAnalyzer()


def get_speech_transcriber():
    """Provide the speech-to-text client. See :func:`get_vision_analyzer`."""
    return SpeechmaticsTranscriber()


async def read_capped(upload, limit, message):
    """Read an upload, refusing anything past ``limit``.

    Stops at the first chunk that crosses the limit, so an oversized file is
    never fully buffered and never reaches a provider. Raises a 413 whose
    detail is a plain sentence: no path, provider text, or byte counts beyond
    the published limit.
    """
    chunks = []
    total = 0

    while True:
        chunk = await upload.read(UPLOAD_CHUNK_BYTES)

        if not chunk:
            break

        total += len(chunk)

        if total > limit:
            logger.info("Rejected an upload above the %d byte limit", limit)

            raise HTTPException(status_code=413, detail=message)

        chunks.append(chunk)

    return b"".join(chunks)


@router.post(
    "/analyze",
    response_model=EmergencyAssessment,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def analyze_endpoint(
    # All three are optional: the frontend omits fields the user did not give.
    audio: UploadFile | None = File(default=None),
    image: UploadFile | None = File(default=None),
    transcript: str | None = Form(default=None),
    analyzer=Depends(get_vision_analyzer),
    transcriber=Depends(get_speech_transcriber),
):
    """Analyze a spoken, described and/or photographed situation."""
    audio_upload = None
    image_upload = None

    # The voice and vision modules validate type, size and filename
    # themselves, so the bytes are handed over exactly as received rather
    # than re-checked here.
    if audio is not None:
        audio_upload = AudioUpload(
            data=await read_capped(audio, MAX_AUDIO_BYTES, AUDIO_TOO_LARGE_MESSAGE),
            filename=audio.filename or "",
            content_type=audio.content_type or "",
        )

    if image is not None:
        image_upload = ImageUpload(
            data=await read_capped(image, MAX_IMAGE_BYTES, IMAGE_TOO_LARGE_MESSAGE),
            filename=image.filename or "",
            content_type=image.content_type or "",
        )

    try:
        assessment = analyze_emergency(
            transcript=transcript,
            image=image_upload,
            audio=audio_upload,
            analyzer=analyzer,
            transcriber=transcriber,
        )

    except EmergencyInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except AnalysisUnavailableError as exc:
        # Valid input, our failure: nothing supplied could be processed.
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    except Exception:
        logger.exception("Unexpected failure while analyzing an emergency")

        raise HTTPException(status_code=500, detail=UNEXPECTED_MESSAGE) from None

    return assessment
