from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research.case_vision_lab.model_adapters import load_model_adapters
from research.case_vision_lab.retroactive_cv_router import VisionEvalStore
from research.case_vision_lab.synthetic_benchmark import run


class VisionEvalStoreTests(unittest.TestCase):
    def test_later_resolution_retroactively_marks_correct_prediction(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "vision.sqlite3"
            with VisionEvalStore(db_path) as store:
                store.init()
                observation = store.record_observation(
                    source_hash="a" * 64,
                    model_name="synthetic-model",
                    model_revision="1" * 40,
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
                    model_revision="2" * 40,
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
                    model_revision="3" * 40,
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

    def test_observation_rejects_mutable_or_missing_model_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with VisionEvalStore(Path(tmpdir) / "vision.sqlite3") as store:
                store.init()
                with self.assertRaisesRegex(ValueError, "immutable 40-character commit SHA"):
                    store.record_observation(
                        source_hash="a" * 64,
                        model_name="synthetic-model",
                        model_revision="main",
                        task="layout_region",
                        document_type="construction_invoice",
                        predicted_label="line_item_table",
                        confidence=0.5,
                    )


class VisionLabConfigurationTests(unittest.TestCase):
    def test_all_declared_model_adapters_use_immutable_revisions(self) -> None:
        manifest = load_model_adapters()

        self.assertEqual(len(manifest["adapters"]), 3)
        self.assertFalse(manifest["promotion_policy"]["automatic_fact_promotion"])
        self.assertTrue(manifest["promotion_policy"]["human_review_required"])
        self.assertTrue(manifest["promotion_policy"]["exact_source_anchor_required"])
        self.assertFalse(manifest["promotion_policy"]["native_case_data_allowed_in_repository"])

    def test_small_synthetic_benchmark_preserves_privacy_and_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run(Path(tmpdir) / "benchmark", count=1, seed=20260718)

        self.assertEqual(result["fixtures"]["fixture_count"], 7)
        self.assertEqual(result["fixtures"]["integrity_failures"], 0)
        self.assertEqual(result["fixtures"]["privacy_failures"], 0)
        self.assertTrue(result["fixtures"]["same_seed_hashes_deterministic"])
        self.assertTrue(result["privacy_and_promotion_safeguards_passed"])
        self.assertFalse(result["router"]["policy"]["automatic_fact_promotion"])

    def test_source_and_resolution_anchors_require_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with VisionEvalStore(Path(tmpdir) / "vision.sqlite3") as store:
                store.init()
                with self.assertRaisesRegex(ValueError, "source_hash"):
                    store.record_observation(
                        source_hash="not-a-hash",
                        model_name="synthetic-model",
                        model_revision="4" * 40,
                        task="layout_region",
                        document_type="construction_invoice",
                        predicted_label="line_item_table",
                        confidence=0.5,
                    )

                observation = store.record_observation(
                    source_hash="b" * 64,
                    model_name="synthetic-model",
                    model_revision="4" * 40,
                    task="layout_region",
                    document_type="construction_invoice",
                    predicted_label="line_item_table",
                    confidence=0.5,
                )
                with self.assertRaisesRegex(ValueError, "anchor_hash"):
                    store.add_resolution(
                        observation_id=observation.observation_id,
                        resolved_label="line_item_table",
                        relation="later_human_review",
                        anchor_hash="not-a-hash",
                        reviewer="reviewer-test",
                    )


if __name__ == "__main__":
    unittest.main()
