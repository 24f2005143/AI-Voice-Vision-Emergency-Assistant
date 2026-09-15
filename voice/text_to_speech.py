"""Browser-native text-to-speech payloads for the emergency dashboard.

Using the browser's SpeechSynthesis API avoids sending emergency guidance to a
second external provider.  The frontend reads ``text`` aloud when
``mode == 'browser'``.
"""

from __future__ import annotations

from typing import Iterable


def make_voice_response(emergency_type: str, severity: str, actions: Iterable[str]) -> dict[str, str]:
    """Return concise text safe for the frontend's browser speech engine."""
    priority = "This may be an emergency. " if severity in {"high", "critical"} else ""
    action_text = " ".join(str(action).strip() for action in actions if str(action).strip())
    text = f"{priority}Assessment: {emergency_type.replace('_', ' ')}. {action_text}".strip()
    return {"mode": "browser", "text": text}
