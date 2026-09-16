"""Orchestration between the HTTP layer and the analysis modules.

Deliberately free of FastAPI imports so it can be tested without starting a
server. It decides *what* to analyze and in which order; the route layer
decides how that maps onto HTTP.

Milestone M4 adds speech-to-text. Speech and vision run independently: either
can fail without taking the request down, as long as something usable remains.
"""

import logging
from typing import NamedTuple

from agent import analyze
from vision.image_analysis import ClaudeVisionAnalyzer, ImageAnalysisError
from voice.speech_to_text import SpeechmaticsTranscriber, TranscriptionError

logger = logging.getLogger(__name__)

# The frontend has no language selector, so the module default is used.
STT_LANGUAGE = "en"

# Shown to a person who may be frightened, so they say what to do next rather
# than describing a provider problem.
NO_INPUT_MESSAGE = (
    "Tell me what is happening. Type a short description of the situation."
)

AUDIO_UNAVAILABLE_MESSAGE = (
    "The recording could not be understood. Please type a short description of "
    "what is happening."
)

VISION_UNAVAILABLE_MESSAGE = (
    "The photo could not be analyzed. Please type a short description of what "
    "is happening."
)

BOTH_UNAVAILABLE_MESSAGE = (
    "The recording and the photo could not be processed. Please type a short "
    "description of what is happening."
)


class AudioUpload(NamedTuple):
    """An uploaded recording, already read by the route layer."""

    data: bytes
    filename: str
    content_type: str


class ImageUpload(NamedTuple):
    """An uploaded image, already read by the route layer."""

    data: bytes
    filename: str
    content_type: str


class EmergencyInputError(ValueError):
    """Raised when the request carried nothing to analyze at all.

    The message is always safe to show to a user.
    """


class AnalysisUnavailableError(RuntimeError):
    """Raised when real input was supplied but none of it could be processed.

    Distinct from :class:`EmergencyInputError` because the user did nothing
    wrong — the failure is ours. The message is user-safe; the underlying
    provider error is logged, never returned.
    """


def clean_transcript(transcript):
    """Trim surrounding whitespace only.

    The user's wording is never rewritten, summarized, merged, or altered —
    the agent matches on what was actually said.
    """
    return transcript.strip() if isinstance(transcript, str) else ""


def _default_transcriber():
    """Build the speech-to-text client.

    Constructed per request so a changed environment is picked up. Reading
    ``SPEECHMATICS_API_KEY`` happens inside the voice module, not here.
    """
    return SpeechmaticsTranscriber()


def _default_analyzer():
    """Build the vision client. See :func:`_default_transcriber`."""
    return ClaudeVisionAnalyzer()


def _run_stt(audio, transcriber):
    """Return the transcribed text, or ``""`` when it cannot be used.

    Never raises. A provider failure and a technically successful but empty
    transcript are both "no usable speech", so the caller can fall back to
    typed text or vision evidence.

    Exactly one transcription job is started per request that carries audio.
    """
    if audio is None:
        return ""

    client = transcriber or _default_transcriber()

    try:
        result = client.transcribe(
            audio.data,
            audio.filename,
            audio.content_type,
            language=STT_LANGUAGE,
        )

    except TranscriptionError:
        # The real cause is for developers; the user gets a safe sentence.
        logger.warning("Speech transcription failed; continuing without it",
                       exc_info=True)

        return ""

    except Exception:
        logger.exception(
            "Unexpected speech transcription failure; continuing without it"
        )

        return ""

    text = result.get("transcript") if isinstance(result, dict) else None

    return clean_transcript(text)


def _run_vision(image, analyzer):
    """Return ``(vision_result, failed)``.

    Never raises: a vision failure is a degradation signal, not an error.
    """
    if image is None:
        return None, False

    client = analyzer or _default_analyzer()

    try:
        return client.analyze(image.data, image.filename, image.content_type), False

    except ImageAnalysisError:
        logger.warning("Image analysis failed; continuing without it", exc_info=True)

        return None, True

    except Exception:
        logger.exception("Unexpected image analysis failure; continuing without it")

        return None, True


def _unavailable_message(audio_failed, image_failed):
    if audio_failed and image_failed:
        return BOTH_UNAVAILABLE_MESSAGE

    if audio_failed:
        return AUDIO_UNAVAILABLE_MESSAGE

    return VISION_UNAVAILABLE_MESSAGE


def analyze_emergency(
    transcript=None,
    image=None,
    audio=None,
    analyzer=None,
    transcriber=None,
):
    """Return the agent's assessment for the supplied inputs.

    Transcript priority is fixed: a usable speech-to-text result wins, and the
    typed description is a fallback used only when speech is unavailable. The
    two are never concatenated.

    Speech and vision are independent — either may fail while the other still
    provides usable evidence.

    Raises :class:`EmergencyInputError` when nothing was supplied, and
    :class:`AnalysisUnavailableError` when input was supplied but none of it
    could be processed. The latter matters: calling the agent with an empty
    transcript and no vision would turn an infrastructure failure into an
    "unknown" assessment, which reads to the user as a real finding.
    """
    typed_text = clean_transcript(transcript)
    spoken_text = _run_stt(audio, transcriber)
    vision, _ = _run_vision(image, analyzer)

    # Speech is primary; typed text is the fallback, never a merge.
    text = spoken_text or typed_text

    if not text and vision is None:
        audio_failed = audio is not None
        image_failed = image is not None

        if audio_failed or image_failed:
            raise AnalysisUnavailableError(
                _unavailable_message(audio_failed, image_failed)
            )

        raise EmergencyInputError(NO_INPUT_MESSAGE)

    return analyze(text, vision)
