"""Vision hazard-detection adapter for the emergency assistant.

Per the README's development rule for this module: do not train a model from
scratch, prototype first with an appropriate existing model/API. This module
sends the uploaded image to a multimodal vision API (Claude) and returns the
shared contract from README section 5.2:

    {"hazard": "smoke", "objects": ["stove", "person"], "confidence": 0.89}

This module deliberately contains no web-framework code, matching the style
of voice/speech_to_text.py. The backend should pass the uploaded image bytes,
original filename, and MIME type to
``ClaudeVisionAnalyzer().analyze(...)`` and forward the returned dict to
``agent.emergency_agent.analyze(transcript, vision=...)`` untouched.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

import requests

from vision.hazard_detection import build_result

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# Default model for image hazard detection. Override with the VISION_MODEL
# env var if a different/newer model should be used instead.
DEFAULT_MODEL = "claude-sonnet-5"

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
}
MAX_IMAGE_BYTES = 10 * 1024 * 1024

HAZARD_PROMPT = (
    "You are the vision component of an emergency-response assistant. "
    "Look at this image and report only what is visible.\n\n"
    "Reply with ONLY a JSON object, no other text, in exactly this shape:\n"
    '{"hazard": "<short hazard label, or \\"none\\" if nothing is wrong>", '
    '"objects": ["<visible object>", ...], '
    '"confidence": <number between 0 and 1>}\n\n'
    "The hazard label should be one short phrase such as: fire, smoke, "
    "flame, burning, blood, bleeding, injury, unresponsive, fallen, "
    "person on floor, collapse, crash, collision, damaged vehicle, "
    "intruder, weapon, masked. If the image shows nothing concerning, use "
    '"none". Do not guess at emergencies the image does not actually show.'
)


class ImageAnalysisError(RuntimeError):
    """A safe, user-facing error raised when image analysis cannot complete."""


@dataclass(frozen=True)
class VisionResult:
    hazard: str
    objects: list[str]
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {"hazard": self.hazard, "objects": self.objects,
                "confidence": self.confidence}


class ClaudeVisionAnalyzer:
    """Small client that sends an image to Claude's vision API for hazard detection.

    ``session`` is injectable so unit tests never need a network connection.
    The production API key is read only from ``VISION_API_KEY``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str | None = None,
        base_url: str = ANTHROPIC_MESSAGES_URL,
        timeout_seconds: int = 30,
        session: requests.Session | Any | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("VISION_API_KEY")
        self.model = model or os.getenv("VISION_MODEL", DEFAULT_MODEL)
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def analyze(self, image: bytes, filename: str, content_type: str) -> dict:
        """Send an image for hazard analysis and return the common payload."""
        media_type = self._validate_image(image, filename, content_type)
        if not self.api_key:
            raise ImageAnalysisError("Image analysis is not configured.")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": 300,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64.b64encode(image).decode("ascii"),
                        },
                    },
                    {"type": "text", "text": HAZARD_PROMPT},
                ],
            }],
        }
        try:
            response = self.session.post(
                self.base_url, headers=headers, json=body,
                timeout=self.timeout_seconds,
            )
            self._raise_for_status(response)
        except requests.RequestException as exc:
            raise ImageAnalysisError(
                "Vision service is unavailable. Please try again.") from exc

        parsed = _parse_model_reply(response.json())
        result = build_result(
            parsed.get("hazard"), parsed.get("objects"),
            parsed.get("confidence"),
        )
        return VisionResult(**result).as_dict()

    @staticmethod
    def _validate_image(image: bytes, filename: str, content_type: str) -> str:
        if not image:
            raise ImageAnalysisError("Please upload an image first.")
        if len(image) > MAX_IMAGE_BYTES:
            raise ImageAnalysisError("Image is too large. Please use a file under 10 MB.")
        if not filename:
            raise ImageAnalysisError("The image file needs a filename.")
        media_type = ALLOWED_CONTENT_TYPES.get(content_type.lower().split(";", 1)[0])
        if not media_type:
            raise ImageAnalysisError("Unsupported image format. Use JPEG, PNG, or WebP.")
        return media_type

    @staticmethod
    def _raise_for_status(response: Any) -> None:
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ImageAnalysisError("Image could not be analyzed.") from exc


def _parse_model_reply(payload: dict) -> dict:
    """Extract the JSON hazard object from a Claude messages API response."""
    blocks = payload.get("content") or []
    text = "".join(
        block.get("text", "") for block in blocks if block.get("type") == "text"
    ).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    if not text:
        raise ImageAnalysisError("Vision service returned no result.")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ImageAnalysisError("Vision service returned an unreadable result.") from exc
    if not isinstance(parsed, dict):
        raise ImageAnalysisError("Vision service returned an unreadable result.")
    return parsed
