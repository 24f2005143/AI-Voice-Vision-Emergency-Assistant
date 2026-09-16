# Vision module

`image_analysis.py` sends an uploaded image to Claude's vision API (a working existing model, per the README's development rule — no training from scratch) and returns:

```json
{"hazard": "smoke", "objects": ["stove", "person"], "confidence": 0.89}
```

Set `VISION_API_KEY` in a local `.env` file before using the live service. Optionally set `VISION_MODEL` to override the default model. The backend should pass the uploaded image bytes, original filename, and MIME type to `ClaudeVisionAnalyzer().analyze(...)`. Supported upload types are JPEG, PNG, and WebP, up to 10 MB.

`hazard_detection.py` has no network code. It normalizes whatever hazard label the model returns onto the fixed vocabulary `agent/emergency_agent.py` already understands (fire/smoke/flame/burning, blood/bleeding/injury/injured/unresponsive, fallen/person_down/"person on floor"/lying/collapse, crash/collision/accident/"damaged vehicle", intruder/weapon/gun/knife/masked), clamps confidence to `[0.0, 1.0]`, and builds the final contract dict. `image_analysis.py` always returns results through this step, so the agent never has to guess at free-text labels.

Failures raise `ImageAnalysisError`; the backend should translate these into a clear 4xx/5xx API response, never expose API keys, and never retry an upload endlessly.

If the model reports `"none"` (or any of `no hazard`, `no_hazard`, `nothing`, `normal`, `safe`), the object list is cleared too, so a confirmed "nothing wrong" reading never carries stray detections into the agent.
