import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "draw_version_decoder.py"


def load_module():
    spec = importlib.util.spec_from_file_location("draw_version_decoder", MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_decoder_prefers_explicit_role_chain_over_nearest_amount():
    decoder = load_module()
    payload = {
        "line_keys": ["base", "added"],
        "versions": [
            {"version_id": "A", "amount_vector": [10, 0], "request_total": 10},
            {"version_id": "B", "amount_vector": [10, 5], "request_total": 15},
        ],
        "support_records": [
            {
                "support_id": "S1",
                "version_id": "A",
                "amount": 10,
                "project_id": "FOREIGN",
                "expected_project_id": "SUBJECT",
                "document_role": "quote",
                "expected_role": "invoice",
            }
        ],
        "payment_candidates": [
            {
                "candidate_id": "EXPLICIT",
                "label": "explicit timing and purpose route",
                "amount_difference": 100,
                "features": {
                    "same_day_message": 1,
                    "same_day_document": 1,
                    "explicit_purpose_match": 1,
                    "support_in_package": 1,
                    "category_present": 1,
                },
            },
            {
                "candidate_id": "NEAREST",
                "label": "nearest amount only",
                "amount_difference": 1,
                "features": {},
            },
        ],
    }
    result = decoder.decode(payload)
    assert result["request_total_checks"][0]["reconciles"] is True
    assert result["version_deltas"][0]["request_delta"] == 5
    assert result["version_deltas"][0]["reconciles"] is True
    assert result["support_audit"]["conflicts"][0]["project_conflict"] is True
    assert result["support_audit"]["conflicts"][0]["role_conflict"] is True
    assert result["payment_candidate_routing"][0]["candidate_id"] == "EXPLICIT"
    assert result["chronology_status"].startswith("OPEN")
