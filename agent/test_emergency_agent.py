"""Tests for the emergency reasoning agent.

Standard library only (``unittest``), no network access and no third-party
packages, matching the agent module itself.

These tests assert the behavior the agent currently implements. Where a
behavior is intentional but debatable, it is asserted as-is and recorded as a
limitation in agent/README.md rather than being tested as if it were ideal.

Run from the repository root:

    python3 -m unittest agent.test_emergency_agent -v
    python3 -m unittest discover -s agent -t .
    python3 agent/test_emergency_agent.py
"""

import os
import sys
import unittest

# Running this file directly puts agent/ on sys.path rather than the repository
# root, so add the root to keep "python3 agent/test_emergency_agent.py" working.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.emergency_agent import DISCLAIMER, analyze  # noqa: E402

OUTPUT_KEYS = {"emergency_type", "severity", "confidence", "reason", "actions"}
EMERGENCY_TYPES = {"possible_fire", "medical_emergency", "fall", "accident",
                   "intrusion", "none", "unknown"}
SEVERITY_LEVELS = {"low", "medium", "high", "critical"}

# Wording that would be unsafe unless the sentence forbids or qualifies it.
UNSAFE_FRAGMENTS = ("approach", "confront", "put out", "move the person",
                    "move seriously injured")
SAFE_QUALIFIERS = ("do not", "only if it is safe", "before you approach")

SMOKE_VISION = {"hazard": "smoke", "objects": ["stove", "person"],
                "confidence": 0.89}


class AgentTestCase(unittest.TestCase):
    """Shared contract checks applied to every result."""

    def assert_valid(self, result):
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result), OUTPUT_KEYS)
        self.assertIn(result["emergency_type"], EMERGENCY_TYPES)
        self.assertIn(result["severity"], SEVERITY_LEVELS)
        self.assertIsInstance(result["confidence"], float)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
        self.assertIsInstance(result["reason"], str)
        self.assertTrue(result["reason"])
        self.assertIsInstance(result["actions"], list)
        for action in result["actions"]:
            self.assertIsInstance(action, str)
            self.assertTrue(action.endswith("."), action)
        return result

    def analyze(self, transcript, vision=None):
        return self.assert_valid(analyze(transcript, vision))


class ScenarioTests(AgentTestCase):
    """A-F: the emergency scenarios the agent supports."""

    def test_a_smoke_and_fire(self):
        result = self.analyze("There is smoke in my kitchen.", SMOKE_VISION)
        self.assertEqual(result["emergency_type"], "possible_fire")
        self.assertEqual(result["severity"], "high")

    def test_b_medical_emergency(self):
        result = self.analyze("He is having a heart attack.")
        self.assertEqual(result["emergency_type"], "medical_emergency")

    def test_c_fall(self):
        result = self.analyze(
            "Someone fell down and is hurt.",
            {"hazard": "person_down", "objects": ["person"], "confidence": 0.80},
        )
        self.assertEqual(result["emergency_type"], "fall")
        # Falls start at medium; confidence does not raise severity on its own.
        self.assertEqual(result["severity"], "medium")

    def test_d_accident(self):
        result = self.analyze(
            "There is a car accident.",
            {"hazard": "accident", "objects": ["car"], "confidence": 0.75},
        )
        self.assertEqual(result["emergency_type"], "accident")
        self.assertEqual(result["severity"], "high")

    def test_e_intrusion(self):
        result = self.analyze(
            "There is an intruder in my house.",
            {"hazard": "intruder", "objects": ["person"], "confidence": 0.7},
        )
        self.assertEqual(result["emergency_type"], "intrusion")
        self.assertEqual(result["severity"], "high")

    def test_f_no_emergency(self):
        result = self.analyze("I am making tea and listening to music.",
                              {"hazard": "none", "objects": [], "confidence": 0.95})
        self.assertEqual(result["emergency_type"], "none")
        self.assertEqual(result["severity"], "low")
        self.assertEqual(result["actions"], [])


class InputHandlingTests(AgentTestCase):
    """G-J: unknown, empty, missing and malformed input."""

    def test_g_unknown_when_no_usable_input(self):
        result = self.analyze("", None)
        self.assertEqual(result["emergency_type"], "unknown")
        self.assertEqual(result["severity"], "low")
        self.assertEqual(result["confidence"], 0.2)

    def test_h_empty_transcript_with_vision_still_classifies(self):
        result = self.analyze("", {"hazard": "fire", "objects": ["stove"],
                                   "confidence": 0.92})
        self.assertEqual(result["emergency_type"], "possible_fire")
        # A single source is capped, never near-certain.
        self.assertLessEqual(result["confidence"], 0.7)

    def test_i_missing_vision_is_not_an_error(self):
        result = self.analyze("There is a fire.", None)
        self.assertEqual(result["emergency_type"], "possible_fire")
        self.assertLessEqual(result["confidence"], 0.7)

    def test_j_vision_missing_individual_fields(self):
        for vision in (
            {},
            {"hazard": "smoke"},
            {"objects": ["stove"]},
            {"confidence": 0.9},
            {"hazard": "smoke", "objects": ["stove"]},
            {"hazard": None, "objects": None, "confidence": None},
        ):
            with self.subTest(vision=vision):
                self.analyze("There is a fire.", vision)

    def test_j_vision_wrong_types_do_not_crash(self):
        for vision in ([], "smoke", 7, 0.5, True, ("smoke",), object()):
            with self.subTest(vision=vision):
                self.analyze("There is a fire.", vision)

    def test_j_non_string_transcript_is_treated_as_empty(self):
        for transcript in (None, 123, 4.5, b"there is smoke", [], {}):
            with self.subTest(transcript=transcript):
                result = self.analyze(transcript, None)
                self.assertEqual(result["emergency_type"], "unknown")

    def test_j_malformed_confidence_falls_back_and_never_inflates(self):
        # Garbage must not buy more confidence than a plain default would.
        for bad in ("abc", None, [], float("nan"), float("inf"),
                    float("-inf"), "nan", "inf"):
            with self.subTest(confidence=bad):
                result = self.analyze(
                    "", {"hazard": "smoke", "objects": [], "confidence": bad})
                self.assertLessEqual(result["confidence"], 0.5)

    def test_j_out_of_range_confidence_is_clamped(self):
        high = self.analyze("", {"hazard": "smoke", "objects": [],
                                 "confidence": 99})
        low = self.analyze("", {"hazard": "smoke", "objects": [],
                                "confidence": -99})
        self.assertLessEqual(high["confidence"], 1.0)
        self.assertGreaterEqual(low["confidence"], 0.0)

    def test_j_non_string_objects_are_not_invented_as_evidence(self):
        result = self.analyze(
            "", {"hazard": "smoke", "objects": [None, ["a"], {"k": 1}, "stove"],
                 "confidence": 0.9})
        self.assertIn("stove", result["reason"])
        for junk in ("none,", "['a']", "{'k': 1}"):
            self.assertNotIn(junk, result["reason"])


class EvidenceCombinationTests(AgentTestCase):
    """K-L: how the two sources are combined."""

    def test_k_agreement_raises_confidence_above_either_source(self):
        both = self.analyze("There is smoke.", SMOKE_VISION)
        voice_only = self.analyze("There is smoke.", None)
        vision_only = self.analyze("", SMOKE_VISION)
        self.assertEqual(both["emergency_type"], "possible_fire")
        self.assertGreater(both["confidence"], voice_only["confidence"])
        self.assertGreater(both["confidence"], vision_only["confidence"])
        self.assertLessEqual(both["confidence"], 0.95)

    def test_k_agreement_confidence_is_capped(self):
        result = self.analyze("There is smoke and fire.",
                              {"hazard": "smoke", "objects": ["stove"],
                               "confidence": 1.0})
        self.assertLessEqual(result["confidence"], 0.95)

    def test_l_conflict_keeps_the_more_dangerous_reading(self):
        result = self.analyze(
            "There is a fire in my kitchen.",
            {"hazard": "person_down", "objects": ["person", "floor"],
             "confidence": 0.85})
        # Fire outranks fall, so it is kept even though vision scored higher.
        self.assertEqual(result["emergency_type"], "possible_fire")
        self.assertGreaterEqual(result["confidence"], 0.15)
        self.assertIn("uncertain", result["reason"])

    def test_l_conflict_without_risk_gap_uses_better_supported_source(self):
        result = self.analyze(
            "My grandmother fell.",
            {"hazard": "fire", "objects": ["stove"], "confidence": 0.95})
        self.assertEqual(result["emergency_type"], "possible_fire")

    def test_l_vision_reporting_no_hazard_lowers_voice_confidence(self):
        disagreed = self.analyze("I smell smoke.",
                                 {"hazard": "none", "objects": [],
                                  "confidence": 0.9})
        alone = self.analyze("I smell smoke.", None)
        self.assertEqual(disagreed["emergency_type"], "possible_fire")
        self.assertLess(disagreed["confidence"], alone["confidence"])
        self.assertIn("disagree", disagreed["reason"])


class SeverityTests(AgentTestCase):
    """M-N: critical escalation and distress signals."""

    def test_m_critical_medical_emergency(self):
        result = self.analyze("He is unconscious and not breathing.", None)
        self.assertEqual(result["emergency_type"], "medical_emergency")
        self.assertEqual(result["severity"], "critical")

    def test_m_critical_markers_escalate_but_do_not_classify(self):
        # "severe" alone is not a critical marker and not an emergency type.
        self.assertEqual(self.analyze("He has a severe headache.")["emergency_type"],
                         "none")
        combined = self.analyze("There is a fire and someone is trapped inside.")
        self.assertEqual(combined["emergency_type"], "possible_fire")
        self.assertEqual(combined["severity"], "critical")

    def test_n_standalone_distress_is_unknown_not_a_guessed_type(self):
        result = self.analyze("Someone is trapped inside.", None)
        self.assertEqual(result["emergency_type"], "unknown")
        self.assertEqual(result["confidence"], 0.4)

    def test_n_distress_phrases_are_narrow(self):
        # Everyday "stuck" wording must not be read as entrapment.
        for phrase in ("I am stuck in traffic.", "I am stuck at work today."):
            with self.subTest(phrase=phrase):
                self.assertEqual(self.analyze(phrase)["emergency_type"], "none")

    def test_n_real_evidence_outranks_a_distress_signal(self):
        result = self.analyze(
            "Someone is trapped inside.",
            {"hazard": "fire", "objects": ["stove"], "confidence": 0.9})
        self.assertEqual(result["emergency_type"], "possible_fire")
        self.assertEqual(result["severity"], "critical")


class FalsePositiveTests(AgentTestCase):
    """O-P: word boundaries and fiction language."""

    def test_o_word_boundaries_prevent_prefix_matches(self):
        for phrase in ("My fellow students are here.",
                       "The firefighter gave a talk.",
                       "I am alarmed by the news."):
            with self.subTest(phrase=phrase):
                self.assertEqual(self.analyze(phrase)["emergency_type"], "none")

    def test_o_real_phrasings_are_still_detected(self):
        expected = {
            "someone fell": "fall",
            "someone has fallen": "fall",
            "there is smoke": "possible_fire",
            "there is a fire": "possible_fire",
            "there was a car crash": "accident",
        }
        for phrase, etype in expected.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(self.analyze(phrase)["emergency_type"], etype)

    def test_p_fiction_language_is_not_an_emergency(self):
        for phrase in ("We watched a movie about a car crash.",
                       "We saw a film about a house fire.",
                       "I had a dream about a fire."):
            with self.subTest(phrase=phrase):
                self.assertEqual(self.analyze(phrase)["emergency_type"], "none")


class ContractTests(AgentTestCase):
    """Q-T: confidence bounds, schema, safe wording and determinism."""

    SAMPLES = (
        ("There is smoke in my kitchen.", SMOKE_VISION),
        ("Someone is unconscious and not breathing.",
         {"hazard": "none", "objects": ["person"], "confidence": 0.91}),
        ("Someone fell down and is hurt.",
         {"hazard": "person_down", "objects": ["person"], "confidence": 0.80}),
        ("There is a car accident.",
         {"hazard": "accident", "objects": ["car"], "confidence": 0.75}),
        ("There is a fire.", None),
        ("", None),
        ("Someone is trapped inside.", None),
        ("There is a fire in my kitchen.",
         {"hazard": "person_down", "objects": ["person"], "confidence": 0.85}),
        ("I am making tea.", {"hazard": "none", "objects": [], "confidence": 0.9}),
    )

    def test_q_confidence_always_within_bounds(self):
        for transcript, vision in self.SAMPLES:
            with self.subTest(transcript=transcript):
                confidence = self.analyze(transcript, vision)["confidence"]
                self.assertGreaterEqual(confidence, 0.0)
                self.assertLessEqual(confidence, 1.0)

    def test_q_confidence_never_claims_certainty(self):
        for transcript, vision in self.SAMPLES:
            with self.subTest(transcript=transcript):
                self.assertLess(self.analyze(transcript, vision)["confidence"], 1.0)

    def test_r_output_schema_is_exact(self):
        for transcript, vision in self.SAMPLES:
            with self.subTest(transcript=transcript):
                self.assertEqual(set(self.analyze(transcript, vision)), OUTPUT_KEYS)

    def test_s_every_emergency_response_carries_the_disclaimer(self):
        for transcript, vision in self.SAMPLES:
            with self.subTest(transcript=transcript):
                result = self.analyze(transcript, vision)
                if result["emergency_type"] == "none":
                    self.assertEqual(result["actions"], [])
                else:
                    self.assertTrue(result["actions"])
                    self.assertEqual(result["actions"][-1], DISCLAIMER)

    def test_s_actions_never_encourage_unsafe_intervention(self):
        for transcript, vision in self.SAMPLES:
            result = self.analyze(transcript, vision)
            for action in result["actions"]:
                lowered = action.lower()
                for fragment in UNSAFE_FRAGMENTS:
                    if fragment in lowered:
                        with self.subTest(action=action):
                            self.assertTrue(
                                any(q in lowered for q in SAFE_QUALIFIERS),
                                f"unqualified unsafe wording: {action}")

    def test_s_serious_results_point_to_emergency_services(self):
        for transcript, vision in self.SAMPLES:
            result = self.analyze(transcript, vision)
            if result["severity"] in ("high", "critical"):
                with self.subTest(transcript=transcript):
                    self.assertTrue(
                        any("emergency services" in a for a in result["actions"]))

    def test_s_weak_evidence_is_flagged_as_uncertain(self):
        for transcript, vision in self.SAMPLES:
            result = self.analyze(transcript, vision)
            if result["emergency_type"] != "none" and result["confidence"] < 0.5:
                with self.subTest(transcript=transcript):
                    self.assertTrue(
                        any("uncertain" in a for a in result["actions"]))

    def test_t_output_is_deterministic(self):
        for transcript, vision in self.SAMPLES:
            with self.subTest(transcript=transcript):
                first = analyze(transcript, vision)
                for _ in range(5):
                    self.assertEqual(analyze(transcript, vision), first)

    def test_t_vision_argument_is_not_mutated(self):
        vision = {"hazard": "smoke", "objects": ["stove", "person"],
                  "confidence": 0.89}
        before = {"hazard": "smoke", "objects": ["stove", "person"],
                  "confidence": 0.89}
        analyze("There is smoke.", vision)
        self.assertEqual(vision, before)


class TeamContractTests(AgentTestCase):
    """The agent consumes the voice/vision payload shapes used by the team."""

    def test_voice_payload_transcript_string_is_accepted(self):
        voice_output = {"transcript": "There is smoke in my kitchen."}
        result = self.analyze(voice_output["transcript"], SMOKE_VISION)
        self.assertEqual(result["emergency_type"], "possible_fire")

    def test_vision_payload_is_accepted_unchanged(self):
        vision_output = {"hazard": "smoke", "objects": ["stove", "person"],
                         "confidence": 0.89}
        result = self.analyze("There is smoke in my kitchen.", vision_output)
        self.assertEqual(set(result), OUTPUT_KEYS)

    def test_output_fields_are_json_serializable(self):
        import json
        payload = json.dumps(self.analyze("There is smoke.", SMOKE_VISION))
        self.assertEqual(set(json.loads(payload)), OUTPUT_KEYS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
