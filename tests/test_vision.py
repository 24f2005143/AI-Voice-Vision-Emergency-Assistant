import unittest

from agent.emergency_agent import VISION_HAZARDS
from vision.hazard_detection import (CANONICAL_HAZARDS, CLEAR_HAZARDS,
                                      UNRECOGNIZED_HAZARD, build_result,
                                      clamp_confidence, normalize_hazard,
                                      normalize_objects)
from vision.image_analysis import ClaudeVisionAnalyzer, ImageAnalysisError


class HazardDetectionTests(unittest.TestCase):
    def test_normalizes_known_synonym_to_canonical_label(self):
        self.assertEqual(normalize_hazard("Smoke detected"), "smoke")
        self.assertEqual(normalize_hazard("person down"), "person_down")
        self.assertEqual(normalize_hazard("car accident"), "accident")

    def test_passes_through_clear_hazard_values(self):
        self.assertEqual(normalize_hazard("Safe"), "safe")
        self.assertEqual(normalize_hazard("no hazard"), "no hazard")

    def test_unknown_text_is_unrecognized_not_clear(self):
        # An unclassifiable hazard must never look like a confirmed all-clear.
        self.assertEqual(normalize_hazard("flooding"), UNRECOGNIZED_HAZARD)
        self.assertEqual(
            normalize_hazard("a cat sitting on a sofa"), UNRECOGNIZED_HAZARD
        )
        self.assertEqual(normalize_hazard("gas leak"), UNRECOGNIZED_HAZARD)

    def test_missing_hazard_is_unrecognized_not_clear(self):
        # The model saying nothing is not the model saying the scene is safe.
        self.assertEqual(normalize_hazard(None), UNRECOGNIZED_HAZARD)
        self.assertEqual(normalize_hazard(""), UNRECOGNIZED_HAZARD)
        self.assertEqual(normalize_hazard("   "), UNRECOGNIZED_HAZARD)

    def test_genuine_clear_labels_are_unchanged(self):
        self.assertEqual(normalize_hazard("none"), "none")
        self.assertEqual(normalize_hazard("safe"), "safe")
        self.assertEqual(normalize_hazard("no hazard"), "no hazard")
        self.assertEqual(normalize_hazard("nothing"), "nothing")

    def test_sentinel_is_not_clear_and_not_canonical(self):
        self.assertNotIn(UNRECOGNIZED_HAZARD, CLEAR_HAZARDS)

        for words in CANONICAL_HAZARDS.values():
            self.assertNotIn(UNRECOGNIZED_HAZARD, words)

    def test_sentinel_does_not_collide_with_agent_vocabulary(self):
        # The agent matches hazards by substring, so the sentinel must not
        # accidentally contain a canonical hazard word.
        for words in VISION_HAZARDS.values():
            for word in words:
                self.assertNotIn(word, UNRECOGNIZED_HAZARD)

    def test_build_result_preserves_objects_for_unrecognized_hazard(self):
        # Objects are the only visual evidence left when the label is unusable.
        result = build_result("flooding", ["water", "person"], 0.9)

        self.assertEqual(result["hazard"], UNRECOGNIZED_HAZARD)
        self.assertEqual(result["objects"], ["water", "person"])

    def test_normalize_objects_dedupes_and_lowercases(self):
        self.assertEqual(
            normalize_objects(["Stove", "person", "STOVE", ""]),
            ["stove", "person"],
        )
        self.assertEqual(normalize_objects("not a list"), [])

    def test_clamp_confidence_bounds_and_defaults(self):
        self.assertEqual(clamp_confidence(1.5), 1.0)
        self.assertEqual(clamp_confidence(-0.2), 0.0)
        self.assertEqual(clamp_confidence("not a number"), 0.5)

    def test_build_result_clears_objects_on_clear_hazard(self):
        result = build_result("none", ["stove"], 0.8)
        self.assertEqual(result, {"hazard": "none", "objects": [],
                                   "confidence": 0.8})

    def test_build_result_matches_readme_contract_shape(self):
        result = build_result("smoke", ["stove", "person"], 0.89)
        self.assertEqual(result, {"hazard": "smoke",
                                   "objects": ["stove", "person"],
                                   "confidence": 0.89})


class ImageAnalysisTests(unittest.TestCase):
    def test_rejects_empty_image_before_network_request(self):
        client = ClaudeVisionAnalyzer(api_key="test")
        with self.assertRaisesRegex(ImageAnalysisError, "upload an image"):
            client.analyze(b"", "photo.jpg", "image/jpeg")

    def test_rejects_unsupported_image_type(self):
        client = ClaudeVisionAnalyzer(api_key="test")
        with self.assertRaisesRegex(ImageAnalysisError, "Unsupported"):
            client.analyze(b"data", "photo.gif", "image/gif")

    def test_rejects_oversized_image(self):
        client = ClaudeVisionAnalyzer(api_key="test")
        with self.assertRaisesRegex(ImageAnalysisError, "too large"):
            client.analyze(b"x" * (10 * 1024 * 1024 + 1), "photo.jpg",
                            "image/jpeg")

    def test_missing_api_key_raises_before_network_request(self):
        client = ClaudeVisionAnalyzer(api_key=None)
        with self.assertRaisesRegex(ImageAnalysisError, "not configured"):
            client.analyze(b"data", "photo.jpg", "image/jpeg")


if __name__ == "__main__":
    unittest.main()
