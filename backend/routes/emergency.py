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
from vision.image_analysis import ClaudeVisionAnalyzer
from voice.speech_to_text import SpeechmaticsTranscriber

logger = logging.getLogger(__name__)

UNEXPECTED_MESSAGE = "We could not analyze this right now. Please try again."

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


@router.post(
    "/analyze",
    response_model=EmergencyAssessment,
    responses={
        400: {"model": ErrorResponse},
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
            data=await audio.read(),
            filename=audio.filename or "",
            content_type=audio.content_type or "",
        )

    if image is not None:
        image_upload = ImageUpload(
            data=await image.read(),
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
