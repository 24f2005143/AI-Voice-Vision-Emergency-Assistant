"""Hazard normalization for the vision module.

This module has no network code and no model calls. It takes whatever a
vision model/API returned (often messy free text) and maps it onto the fixed
vocabulary that ``agent/emergency_agent.py`` already understands, then builds
the final contract dict from README section 5.2:

    {"hazard": "smoke", "objects": ["stove", "person"], "confidence": 0.89}

Keeping this separate from ``image_analysis.py`` means the mapping logic can
be unit tested with zero network access, and the model/API in
``image_analysis.py`` can be swapped later without touching this file.
"""

from __future__ import annotations

# Canonical hazard labels, grouped the same way as
# agent.emergency_agent.VISION_HAZARDS so a match here is guaranteed to be
# understood by the agent. Keep these two lists in sync if either changes.
CANONICAL_HAZARDS = {
    "possible_fire": ("fire", "smoke", "flame", "burning"),
    "medical_emergency": ("blood", "bleeding", "injury", "injured",
                           "unresponsive"),
    "fall": ("fallen", "person_down", "person on floor", "lying",
             "collapse"),
    "accident": ("crash", "collision", "accident", "damaged vehicle"),
    "intrusion": ("intruder", "weapon", "gun", "knife", "masked"),
}

# Free-text synonyms a vision model/API is likely to use, mapped onto one of
# the canonical labels above. Add to this as real model output is observed;
# it is deliberately a plain dict rather than anything clever so it stays
# easy to extend.
HAZARD_SYNONYMS = {
    "fire": "fire", "flames": "flame", "on fire": "fire",
    "smoke": "smoke", "smoky": "smoke", "smoke detected": "smoke",
    "burn": "burning", "burnt": "burning", "scorched": "burning",
    "blood": "blood", "bloody": "blood", "bleeding": "bleeding",
    "wound": "injury", "wounded": "injured", "hurt": "injured",
    "unconscious": "unresponsive", "not moving": "unresponsive",
    "fell": "fallen", "fallen down": "fallen", "person down": "person_down",
    "lying down": "lying", "lying on floor": "person on floor",
    "collapsed": "collapse",
    "car crash": "crash", "car accident": "accident",
    "vehicle collision": "collision", "wrecked car": "damaged vehicle",
    "intruder": "intruder", "burglar": "intruder", "masked person": "masked",
    "gun": "weapon", "knife": "weapon", "armed": "weapon",
}

# Values that explicitly mean "the image was checked and nothing is wrong".
# Must match agent.emergency_agent.CLEAR_HAZARDS exactly.
CLEAR_HAZARDS = ("none", "no hazard", "no_hazard", "nothing", "normal",
                  "safe")

# Returned when the model reported something that cannot be mapped onto a
# canonical hazard, or reported nothing at all.
#
# This is deliberately NOT a member of CLEAR_HAZARDS or CANONICAL_HAZARDS.
# "we could not classify this photo" and "this photo is safe" are different
# facts, and collapsing the first into the second turned an unclassified
# hazard such as flooding into a false all-clear.
UNRECOGNIZED_HAZARD = "unrecognized"

DEFAULT_CONFIDENCE = 0.5


def normalize_hazard(raw_hazard: str | None) -> str:
    """Map free-text model output onto the agent's known hazard vocabulary.

    Returns a lowercase string that is either one of ``CLEAR_HAZARDS``, one
    of the canonical labels the agent's ``VISION_HAZARDS`` table recognizes,
    or ``UNRECOGNIZED_HAZARD`` when the model's answer could not be mapped
    onto either. Never raises.

    An empty or missing hazard is unrecognized, not clear: the model saying
    nothing is not the model saying the scene is safe.
    """
    text = str(raw_hazard or "").strip().lower()
    if not text:
        return UNRECOGNIZED_HAZARD
    if text in CLEAR_HAZARDS:
        return text

    if text in HAZARD_SYNONYMS:
        return HAZARD_SYNONYMS[text]

    for canonical_words in CANONICAL_HAZARDS.values():
        if text in canonical_words:
            return text

    for synonym, canonical in HAZARD_SYNONYMS.items():
        if synonym in text:
            return canonical
    for canonical_words in CANONICAL_HAZARDS.values():
        for word in canonical_words:
            if word in text:
                return word

    return UNRECOGNIZED_HAZARD


def normalize_objects(raw_objects) -> list[str]:
    """Clean a list of detected objects: strings, trimmed, lowercased, deduped."""
    if not isinstance(raw_objects, (list, tuple)):
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in raw_objects:
        text = str(item).strip().lower()
        if text and text not in seen:
            seen.add(text)
            cleaned.append(text)
    return cleaned


def clamp_confidence(raw_confidence) -> float:
    """Coerce to float in [0.0, 1.0], falling back to DEFAULT_CONFIDENCE."""
    try:
        value = float(raw_confidence)
    except (TypeError, ValueError):
        return DEFAULT_CONFIDENCE
    return max(0.0, min(1.0, value))


def build_result(raw_hazard, raw_objects, raw_confidence) -> dict:
    """Build the exact README section 5.2 contract dict.

    This is the single place that decides what
    ``image_analysis.py`` hands back to the backend/agent, so any model or
    API can sit behind it as long as it produces a hazard guess, an object
    list, and a confidence number.
    """
    hazard = normalize_hazard(raw_hazard)
    objects = normalize_objects(raw_objects)
    confidence = clamp_confidence(raw_confidence)
    if hazard in CLEAR_HAZARDS:
        # A confirmed "nothing wrong" reading should not carry leftover
        # object detections from an unrelated part of the model's output.
        #
        # An UNRECOGNIZED_HAZARD deliberately does not land here: when the
        # label could not be classified, the objects are the only visual
        # evidence left and discarding them would throw it away.
        objects = []
    return {
        "hazard": hazard,
        "objects": objects,
        "confidence": round(confidence, 2),
    }
