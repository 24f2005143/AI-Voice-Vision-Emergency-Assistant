"""Backend integration tests for POST /api/emergency/analyze.

These run entirely offline. The agent needs no API keys; the vision and speech
clients are replaced with stubs via FastAPI's dependency overrides, or driven
through the real modules with a fake HTTP session. Any test here that started
making a network call would be a bug in the backend.
"""

import io
import json
import logging
import unittest

from fastapi.testclient import TestClient

from backend.main import app
from backend.routes.emergency import get_speech_transcriber, get_vision_analyzer
from backend.services.orchestrator import (
    AnalysisUnavailableError,
    AudioUpload,
    EmergencyInputError,
    ImageUpload,
    analyze_emergency,
    clean_transcript,
)
from vision.image_analysis import ClaudeVisionAnalyzer, ImageAnalysisError
from voice.speech_to_text import SpeechmaticsTranscriber, TranscriptionError

ENDPOINT = "/api/emergency/analyze"
EXPECTED_KEYS = {"emergency_type", "severity", "confidence", "reason", "actions"}

SMOKE_VISION = {"hazard": "smoke", "objects": ["stove", "person"], "confidence": 0.89}

IMAGE_BYTES = b"\xff\xd8\xff\xe0 pretend jpeg bytes"
AUDIO_BYTES = b"\x1aE\xdf\xa3 pretend webm bytes"

# Two transcripts that classify differently, so tests can prove which one the
# agent actually received.
SPOKEN_FIRE = "There is smoke in my kitchen."
TYPED_CALM = "I am making tea and listening to music."
TYPED_FALL = "My grandmother fell in the bathroom."

# Strings that would indicate an internal detail escaped into a response.
LEAK_MARKERS = (
    "traceback",
    "file \"",
    "line ",
    ".py",
    "exception",
    "errno",
    "api_key",
    "api key",
    "speechmatics",
    "anthropic",
    "claude",
    "/users/",
    "backend.",
    "agent.",
    "vision.",
    "voice.",
    "valueerror",
    "runtimeerror",
    "secret",
)


class StubTranscriber:
    """Records what it was given and returns a canned transcript."""

    def __init__(self, transcript=SPOKEN_FIRE, error=None, result=None):
        self.transcript = transcript
        self.error = error
        self.result = result
        self.calls = []

    def transcribe(self, audio, filename, content_type, *, language="en"):
        self.calls.append(
            {
                "audio": audio,
                "filename": filename,
                "content_type": content_type,
                "language": language,
            }
        )

        if self.error is not None:
            raise self.error

        if self.result is not None:
            return self.result

        return {"transcript": self.transcript}


class ExplodingTranscriber:
    """Fails the way an unexpected provider bug would."""

    def __init__(self):
        self.calls = []

    def transcribe(self, audio, filename, content_type, *, language="en"):
        self.calls.append(filename)

        raise ValueError("boom: /Users/someone/secret_path.py api_key=sk-12345")


class StubAnalyzer:
    """Records what it was given and returns a canned vision result."""

    def __init__(self, result=None, error=None):
        self.result = result if result is not None else dict(SMOKE_VISION)
        self.error = error
        self.calls = []

    def analyze(self, image, filename, content_type):
        self.calls.append((image, filename, content_type))

        if self.error is not None:
            raise self.error

        return dict(self.result)


class ExplodingAnalyzer:
    def __init__(self):
        self.calls = []

    def analyze(self, image, filename, content_type):
        self.calls.append(filename)

        raise ValueError("boom: /Users/someone/secret_path.py api_key=sk-12345")


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeSession:
    """Stands in for requests.Session inside the real vision analyzer."""

    def __init__(self, hazard_json):
        self.payload = {"content": [{"type": "text", "text": hazard_json}]}
        self.posts = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.posts.append({"url": url, "headers": headers, "json": json})

        return FakeResponse(self.payload)


def setUpModule():
    # Several tests deliberately make speech or vision fail, and the backend
    # logs the real cause on purpose. Silence that expected noise so genuine
    # failures stand out; two tests below re-enable it to prove logging works.
    logging.getLogger("backend").setLevel(logging.CRITICAL)


def tearDownModule():
    logging.getLogger("backend").setLevel(logging.NOTSET)


def image_upload(data=IMAGE_BYTES, filename="kitchen.jpg", content_type="image/jpeg"):
    return {"image": (filename, io.BytesIO(data), content_type)}


def audio_upload(data=AUDIO_BYTES, filename="recording.webm", content_type="audio/webm"):
    return {"audio": (filename, io.BytesIO(data), content_type)}


class BackendTestCase(unittest.TestCase):
    """Installs stub speech and vision clients for every request."""

    def setUp(self):
        self.analyzer = StubAnalyzer()
        self.transcriber = StubTranscriber()

        app.dependency_overrides[get_vision_analyzer] = lambda: self.analyzer
        app.dependency_overrides[get_speech_transcriber] = lambda: self.transcriber

        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def use_vision(self, analyzer):
        self.analyzer = analyzer
        app.dependency_overrides[get_vision_analyzer] = lambda: analyzer

    def use_speech(self, transcriber):
        self.transcriber = transcriber
        app.dependency_overrides[get_speech_transcriber] = lambda: transcriber


# ---------------------------------------------------------------------------
# M2 / M3 behaviour that must not regress
# ---------------------------------------------------------------------------

class HealthTests(BackendTestCase):
    def test_health_still_returns_ok(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class TranscriptOnlyTests(BackendTestCase):
    def test_typed_transcript_returns_200(self):
        response = self.client.post(ENDPOINT, data={"transcript": SPOKEN_FIRE})

        self.assertEqual(response.status_code, 200)

    def test_fire_transcript_is_classified(self):
        body = self.client.post(ENDPOINT, data={"transcript": SPOKEN_FIRE}).json()

        self.assertEqual(body["emergency_type"], "possible_fire")
        self.assertEqual(body["severity"], "high")

    def test_medical_transcript_is_critical(self):
        body = self.client.post(
            ENDPOINT, data={"transcript": "He is unconscious and not breathing."}
        ).json()

        self.assertEqual(body["emergency_type"], "medical_emergency")
        self.assertEqual(body["severity"], "critical")

    def test_non_emergency_transcript_is_returned_calmly(self):
        body = self.client.post(ENDPOINT, data={"transcript": TYPED_CALM}).json()

        self.assertEqual(body["emergency_type"], "none")
        self.assertEqual(body["actions"], [])

    def test_response_has_exactly_the_five_contract_keys(self):
        body = self.client.post(ENDPOINT, data={"transcript": SPOKEN_FIRE}).json()

        self.assertEqual(set(body), EXPECTED_KEYS)

    def test_response_field_types_match_the_contract(self):
        body = self.client.post(ENDPOINT, data={"transcript": "There is a fire."}).json()

        self.assertIsInstance(body["emergency_type"], str)
        self.assertIsInstance(body["severity"], str)
        self.assertIsInstance(body["confidence"], float)
        self.assertIsInstance(body["reason"], str)
        self.assertIsInstance(body["actions"], list)
        self.assertTrue(all(isinstance(item, str) for item in body["actions"]))
        self.assertGreaterEqual(body["confidence"], 0.0)
        self.assertLessEqual(body["confidence"], 1.0)

    def test_transcript_wording_is_not_rewritten(self):
        body = self.client.post(
            ENDPOINT, data={"transcript": "   There is a fire.   "}
        ).json()

        self.assertEqual(body["emergency_type"], "possible_fire")

    def test_no_uploads_means_neither_client_is_called(self):
        self.client.post(ENDPOINT, data={"transcript": "There is a fire."})

        self.assertEqual(self.analyzer.calls, [])
        self.assertEqual(self.transcriber.calls, [])


class VisionIntegrationTests(BackendTestCase):
    def test_image_with_transcript_calls_vision_once(self):
        self.client.post(
            ENDPOINT, data={"transcript": SPOKEN_FIRE}, files=image_upload()
        )

        self.assertEqual(len(self.analyzer.calls), 1)

    def test_vision_result_reaches_the_agent(self):
        body = self.client.post(
            ENDPOINT, data={"transcript": SPOKEN_FIRE}, files=image_upload()
        ).json()

        self.assertEqual(body["emergency_type"], "possible_fire")
        self.assertGreater(body["confidence"], 0.7)
        self.assertIn("image analysis", body["reason"])

    def test_image_only_is_analyzed_and_reaches_the_agent(self):
        response = self.client.post(ENDPOINT, files=image_upload())
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.analyzer.calls), 1)
        self.assertEqual(body["emergency_type"], "possible_fire")
        self.assertIn("no supporting description", body["reason"])

    def test_image_bytes_filename_and_type_pass_through_unchanged(self):
        self.client.post(
            ENDPOINT,
            data={"transcript": "There is a fire."},
            files=image_upload(filename="stove.png", content_type="image/png"),
        )

        sent_bytes, filename, content_type = self.analyzer.calls[0]

        self.assertEqual(sent_bytes, IMAGE_BYTES)
        self.assertEqual(filename, "stove.png")
        self.assertEqual(content_type, "image/png")

    def test_vision_failure_with_transcript_degrades_to_200(self):
        self.use_vision(StubAnalyzer(error=ImageAnalysisError("unavailable")))

        response = self.client.post(
            ENDPOINT, data={"transcript": "There is a fire."}, files=image_upload()
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("no supporting vision result", response.json()["reason"])

    def test_vision_failure_without_transcript_returns_502(self):
        self.use_vision(StubAnalyzer(error=ImageAnalysisError("unavailable")))

        response = self.client.post(ENDPOINT, files=image_upload())

        self.assertEqual(response.status_code, 502)
        self.assertEqual(set(response.json()), {"detail"})


class RealModuleTests(BackendTestCase):
    """Exercises the actual vision module offline via its injectable session."""

    def test_real_analyzer_normalizes_and_reaches_the_agent(self):
        session = FakeSession(
            json.dumps({"hazard": "Smoke detected", "objects": ["Stove", "person"],
                        "confidence": 0.89})
        )

        self.use_vision(ClaudeVisionAnalyzer(api_key="test-key", session=session))

        body = self.client.post(
            ENDPOINT, data={"transcript": SPOKEN_FIRE}, files=image_upload()
        ).json()

        self.assertEqual(len(session.posts), 1)
        self.assertEqual(body["emergency_type"], "possible_fire")
        self.assertGreater(body["confidence"], 0.7)

    def test_real_transcriber_without_key_degrades_before_network(self):
        # The voice module raises before any HTTP call when no key is set.
        self.use_speech(SpeechmaticsTranscriber(api_key=None))

        response = self.client.post(
            ENDPOINT, data={"transcript": TYPED_FALL}, files=audio_upload()
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["emergency_type"], "fall")

    def test_real_transcriber_rejects_bad_audio_type_before_network(self):
        self.use_speech(SpeechmaticsTranscriber(api_key="test-key"))

        response = self.client.post(
            ENDPOINT,
            data={"transcript": TYPED_FALL},
            files=audio_upload(filename="notes.txt", content_type="text/plain"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["emergency_type"], "fall")


# ---------------------------------------------------------------------------
# M4: speech-to-text
# ---------------------------------------------------------------------------

class SpeechIntegrationTests(BackendTestCase):
    def test_audio_only_with_successful_stt_returns_200(self):
        response = self.client.post(ENDPOINT, files=audio_upload())
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["emergency_type"], "possible_fire")

    def test_exactly_one_stt_call_per_request(self):
        self.client.post(ENDPOINT, files=audio_upload())

        self.assertEqual(len(self.transcriber.calls), 1)

    def test_no_audio_means_stt_is_never_called(self):
        self.client.post(ENDPOINT, data={"transcript": SPOKEN_FIRE}, files=image_upload())

        self.assertEqual(self.transcriber.calls, [])

    def test_audio_bytes_filename_and_type_pass_through_unchanged(self):
        self.client.post(
            ENDPOINT,
            files=audio_upload(filename="clip.ogg", content_type="audio/ogg"),
        )

        call = self.transcriber.calls[0]

        self.assertEqual(call["audio"], AUDIO_BYTES)
        self.assertEqual(call["filename"], "clip.ogg")
        self.assertEqual(call["content_type"], "audio/ogg")

    def test_language_english_is_passed(self):
        self.client.post(ENDPOINT, files=audio_upload())

        self.assertEqual(self.transcriber.calls[0]["language"], "en")

    def test_stt_transcript_is_not_rewritten(self):
        self.use_speech(StubTranscriber(transcript="   There is a fire.   "))

        body = self.client.post(ENDPOINT, files=audio_upload()).json()

        self.assertEqual(body["emergency_type"], "possible_fire")

    def test_audio_and_image_both_reach_the_agent(self):
        body = self.client.post(
            ENDPOINT, files={**audio_upload(), **image_upload()}
        ).json()

        self.assertEqual(len(self.transcriber.calls), 1)
        self.assertEqual(len(self.analyzer.calls), 1)
        # Voice and vision agreeing lifts confidence past the single-source cap.
        self.assertEqual(body["emergency_type"], "possible_fire")
        self.assertGreater(body["confidence"], 0.7)
        self.assertIn("image analysis", body["reason"])


class TranscriptPriorityTests(BackendTestCase):
    """Speech wins; typed text is a fallback and is never merged in."""

    def test_stt_transcript_wins_over_typed_transcript(self):
        # Spoken text is a fire; typed text is calm. The result proves which won.
        body = self.client.post(
            ENDPOINT, data={"transcript": TYPED_CALM}, files=audio_upload()
        ).json()

        self.assertEqual(body["emergency_type"], "possible_fire")

    def test_typed_transcript_does_not_reach_the_agent_when_stt_succeeds(self):
        body = self.client.post(
            ENDPOINT, data={"transcript": TYPED_FALL}, files=audio_upload()
        ).json()

        # A merge would have matched "fell" as well; it must not appear.
        self.assertEqual(body["emergency_type"], "possible_fire")
        self.assertNotIn("fell", body["reason"])

    def test_typed_transcript_is_used_when_stt_fails(self):
        self.use_speech(StubTranscriber(error=TranscriptionError("unavailable")))

        response = self.client.post(
            ENDPOINT, data={"transcript": TYPED_FALL}, files=audio_upload()
        )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["emergency_type"], "fall")

    def test_empty_stt_transcript_falls_back_to_typed(self):
        self.use_speech(StubTranscriber(transcript=""))

        body = self.client.post(
            ENDPOINT, data={"transcript": TYPED_FALL}, files=audio_upload()
        ).json()

        self.assertEqual(body["emergency_type"], "fall")

    def test_whitespace_stt_transcript_falls_back_to_typed(self):
        self.use_speech(StubTranscriber(transcript="    "))

        body = self.client.post(
            ENDPOINT, data={"transcript": TYPED_FALL}, files=audio_upload()
        ).json()

        self.assertEqual(body["emergency_type"], "fall")

    def test_malformed_stt_payload_falls_back_to_typed(self):
        self.use_speech(StubTranscriber(result={"not_transcript": "oops"}))

        body = self.client.post(
            ENDPOINT, data={"transcript": TYPED_FALL}, files=audio_upload()
        ).json()

        self.assertEqual(body["emergency_type"], "fall")


class SpeechDegradationTests(BackendTestCase):
    def test_audio_only_with_stt_failure_returns_502(self):
        self.use_speech(StubTranscriber(error=TranscriptionError("unavailable")))

        response = self.client.post(ENDPOINT, files=audio_upload())

        self.assertEqual(response.status_code, 502)
        self.assertEqual(set(response.json()), {"detail"})
        self.assertIsInstance(response.json()["detail"], str)

    def test_audio_only_with_empty_stt_returns_502(self):
        self.use_speech(StubTranscriber(transcript=""))

        response = self.client.post(ENDPOINT, files=audio_upload())

        self.assertEqual(response.status_code, 502)

    def test_stt_failure_with_successful_vision_uses_vision_alone(self):
        self.use_speech(StubTranscriber(error=TranscriptionError("unavailable")))

        response = self.client.post(
            ENDPOINT, files={**audio_upload(), **image_upload()}
        )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["emergency_type"], "possible_fire")
        self.assertIn("no supporting description", body["reason"])

    def test_empty_stt_with_successful_vision_uses_vision_alone(self):
        self.use_speech(StubTranscriber(transcript="   "))

        response = self.client.post(
            ENDPOINT, files={**audio_upload(), **image_upload()}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("no supporting description", response.json()["reason"])

    def test_empty_stt_no_typed_and_vision_failure_returns_502(self):
        self.use_speech(StubTranscriber(transcript=""))
        self.use_vision(StubAnalyzer(error=ImageAnalysisError("unavailable")))

        response = self.client.post(
            ENDPOINT, files={**audio_upload(), **image_upload()}
        )

        self.assertEqual(response.status_code, 502)

    def test_stt_and_vision_both_fail_but_typed_transcript_survives(self):
        self.use_speech(StubTranscriber(error=TranscriptionError("unavailable")))
        self.use_vision(StubAnalyzer(error=ImageAnalysisError("unavailable")))

        response = self.client.post(
            ENDPOINT,
            data={"transcript": TYPED_FALL},
            files={**audio_upload(), **image_upload()},
        )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["emergency_type"], "fall")
        self.assertIn("no supporting vision result", body["reason"])

    def test_both_failing_without_typed_text_names_both_in_the_message(self):
        self.use_speech(StubTranscriber(error=TranscriptionError("unavailable")))
        self.use_vision(StubAnalyzer(error=ImageAnalysisError("unavailable")))

        response = self.client.post(
            ENDPOINT, files={**audio_upload(), **image_upload()}
        )
        detail = response.json()["detail"]

        self.assertEqual(response.status_code, 502)
        self.assertIn("recording", detail)
        self.assertIn("photo", detail)

    def test_unexpected_stt_error_degrades_without_leaking(self):
        self.use_speech(ExplodingTranscriber())

        response = self.client.post(
            ENDPOINT, data={"transcript": TYPED_FALL}, files=audio_upload()
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["emergency_type"], "fall")

    def test_unexpected_stt_error_without_fallback_is_a_safe_502(self):
        self.use_speech(ExplodingTranscriber())

        response = self.client.post(ENDPOINT, files=audio_upload())
        detail = response.json()["detail"]

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("sk-12345", detail)
        self.assertNotIn("secret_path", detail)

    def test_stt_failure_is_logged_server_side(self):
        self.use_speech(StubTranscriber(error=TranscriptionError("provider said no")))

        with self.assertLogs("backend.services.orchestrator", level="WARNING") as logs:
            self.client.post(
                ENDPOINT, data={"transcript": TYPED_FALL}, files=audio_upload()
            )

        self.assertTrue(
            any("Speech transcription failed" in line for line in logs.output)
        )

    def test_vision_failure_is_logged_server_side(self):
        self.use_vision(StubAnalyzer(error=ImageAnalysisError("provider said no")))

        with self.assertLogs("backend.services.orchestrator", level="WARNING") as logs:
            self.client.post(
                ENDPOINT, data={"transcript": "There is a fire."}, files=image_upload()
            )

        self.assertTrue(any("Image analysis failed" in line for line in logs.output))


class RejectionTests(BackendTestCase):
    def test_missing_everything_returns_400(self):
        response = self.client.post(ENDPOINT, data={})

        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response.json()["detail"], str)

    def test_whitespace_only_transcript_returns_400(self):
        response = self.client.post(ENDPOINT, data={"transcript": "    "})

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("actions", response.json())


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

class SafetyTests(BackendTestCase):
    def _assert_no_leak(self, text):
        lowered = text.lower()

        for marker in LEAK_MARKERS:
            self.assertNotIn(marker, lowered, f"leaked {marker!r}: {text}")

    def test_error_details_contain_nothing_internal(self):
        responses = [self.client.post(ENDPOINT, data={})]

        self.use_speech(StubTranscriber(error=TranscriptionError("provider detail")))
        responses.append(self.client.post(ENDPOINT, files=audio_upload()))

        self.use_speech(ExplodingTranscriber())
        responses.append(self.client.post(ENDPOINT, files=audio_upload()))

        self.use_vision(StubAnalyzer(error=ImageAnalysisError("provider detail")))
        responses.append(self.client.post(ENDPOINT, files=image_upload()))

        self.use_vision(ExplodingAnalyzer())
        responses.append(self.client.post(ENDPOINT, files=image_upload()))

        responses.append(self.client.get("/api/emergency/does-not-exist"))

        for response in responses:
            with self.subTest(status=response.status_code):
                self._assert_no_leak(response.json()["detail"])

    def test_every_error_response_is_json_with_a_string_detail(self):
        self.use_speech(StubTranscriber(error=TranscriptionError("nope")))

        for response in (
            self.client.post(ENDPOINT, data={}),
            self.client.post(ENDPOINT, files=audio_upload()),
            self.client.get("/nope"),
        ):
            with self.subTest(status=response.status_code):
                body = response.json()

                self.assertEqual(set(body), {"detail"})
                self.assertIsInstance(body["detail"], str)

    def test_502_body_carries_no_assessment(self):
        self.use_speech(StubTranscriber(error=TranscriptionError("nope")))

        body = self.client.post(ENDPOINT, files=audio_upload()).json()

        self.assertEqual(set(body), {"detail"})
        self.assertNotIn("unknown", body["detail"].lower())

    def test_backend_never_claims_emergency_services_were_contacted(self):
        body = self.client.post(
            ENDPOINT, files={**audio_upload(), **image_upload()}
        ).json()

        blob = " ".join([body["reason"], *body["actions"]]).lower()

        for claim in (
            "have been contacted",
            "has been contacted",
            "ambulance dispatched",
            "help is on the way",
            "help is coming",
            "location shared",
            "we called",
            "police contacted",
        ):
            self.assertNotIn(claim, blob)

    def test_successful_response_always_has_exactly_five_fields(self):
        for kwargs in (
            {"data": {"transcript": SPOKEN_FIRE}},
            {"files": audio_upload()},
            {"files": image_upload()},
            {"files": {**audio_upload(), **image_upload()}},
            {"data": {"transcript": TYPED_FALL}, "files": audio_upload()},
        ):
            with self.subTest(kwargs=sorted(kwargs)):
                body = self.client.post(ENDPOINT, **kwargs).json()

                self.assertEqual(set(body), EXPECTED_KEYS)

    def test_cors_allows_the_frontend_origins_only(self):
        for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
            with self.subTest(origin=origin):
                response = self.client.options(
                    ENDPOINT,
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "POST",
                    },
                )

                self.assertEqual(
                    response.headers.get("access-control-allow-origin"), origin
                )

        blocked = self.client.options(
            ENDPOINT,
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertIsNone(blocked.headers.get("access-control-allow-origin"))


# ---------------------------------------------------------------------------
# Orchestrator, without a server
# ---------------------------------------------------------------------------

class OrchestratorTests(unittest.TestCase):
    def test_clean_transcript_trims_only_surrounding_whitespace(self):
        self.assertEqual(clean_transcript("  There is a fire.  "), "There is a fire.")
        self.assertEqual(clean_transcript(""), "")
        self.assertEqual(clean_transcript(None), "")
        self.assertEqual(clean_transcript(123), "")

    def test_returns_the_contract_for_a_transcript(self):
        result = analyze_emergency(transcript=SPOKEN_FIRE)

        self.assertEqual(set(result), EXPECTED_KEYS)
        self.assertEqual(result["emergency_type"], "possible_fire")

    def test_clients_are_skipped_when_nothing_is_uploaded(self):
        analyzer = StubAnalyzer()
        transcriber = StubTranscriber()

        analyze_emergency(
            transcript="There is a fire.", analyzer=analyzer, transcriber=transcriber
        )

        self.assertEqual(analyzer.calls, [])
        self.assertEqual(transcriber.calls, [])

    def test_speech_and_vision_are_independent(self):
        analyzer = StubAnalyzer()
        transcriber = StubTranscriber(error=TranscriptionError("down"))

        result = analyze_emergency(
            audio=AudioUpload(AUDIO_BYTES, "a.webm", "audio/webm"),
            image=ImageUpload(IMAGE_BYTES, "a.jpg", "image/jpeg"),
            analyzer=analyzer,
            transcriber=transcriber,
        )

        # Speech failed, vision still ran and carried the request.
        self.assertEqual(len(transcriber.calls), 1)
        self.assertEqual(len(analyzer.calls), 1)
        self.assertEqual(result["emergency_type"], "possible_fire")

    def test_empty_input_raises_input_error(self):
        with self.assertRaises(EmergencyInputError):
            analyze_emergency(transcript="   ")

    def test_audio_only_failure_raises_analysis_unavailable(self):
        with self.assertRaises(AnalysisUnavailableError):
            analyze_emergency(
                audio=AudioUpload(AUDIO_BYTES, "a.webm", "audio/webm"),
                transcriber=StubTranscriber(error=TranscriptionError("down")),
            )

    def test_image_only_failure_raises_analysis_unavailable(self):
        with self.assertRaises(AnalysisUnavailableError):
            analyze_emergency(
                image=ImageUpload(IMAGE_BYTES, "a.jpg", "image/jpeg"),
                analyzer=StubAnalyzer(error=ImageAnalysisError("down")),
            )

    def test_stt_result_is_used_verbatim(self):
        result = analyze_emergency(
            transcript=TYPED_CALM,
            audio=AudioUpload(AUDIO_BYTES, "a.webm", "audio/webm"),
            transcriber=StubTranscriber(transcript="There is a fire."),
        )

        self.assertEqual(result["emergency_type"], "possible_fire")


if __name__ == "__main__":
    unittest.main(verbosity=2)
