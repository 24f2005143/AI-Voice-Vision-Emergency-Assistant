"""Deterministic emergency reasoning agent.

Combines a voice transcript with a vision result and returns a structured
emergency assessment. Rule based and offline: standard library only, no LLM,
no network calls.

The scoring here is a hackathon heuristic. It is not medically or
scientifically validated and must not be treated as a clinical assessment.

Contract (README section 5.3):

    analyze(transcript: str, vision: dict | None) -> dict

Output keys: emergency_type, severity, confidence, reason, actions.

emergency_type: possible_fire, medical_emergency, fall, accident, intrusion,
                none, unknown
severity:       low, medium, high, critical
confidence:     float between 0.0 and 1.0
actions:        list of complete sentences, empty when emergency_type is none
"""

import math
import re

SEVERITY_LEVELS = ("low", "medium", "high", "critical")

TRANSCRIPT_KEYWORDS = {
    "possible_fire": ["fire", "smoke", "smoky", "burning", "burnt", "flame",
                      "gas leak", "spark", "short circuit"],
    "medical_emergency": ["heart attack", "chest pain", "not breathing",
                          "can't breathe", "cannot breathe", "unconscious",
                          "unresponsive", "bleeding", "stroke", "seizure",
                          "choking", "overdose", "allergic"],
    "fall": ["fell", "fallen", "falling", "slipped", "tripped", "collapsed",
             "on the floor", "on the ground"],
    "accident": ["accident", "crash", "crashed", "collision", "hit by",
                 "ran over", "wreck"],
    "intrusion": ["intruder", "break in", "broke in", "breaking in",
                  "burglar", "robbery", "robbed", "attacker", "armed",
                  "someone is inside", "stranger in"],
}

VISION_HAZARDS = {
    "possible_fire": ["fire", "smoke", "flame", "burning"],
    "medical_emergency": ["blood", "bleeding", "injury", "injured",
                          "unresponsive"],
    "fall": ["fallen", "person_down", "person on floor", "lying", "collapse"],
    "accident": ["crash", "collision", "accident", "damaged vehicle"],
    "intrusion": ["intruder", "weapon", "gun", "knife", "masked"],
}

SUPPORTING_OBJECTS = {
    "possible_fire": ("stove", "oven", "gas cylinder", "kitchen", "cooker"),
    "medical_emergency": ("person", "blood", "medicine"),
    "fall": ("person", "floor", "stairs", "ladder"),
    "accident": ("car", "vehicle", "truck", "motorcycle", "bike"),
    "intrusion": ("person", "weapon", "window", "door"),
}

CLEAR_HAZARDS = ("none", "no hazard", "no_hazard", "nothing", "normal", "safe")

# Phrases that usually mean the speaker is describing fiction or a retelling
# rather than reporting something happening now. Crude but it stops obvious
# false positives such as "a movie about a car crash".
NON_EVENT_MARKERS = ("movie", "film", "tv show", "television", "documentary",
                     "video game", "cartoon", "dream", "story about",
                     "novel", "on tv")

# Explicit life-threatening signals only. This is a short keyword list for the
# scenarios the agent supports, not a medical triage or diagnosis system.
CRITICAL_MARKERS = ("not breathing", "stopped breathing", "can't breathe",
                    "cannot breathe", "unconscious", "unresponsive",
                    "no pulse", "no heartbeat", "heart attack", "stroke",
                    "choking", "severe bleeding", "bleeding heavily",
                    "heavily bleeding", "trapped", "stuck under",
                    "can't get out", "cannot get out", "armed")

# Signals that someone is in trouble without saying what kind of emergency it
# is. They classify as "unknown" rather than guessing a specific type. The
# phrases are deliberately narrow so that "stuck in traffic" is not caught.
DISTRESS_MARKERS = ("trapped", "stuck inside", "stuck under", "can't get out",
                    "cannot get out")

# A distress signal shows something is wrong but says nothing about which
# emergency it is, so confidence stays low.
DISTRESS_CONFIDENCE = 0.4

# A photo that could not be classified carries no information either way, so
# it is no more certain than having received nothing at all. Any hazard string
# outside CLEAR_HAZARDS that matches no known vocabulary lands here — the
# agent never has to know the vision module's sentinel by name.
UNRECOGNIZED_VISION_CONFIDENCE = 0.2

# Rough danger ordering used only to break voice/vision disagreements.
# Hand-set for this hackathon MVP; not a validated triage scale.
RISK_PRIORITY = {
    "possible_fire": 4,
    "medical_emergency": 3,
    "accident": 3,
    "intrusion": 3,
    "fall": 1,
    "unknown": 0,
    "none": 0,
}

# How much score advantage a lower-risk classification may give up per step of
# risk priority before the more dangerous classification is preferred instead.
CONFLICT_MARGIN_PER_RANK = 0.2

# Emergencies where the scene itself threatens the user, so the first advice
# is to get away. Medical emergencies and falls are handled differently: there
# the user is usually the helper, not the person at risk.
SCENE_HAZARD_TYPES = ("possible_fire", "accident", "intrusion")

BASE_SEVERITY = {
    "possible_fire": "high",
    "medical_emergency": "high",
    "accident": "high",
    "intrusion": "high",
    "fall": "medium",
    "unknown": "low",
    "none": "low",
}

TYPE_ACTIONS = {
    "possible_fire": [
        "Leave the area immediately and move away from the smoke or fire.",
        "Do not try to approach or put out the fire yourself.",
        "Turn off the gas or stove supply on your way out only if it is safe.",
    ],
    "medical_emergency": [
        "Stay with the affected person and keep them calm and still.",
        "Check whether the person is breathing and responsive.",
        "Do not give food or water to a person who is not fully conscious.",
    ],
    "fall": [
        "Do not move the person until you know whether they are injured.",
        "Check whether the person is conscious and responsive.",
        "Keep the person warm and still while help is arranged.",
    ],
    "accident": [
        "Move to a safe position away from traffic or further impact.",
        "Do not move seriously injured people unless they are in danger.",
    ],
    "intrusion": [
        "Move to a safe room or leave the area if you can do so safely.",
        "Do not confront the intruder.",
        "Stay quiet and keep your phone with you.",
    ],
    "unknown": [
        "The available information is not enough to identify the situation.",
        "Describe what you can see or hear in more detail.",
    ],
}

DISCLAIMER = ("This assistant only offers guidance and does not replace "
              "professional emergency services.")


def analyze(transcript, vision=None):
    """Return a structured emergency assessment from transcript and vision."""
    transcript = transcript if isinstance(transcript, str) else ""
    t_type, t_score, t_words = _match_transcript(transcript)
    v_type, v_score, hazard, objects, vision_clear = _match_vision(vision)

    has_transcript = bool(transcript.strip())
    has_vision = bool(hazard or objects)
    risk_override = False

    if not has_transcript and not has_vision:
        return _result("unknown", "low", 0.2,
                       "No voice transcript or vision result was provided.",
                       _build_actions("unknown", "low", 0.2))

    if t_type and v_type and t_type == v_type:
        etype = t_type
        confidence = min(0.95, t_score + v_score * (1.0 - t_score))
        reason = "%s and %s, which both point to %s." % (
            _describe_transcript(t_words), _describe_vision(hazard, objects),
            _label(etype))
    elif t_type and v_type:
        etype, chosen_score, other_score, risk_override = _resolve_conflict(
            t_type, t_score, v_type, v_score)
        confidence = max(0.15, chosen_score - 0.5 * other_score)
        tail = ("the more dangerous possibility was kept for safety"
                if risk_override else "the better supported reading was used")
        reason = ("%s while %s; %s, so this assessment is uncertain."
                  % (_describe_transcript(t_words),
                     _describe_vision(hazard, objects), tail))
    elif t_type:
        etype = t_type
        confidence = min(0.7, t_score)
        if vision_clear:
            confidence *= 0.85
            reason = ("%s, but the image analysis reports no hazard, so the "
                      "two sources disagree." % _describe_transcript(t_words))
        elif hazard:
            # Vision answered but the answer could not be classified. That is
            # not a clear scene, so no disagreement penalty is applied and the
            # reason must not claim the photo showed nothing wrong.
            reason = ("%s, and the image analysis could not identify what is "
                      "in the photo." % _describe_transcript(t_words))
        else:
            reason = ("%s, and no supporting vision result was available."
                      % _describe_transcript(t_words))
    elif v_type:
        etype = v_type
        confidence = min(0.7, v_score)
        reason = ("%s, with no supporting description from the user."
                  % _describe_vision(hazard, objects))
    elif _contains(transcript.lower(), DISTRESS_MARKERS):
        etype = "unknown"
        confidence = DISTRESS_CONFIDENCE
        reason = ("the description reports someone trapped or stuck, but "
                  "neither source shows what kind of emergency it is.")
    elif hazard and not vision_clear:
        # A photo was analyzed but nothing in it could be classified, and
        # there is no description to fall back on. Reporting "none" here
        # would tell the user the scene is safe when it was never assessed.
        etype = "unknown"
        confidence = UNRECOGNIZED_VISION_CONFIDENCE
        reason = ("the image analysis could not identify what is in the "
                  "photo, and there is no description to go on.")
    else:
        confidence = 0.7 if (has_transcript and has_vision) else 0.6
        reason = "No emergency indicators were found in the available input."
        return _result("none", "low", confidence, reason, [])

    severity = BASE_SEVERITY[etype]
    if _has_critical_marker(transcript, hazard):
        severity = "critical"
    elif confidence < 0.4 and not risk_override:
        severity = _demote(severity)

    return _result(etype, severity, confidence, reason,
                   _build_actions(etype, severity, confidence))


def _match_transcript(transcript):
    """Return (emergency_type, score, matched_words) for the best match.

    Matching is whole-word so that "fellow" is not read as "fell" and
    "firefighter" is not read as "fire". Transcripts that look like they are
    describing fiction are treated as carrying no evidence.
    """
    text = transcript.lower()
    if _contains(text, NON_EVENT_MARKERS):
        return None, 0.0, []
    best_type, best_score, best_words = None, 0.0, []
    for etype, words in TRANSCRIPT_KEYWORDS.items():
        found = [w for w in words if _contains(text, (w,))]
        if not found:
            continue
        score = min(0.75, 0.45 + 0.15 * (len(found) - 1))
        if score > best_score:
            best_type, best_score, best_words = etype, score, found
    return best_type, best_score, best_words


def _match_vision(vision):
    """Return (emergency_type, score, hazard, objects, reports_no_hazard)."""
    if not isinstance(vision, dict):
        return None, 0.0, "", [], False

    hazard = str(vision.get("hazard") or "").strip().lower()
    raw_objects = vision.get("objects")
    if not isinstance(raw_objects, list):
        raw_objects = []
    # Only real labels count. Coercing None or a nested list into text would
    # invent an object that the vision module never reported, and that text
    # ends up in the user-facing reason.
    objects = [str(o).strip().lower() for o in raw_objects
               if isinstance(o, (str, int, float)) and not isinstance(o, bool)
               and str(o).strip()]

    try:
        raw_confidence = float(vision.get("confidence", 0.5))
        if not math.isfinite(raw_confidence):
            raise ValueError("confidence must be a finite number")
        confidence = _clamp(raw_confidence)
    except (TypeError, ValueError):
        confidence = 0.5

    if hazard in CLEAR_HAZARDS:
        return None, 0.0, hazard, objects, True

    for etype, hazards in VISION_HAZARDS.items():
        if any(h in hazard for h in hazards):
            score = confidence
            if any(o in SUPPORTING_OBJECTS[etype] for o in objects):
                score = _clamp(score + 0.05)
            return etype, score, hazard, objects, False

    return None, 0.0, hazard, objects, False


def _build_actions(etype, severity, confidence):
    if etype == "none":
        return []
    actions = []
    if severity in ("high", "critical"):
        if etype in SCENE_HAZARD_TYPES:
            actions.append("Move yourself to a safe place first and stay away "
                           "from the danger.")
        elif etype in ("medical_emergency", "fall"):
            actions.append("Check that the area around the person is safe "
                           "before you approach them.")
    actions.extend(TYPE_ACTIONS[etype])
    if severity in ("high", "critical"):
        actions.append("Contact your local emergency services now.")
    elif severity == "medium":
        actions.append("Contact your local emergency services if the "
                       "situation gets worse.")
    elif etype == "unknown":
        actions.append("Contact your local emergency services directly if "
                       "you are in danger.")
    if confidence < 0.5:
        actions.append("This assessment is uncertain, so confirm what is "
                       "happening before relying on it.")
    actions.append(DISCLAIMER)
    return actions


def _describe_transcript(words):
    return "the description mentions " + ", ".join(sorted(set(words)))


def _describe_vision(hazard, objects):
    text = "the image analysis reports '%s'" % (hazard or "no hazard")
    if objects:
        text += " with " + ", ".join(objects) + " visible"
    return text


def _resolve_conflict(t_type, t_score, v_type, v_score):
    """Pick one type when transcript and vision disagree.

    The better supported type normally wins. It is overridden when the other
    type is more dangerous and is behind by no more than
    CONFLICT_MARGIN_PER_RANK per step of risk priority, so a reported fire is
    not dropped just because vision scored a lower-risk type slightly higher.
    Cautious by design, and not a validated triage rule.

    Returns (emergency_type, chosen_score, other_score, risk_override).
    """
    if t_score >= v_score:
        chosen, chosen_score, other, other_score = t_type, t_score, v_type, v_score
    else:
        chosen, chosen_score, other, other_score = v_type, v_score, t_type, t_score

    rank_gap = RISK_PRIORITY[other] - RISK_PRIORITY[chosen]
    if rank_gap > 0 and chosen_score - other_score <= CONFLICT_MARGIN_PER_RANK * rank_gap:
        return other, other_score, chosen_score, True
    return chosen, chosen_score, other_score, False


def _contains(text, phrases):
    """Whole-word match, tolerating a simple plural on the last word."""
    return any(re.search(r"\b" + re.escape(p) + r"s?\b", text) for p in phrases)


def _has_critical_marker(transcript, hazard):
    return _contains(transcript.lower() + " " + hazard, CRITICAL_MARKERS)


def _demote(severity):
    index = SEVERITY_LEVELS.index(severity)
    return SEVERITY_LEVELS[max(0, index - 1)]


def _clamp(value):
    return max(0.0, min(1.0, value))


def _label(etype):
    return etype.replace("_", " ")


def _result(emergency_type, severity, confidence, reason, actions):
    return {
        "emergency_type": emergency_type,
        "severity": severity,
        "confidence": round(_clamp(confidence), 2),
        "reason": reason[0].upper() + reason[1:] if reason else reason,
        "actions": actions,
    }
