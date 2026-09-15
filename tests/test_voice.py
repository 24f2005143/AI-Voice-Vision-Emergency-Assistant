
import unittest

from voice.speech_to_text import SpeechmaticsTranscriber, TranscriptionError, _extract_transcript
from voice.text_to_speech import make_voice_response


class VoiceTests(unittest.TestCase):
    def test_extracts_words_from_speechmatics_result(self):
        payload = {"results": [
            {"type": "word", "alternatives": [{"content": "There"}]},
            {"type": "punctuation", "alternatives": [{"content": "."}]},
            {"type": "word", "alternatives": [{"content": "is"}]},
            {"type": "word", "alternatives": [{"content": "smoke"}]},
        ]}
        self.assertEqual(_extract_transcript(payload), "There is smoke")

    def test_rejects_empty_audio_before_network_request(self):
        client = SpeechmaticsTranscriber(api_key="test")
        with self.assertRaisesRegex(TranscriptionError, "record or upload"):
            client.transcribe(b"", "recording.webm", "audio/webm")

    def test_rejects_unknown_audio_type(self):
        client = SpeechmaticsTranscriber(api_key="test")
        with self.assertRaisesRegex(TranscriptionError, "Unsupported"):
            client.transcribe(b"audio", "recording.txt", "text/plain")

    def test_builds_browser_speech_payload(self):
        result = make_voice_response("possible_fire", "high", ["Leave the area."])
        self.assertEqual(result["mode"], "browser")
        self.assertIn("may be an emergency", result["text"])
        self.assertIn("Leave the area.", result["text"])


if __name__ == "__main__":
    unittest.main()
