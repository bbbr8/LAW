from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research.case_vision_lab.retroactive_cv_router import VisionEvalStore


class VisionEvalStoreTests(unittest.TestCase):
    def test_later_resolution_retroactively_marks_correct_prediction(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "vision.sqlite3"
            with VisionEvalStore(db_path) as store:
                store.init()
                observation = store.record_observation(
                    source_hash="a" * 64,
                    model_name="synthetic-model",
                    model_revision="rev-1",
                    task="layout_region",
                    document_type="construction_invoice",
                    predicted_label="line_item_table",
                    confidence=0.92,
                    region={"x": 10, "y": 20, "width": 100, "height": 80},
                    features={"synthetic": True, "degradation": "jpeg"},
                )
                store.add_resolution(
                    observation_id=observation.observation_id,
                    resolved_label="line_item_table",
                    relation="later_human_review",
                    anchor_hash="b" * 64,
                    reviewer="reviewer-test",
                )
                results = store.reevaluate_pending()
                report = store.report()

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["outcome"], "true_positive")
            self.assertTrue(results[0]["exact_match"])
            self.assertEqual(results[0]["route"], "retain_with_monitoring")
            self.assertEqual(report["counts"]["observations"], 1)
            self.assertEqual(report["counts"]["resolutions"], 1)
            self.assertEqual(report["counts"]["reevaluations"], 1)
            self.assertFalse(report["policy"]["raw_case_bytes_stored"])
            self.assertFalse(report["policy"]["automatic_fact_promotion"])
            self.assertTrue(report["policy"]["human_review_required"])

    def test_high_confidence_wrong_prediction_routes_to_disable_or_retrain(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "vision.sqlite3"
            with VisionEvalStore(db_path) as store:
                store.init()
                observation = store.record_observation(
                    source_hash="c" * 64,
                    model_name="synthetic-model",
                    model_revision="rev-2",
                    task="signature_region",
                    document_type="draw_request",
                    predicted_label="borrower_signature",
                    confidence=0.97,
                    features={"synthetic": True},
                )
                store.add_resolution(
                    observation_id=observation.observation_id,
                    resolved_label="decorative_mark",
                    relation="later_source_cross_reference",
                    anchor_hash="d" * 64,
                    reviewer="reviewer-test",
                    notes="Synthetic mismatch used to test the critical route.",
                )
                results = store.reevaluate_pending()

            self.assertEqual(results[0]["outcome"], "false_positive")
            self.assertEqual(results[0]["route"], "disable_or_retrain")
            self.assertGreater(results[0]["confidence_error"], 0.9)

    def test_reevaluation_is_idempotent_for_same_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "vision.sqlite3"
            with VisionEvalStore(db_path) as store:
                store.init()
                observation = store.record_observation(
                    source_hash="e" * 64,
                    model_name="synthetic-model",
                    model_revision="rev-3",
                    task="document_type",
                    document_type="unknown",
                    predicted_label="abstain",
                    confidence=0.10,
                )
                store.add_resolution(
                    observation_id=observation.observation_id,
                    resolved_label="construction_invoice",
                    relation="later_human_review",
                    anchor_hash="f" * 64,
                    reviewer="reviewer-test",
                )
                first = store.reevaluate_pending()
                second = store.reevaluate_pending()

            self.assertEqual(len(first), 1)
            self.assertEqual(first[0]["outcome"], "false_negative")
            self.assertEqual(second, [])


if __name__ == "__main__":
    unittest.main()
