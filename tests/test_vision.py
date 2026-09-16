import unittest

from vision.hazard_detection import (build_result, clamp_confidence,
                                      normalize_hazard, normalize_objects)
from vision.image_analysis import ClaudeVisionAnalyzer, ImageAnalysisError


class HazardDetectionTests(unittest.TestCase):
    def test_normalizes_known_synonym_to_canonical_label(self):
        self.assertEqual(normalize_hazard("Smoke detected"), "smoke")
        self.assertEqual(normalize_hazard("person down"), "person_down")
        self.assertEqual(normalize_hazard("car accident"), "accident")

    def test_passes_through_clear_hazard_values(self):
        self.assertEqual(normalize_hazard("Safe"), "safe")
        self.assertEqual(normalize_hazard("no hazard"), "no hazard")

    def test_falls_back_to_none_for_unknown_text(self):
        self.assertEqual(normalize_hazard("a cat sitting on a sofa"), "none")
        self.assertEqual(normalize_hazard(None), "none")

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
