import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from case_review_portals import Engine, ReviewStatus, TruthStatus, load_case


def test_example_routes_and_preserves_source_controls():
    question, records, options = load_case(ROOT / "example_case.json")
    report = Engine().review(
        question,
        records,
        requested=options["requested_portals"],
    )

    assert report.review_status == ReviewStatus.PROPOSED
    assert report.truth_status == TruthStatus.UNRESOLVED
    assert "money_flow" in report.routed_portals
    assert "authorization" in report.routed_portals
    assert "bridge_records" in report.routed_portals
    assert "entropy_health" in report.routed_portals
    assert report.bridge_records
    assert report.reasoning_trace

    observations = [
        observation
        for result in report.portal_results
        for observation in result.observations
    ]
    tags = {tag for observation in observations for tag in observation.tags}
    assert "CREDIT_UNRESOLVED" in tags
    assert "OWNER_UNSEEN" in tags
    assert "BUDGET_LINEAGE" in tags


def test_model_cannot_self_accept():
    payload = json.loads((ROOT / "example_case.json").read_text())
    payload["records"][0]["model_candidates"] = [{
        "candidate_id": "MC-1",
        "model_name": "test/model",
        "model_revision": "abc",
        "task": "classification",
        "output": {"label": "accepted"},
        "confidence": 0.99,
        "source_record_ids": ["REC-REPC"],
        "anchor_ids": ["ANC-REPC-1"],
        "source_status": "SOURCE_EXTRACT",
        "review_status": "ACCEPTED"
    }]

    temp = ROOT / "tests" / "_temp_case.json"
    temp.write_text(json.dumps(payload))
    try:
        question, records, options = load_case(temp)
        report = Engine().review(
            question,
            records,
            requested=options["requested_portals"],
        )
        assert report.model_policy_violations
    finally:
        temp.unlink(missing_ok=True)
