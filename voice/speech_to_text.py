
"""Speechmatics batch-transcription adapter for the emergency assistant.

This module deliberately contains no web-framework code.  The backend can pass
the uploaded audio bytes to :class:`SpeechmaticsTranscriber` and receive the
shared ``{"transcript": "..."}`` contract from the README.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Mapping

import requests


SPEECHMATICS_BATCH_URL = "https://asr.api.speechmatics.com/v2"
ALLOWED_CONTENT_TYPES = {
    "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/mp4",
    "audio/webm", "video/webm", "audio/ogg", "application/ogg",
}
MAX_AUDIO_BYTES = 25 * 1024 * 1024


class TranscriptionError(RuntimeError):
    """A safe, user-facing error raised when transcription cannot complete."""


@dataclass(frozen=True)
class Transcript:
    text: str
    language: str

    def as_dict(self) -> dict[str, str]:
        return {"transcript": self.text}


class SpeechmaticsTranscriber:
    """Small client for the Speechmatics batch API.

    ``session`` is injectable so unit tests never need a network connection.
    The production API key is read only from ``SPEECHMATICS_API_KEY``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = SPEECHMATICS_BATCH_URL,
        timeout_seconds: int = 30,
        poll_interval_seconds: float = 1.0,
        max_wait_seconds: int = 90,
        session: requests.Session | Any | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("SPEECHMATICS_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.max_wait_seconds = max_wait_seconds
        self.session = session or requests.Session()

    def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
        *,
        language: str = "en",
    ) -> dict[str, str]:
        """Upload audio, wait for completion, and return the common payload."""
        self._validate_audio(audio, filename, content_type)
        if not self.api_key:
            raise TranscriptionError("Speech transcription is not configured.")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        config = {"type": "transcription", "transcription_config": {"language": language}}
        try:
            submitted = self.session.post(
                f"{self.base_url}/jobs",
                headers=headers,
                data={"config": _json(config)},
                files={"data_file": (filename, audio, content_type)},
                timeout=self.timeout_seconds,
            )
            self._raise_for_status(submitted, "Audio could not be submitted for transcription")
            job_id = submitted.json().get("id")
            if not job_id:
                raise TranscriptionError("Speech service returned no transcription job ID.")
            self._wait_for_job(str(job_id), headers)
            transcript_response = self.session.get(
                f"{self.base_url}/jobs/{job_id}/transcript",
                headers=headers,
                params={"format": "json-v2"},
                timeout=self.timeout_seconds,
            )
            self._raise_for_status(transcript_response, "Transcript could not be retrieved")
        except requests.RequestException as exc:
            raise TranscriptionError("Speech service is unavailable. Please try again.") from exc

        text = _extract_transcript(transcript_response.json())
        if not text:
            raise TranscriptionError("No speech was detected in the uploaded audio.")
        return Transcript(text=text, language=language).as_dict()

    def _wait_for_job(self, job_id: str, headers: Mapping[str, str]) -> None:
        deadline = time.monotonic() + self.max_wait_seconds
        while time.monotonic() < deadline:
            response = self.session.get(
                f"{self.base_url}/jobs/{job_id}", headers=headers, timeout=self.timeout_seconds
            )
            self._raise_for_status(response, "Transcription status could not be checked")
            status = str(response.json().get("job", {}).get("status", "")).lower()
            if status == "done":
                return
            if status in {"rejected", "failed", "expired"}:
                raise TranscriptionError("Speech transcription could not be completed.")
            time.sleep(self.poll_interval_seconds)
        raise TranscriptionError("Speech transcription timed out. Please try a shorter recording.")

    @staticmethod
    def _validate_audio(audio: bytes, filename: str, content_type: str) -> None:
        if not audio:
            raise TranscriptionError("Please record or upload an audio file first.")
        if len(audio) > MAX_AUDIO_BYTES:
            raise TranscriptionError("Audio is too large. Please use a file under 25 MB.")
        if not filename:
            raise TranscriptionError("The audio file needs a filename.")
        if content_type.lower().split(";", 1)[0] not in ALLOWED_CONTENT_TYPES:
            raise TranscriptionError("Unsupported audio format. Use WAV, MP3, WebM, M4A, or OGG.")

    @staticmethod
    def _raise_for_status(response: Any, message: str) -> None:
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TranscriptionError(f"{message}.") from exc


def _extract_transcript(payload: Mapping[str, Any]) -> str:
    """Extract text from Speechmatics' json-v2 word results without timestamps."""
    words: list[str] = []
    for item in payload.get("results", []):
        if item.get("type") != "word":
            continue
        alternatives = item.get("alternatives") or []
        if alternatives and alternatives[0].get("content"):
            words.append(str(alternatives[0]["content"]))
    return " ".join(words).strip()


def _json(value: Mapping[str, Any]) -> str:
    import json
    return json.dumps(value)
