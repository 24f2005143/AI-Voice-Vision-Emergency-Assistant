# Emergency Agent

The reasoning layer of the AI Voice + Vision Emergency Assistant.

This module is implemented entirely in `agent/emergency_agent.py`.

## 1. Purpose

The agent turns the outputs of the voice and vision modules into a single
structured emergency assessment: what kind of emergency this appears to be,
how severe it is, how confident the assessment is, why that conclusion was
reached, and what the user should do.

It combines **both** sources of evidence rather than trusting either one on
its own. A transcript and a vision result that agree raise confidence; a
transcript and a vision result that disagree lower it and say so in the
`reason` field. Either source may be missing.

The agent is **deterministic and offline**. It is rule based, uses only the
Python standard library (`math`, `re`), makes no network calls, and uses no
LLM. The same input always produces the same output.

## Files

```text
agent/
├── __init__.py               re-exports analyze
├── emergency_agent.py        the implementation
├── test_emergency_agent.py   agent-owned tests (unittest, stdlib only)
└── README.md                 this document
```

The scoring is a hackathon heuristic. It is **not** medically or
scientifically validated and must not be treated as a clinical or triage
assessment.

## 2. Current interface

One public function:

```python
analyze(transcript: str, vision: dict | None) -> dict
```

Importable either way:

```python
from agent import analyze
from agent.emergency_agent import analyze
```

`vision` defaults to `None`. There are no classes, no configuration objects,
and no other public entry points.

### Input: transcript

A plain string. A non-string value is treated as an empty string rather than
raising.

### Input: vision

The vision contract used across the repository:

```json
{
  "hazard": "smoke",
  "objects": ["stove", "person"],
  "confidence": 0.89
}
```

All three keys are read defensively:

- A missing or non-string `hazard` becomes `""`.
- An `objects` value that is not a list becomes `[]`, and entries that are not
  a string or number are dropped rather than coerced into text, so a `None`
  entry never appears as an invented object in the `reason`.
- A `confidence` that cannot be converted to a float, or that is not finite
  (`NaN`, `inf`), falls back to `0.5`. Values outside `0.0`–`1.0` are clamped.
  Malformed confidence never produces a higher score than the fallback.
- A `vision` argument that is not a dict (including `None`) is treated as "no
  vision evidence".

The agent never raises on a malformed vision payload, and it does not mutate
the dict passed to it.

### Output

Always a dict with exactly these five keys:

```text
emergency_type
severity
confidence
reason
actions
```

- `emergency_type` — one of the values listed in section 3.
- `severity` — one of the values listed in section 3.
- `confidence` — float, clamped to `0.0`–`1.0` and rounded to 2 decimals.
- `reason` — a sentence explaining which evidence led to the conclusion.
- `actions` — a list of complete sentences, each ending with a period. It is
  empty **only** when `emergency_type` is `none`.

## 3. Supported behavior

### Emergency types

```text
possible_fire
medical_emergency
fall
accident
intrusion
none
unknown
```

### Severity levels

```text
low
medium
high
critical
```

`none` is always paired with severity `low` and an empty `actions` list.

### Base severity per type

Before any escalation or demotion, each type starts at a fixed severity:

| Type | Base severity |
|---|---|
| `possible_fire` | `high` |
| `medical_emergency` | `high` |
| `accident` | `high` |
| `intrusion` | `high` |
| `fall` | `medium` |
| `unknown` | `low` |
| `none` | `low` |

## 4. Evidence handling

### Transcript evidence

Each emergency type has a keyword list. Matching is **whole word** (with a
tolerated trailing `s`), so `"fellow"` is not read as `"fell"` and
`"firefighter"` is not read as `"fire"`. The type with the most matched
keywords wins; ties are resolved by the order the types are declared.

A transcript match scores `0.45` for one keyword and `+0.15` per additional
keyword, capped at `0.75`.

Transcripts containing a fiction marker (for example `movie`, `film`,
`dream`, `story about`) are treated as carrying **no** evidence, so
*"a movie about a car crash"* does not classify as an emergency.

### Vision evidence

The `hazard` string is matched by substring against the hazard vocabulary for
each type. The match score is the vision `confidence`, plus `0.05` if any
entry in `objects` is a known supporting object for that type (for example
`stove` supports `possible_fire`).

A `hazard` value of `none`, `no hazard`, `no_hazard`, `nothing`, `normal` or
`safe` is read as an explicit "nothing is wrong" signal rather than as a
hazard.

Any other unmatched hazard — including the vision module's `unrecognized`
sentinel — is treated as **no information**, never as an all-clear. It carries
no disagreement penalty, and on its own it yields `unknown` rather than `none`.

### Confidence handling

- **Both sources agree:** confidence combines as
  `t + v * (1 - t)`, capped at `0.95`. Corroboration raises confidence above
  what either source gives alone.
- **One source only:** confidence is capped at `0.70`. A single source can
  never produce near-certainty.
- **Transcript reports a hazard but vision explicitly reports no hazard:**
  confidence is multiplied by `0.85` and the disagreement is stated in
  `reason`.
- Confidence is always clamped to `0.0`–`1.0`.

### Conflicting evidence

When the transcript and vision point at **different** types, the better
supported type normally wins. That is overridden when the other type is more
dangerous and is behind by no more than `0.2` of score per step of risk
priority, so a reported fire is not discarded merely because vision scored a
lower-risk type somewhat higher. The risk ordering used only for this
tie-break is:

```text
possible_fire     4
medical_emergency 3
accident          3
intrusion         3
fall              1
unknown / none    0
```

Conflict confidence is `chosen_score - 0.5 * other_score`, with a floor of
`0.15`. The `reason` field states which rule applied — either *"the better
supported reading was used"* or *"the more dangerous possibility was kept for
safety"*.

This ordering is hand-set for the MVP and is not a validated triage scale.

### Uncertainty handling

- Confidence below `0.4` demotes severity by one level — **except** when the
  type was chosen by the risk override above, so deliberately keeping the
  more dangerous reading does not then quietly downgrade its severity.
- Confidence below `0.5` appends an explicit sentence to `actions`:
  *"This assessment is uncertain, so confirm what is happening before relying
  on it."*
- The `reason` field names the evidence actually used, so a weak conclusion
  is visible rather than implied.

### Distress and unknown handling

`unknown` is returned in three cases:

1. **No usable input at all** — empty transcript and no vision evidence.
   Confidence `0.2`.
2. **A distress signal with no identifiable emergency type** — the transcript
   contains `trapped`, `stuck inside`, `stuck under`, `can't get out` or
   `cannot get out`, but neither source indicates *which* emergency it is.
   Confidence `0.4`. The agent reports `unknown` rather than guessing a
   specific type. These phrases are deliberately narrow so that
   *"stuck in traffic"* is not caught.
3. **A photo that could not be classified, with no transcript** — the hazard
   is neither a clear value nor a recognised one. Confidence `0.2`. Reporting
   `none` here would tell the user the scene is safe when it was never
   actually assessed.

When real evidence identifies a type, that type wins and the distress phrase
only contributes escalation (see below).

### Critical escalation

A short list of explicit life-threatening signals in the transcript or hazard
— including `not breathing`, `unconscious`, `no pulse`, `heart attack`,
`stroke`, `choking`, `severe bleeding`, `trapped` and `armed` — forces
severity to `critical`. These markers **escalate** an assessment; they do not
classify on their own. This is a keyword list for the supported scenarios,
not a medical diagnosis system.

### Safety-focused action generation

`actions` is assembled in a fixed order:

1. At `high` or `critical` severity, a safety line comes first. For
   `possible_fire`, `accident` and `intrusion` — where the scene itself
   threatens the user — it advises moving away from the danger. For
   `medical_emergency` and `fall` — where the user is usually the helper, not
   the person at risk — it instead advises checking that the area around the
   person is safe before approaching.
2. The guidance specific to the emergency type.
3. A contact line: at `high`/`critical`, contact emergency services now; at
   `medium`, contact them if the situation gets worse; for a low-severity
   `unknown`, contact them directly if in danger.
4. The uncertainty sentence, when confidence is below `0.5`.
5. The standing disclaimer (see section 7).

## 5. Integration example

```python
from agent.emergency_agent import analyze

result = analyze(
    transcript="There is smoke in my kitchen.",
    vision={
        "hazard": "smoke",
        "objects": ["stove", "person"],
        "confidence": 0.89,
    },
)
```

This input is deterministic and produces:

```json
{
  "emergency_type": "possible_fire",
  "severity": "high",
  "confidence": 0.95,
  "reason": "The description mentions smoke and the image analysis reports 'smoke' with stove, person visible, which both point to possible fire.",
  "actions": [
    "Move yourself to a safe place first and stay away from the danger.",
    "Leave the area immediately and move away from the smoke or fire.",
    "Do not try to approach or put out the fire yourself.",
    "Turn off the gas or stove supply on your way out only if it is safe.",
    "Contact your local emergency services now.",
    "This assistant only offers guidance and does not replace professional emergency services."
  ]
}
```

Voice only and vision only both work:

```python
analyze("My grandmother fell in the bathroom.", None)
analyze("", {"hazard": "fire", "objects": ["stove"], "confidence": 0.92})
```

## 6. Integration notes

**Backend integration does not exist yet.** At the time of writing,
`backend/main.py` is empty and no endpoint calls this module. The notes below
describe how the current module interfaces line up, not an integration that
is already built.

- **Voice/STT** currently returns `{"transcript": str}`. `analyze()` takes the
  transcript **string**, not the dict, so a caller must unwrap it — for
  example `analyze(voice_result["transcript"], vision_result)`.
- **Vision** currently returns `{"hazard": str, "objects": [...],
  "confidence": float}`, which can be passed directly as the `vision`
  argument with no transformation.
- **Voice response**: `voice/text_to_speech.py` provides
  `make_voice_response(emergency_type, severity, actions)`, which accepts
  three of this agent's output fields directly.
- This module imports only the standard library, so it can be imported and
  run without installing anything from `requirements.txt`.

### Tests

The agent owns its own tests, because `tests/` belongs to another module
owner. From the repository root:

```bash
python3 -m unittest agent.test_emergency_agent -v
python3 -m unittest discover -s agent -t .
python3 agent/test_emergency_agent.py
```

They use `unittest` only — no pytest, no network, no fixtures.

### Coupling with the vision module

`vision/hazard_detection.py` deliberately mirrors two tables from
`agent/emergency_agent.py`: its `CANONICAL_HAZARDS` mirrors `VISION_HAZARDS`,
and its `CLEAR_HAZARDS` must match this module's `CLEAR_HAZARDS` exactly. They
match at the time of writing. Nothing in the repository enforces this, so if
either table is edited, the other must be updated to match.

## 7. Safety

The agent's prototype safety behavior, as implemented:

- **Prioritize immediate safety.** High and critical assessments lead with a
  safety instruction before any other guidance.
- **Direct users to real help.** High and critical assessments tell the user
  to contact their local emergency services now; medium assessments tell them
  to do so if the situation worsens.
- **Communicate uncertainty.** When confidence is below `0.5`, the agent adds
  an explicit sentence telling the user the assessment is uncertain and should
  be confirmed. The `reason` field always names the evidence used.
- **Do not replace emergency services.** Every non-`none` response ends with:
  *"This assistant only offers guidance and does not replace professional
  emergency services."*

This is a prototype. It does not replace emergency services, professional
responders, or human judgment.

## 8. Current limitations

Observable from the current code:

- **Keyword matching only.** Classification depends on fixed keyword and
  hazard lists. Wording outside those lists is not recognized — for example
  `gas leak` is a transcript keyword but is not in the vision hazard
  vocabulary.
- **The fiction filter is coarse.** A fiction marker suppresses the whole
  transcript, so *"I was watching a film and now my kitchen is on fire"*
  contributes no transcript evidence. Vision evidence would still apply.
- **No negation handling**, on either input. *"There is no fire"* matches the
  `fire` keyword, and a vision `hazard` of `"no fire"` is read as a fire. The
  vision module's own normalizer does not emit such labels, so this affects
  direct callers rather than the current pipeline.
- **English only**, and no handling of transcription errors from the speech
  module.
- **Confidence is a heuristic, not a probability.** The combination formulas
  are hand-tuned constants and carry no statistical meaning.
- **Severity does not rise with confidence.** A high-confidence `fall` stays
  at `medium` unless a critical marker is present, because base severity is
  fixed per type.
- **Conflicting evidence can produce a very low confidence** — the floor is
  `0.15` — while severity stays high. This is intentional under the risk
  override, but means a caller may display a high-severity result alongside a
  low confidence number.
- **`unknown` can be paired with `critical`** when a distress marker such as
  `trapped` is present without an identifiable type.
- **Only the first matching hazard group wins.** `_match_vision` returns the
  first type whose vocabulary matches the hazard string, in declaration order,
  so a compound hazard such as `"smoke and blood"` resolves to `possible_fire`
  rather than weighing both. Deterministic, but not a ranked match.
