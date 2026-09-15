# Voice module

`speech_to_text.py` uploads recorded audio to Speechmatics Batch ASR and returns:

```json
{"transcript": "There is smoke in my kitchen."}
```

Set `SPEECHMATICS_API_KEY` in a local `.env` file before using the live service. The backend should pass the upload bytes, original filename, and MIME type to `SpeechmaticsTranscriber().transcribe(...)`. Supported browser upload types include WebM, WAV, MP3, M4A, and OGG.

`text_to_speech.py` deliberately returns a browser SpeechSynthesis payload. This keeps emergency advice local to the browser rather than sending it to another third party. The frontend should call `speechSynthesis.speak(new SpeechSynthesisUtterance(payload.text))` only after a user interaction.

Failures raise `TranscriptionError`; the backend should translate these into a clear 4xx/5xx API response, never expose API keys, and never retry an upload endlessly.
