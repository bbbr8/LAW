import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "visual_quality_gate.py"

spec = importlib.util.spec_from_file_location("visual_quality_gate", MODULE_PATH)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def write_csv(path, rows):
    fieldnames = [
        "claim_id",
        "case_question",
        "visual_lane",
        "recommended_visual_type",
        "source_status",
        "native_locator",
        "bridge_needed",
        "conflict_type",
        "scale_rule",
        "audience",
        "export_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_quality_gate_passes_clean_registry(tmp_path):
    csv_path = tmp_path / "registry.csv"
    write_csv(csv_path, [{
        "claim_id": "SYN-100",
        "case_question": "Where should this redacted item route?",
        "visual_lane": "case_navigation",
        "recommended_visual_type": "subway_map",
        "source_status": "source_routed",
        "native_locator": "REDACTED_ROUTE",
        "bridge_needed": "",
        "conflict_type": "",
        "scale_rule": "not_applicable",
        "audience": "internal_review",
        "export_status": "review_ready",
    }])
    result = gate.audit(gate.read_rows(csv_path))
    assert result["passed"] is True
    assert result["error_count"] == 0


def test_quality_gate_blocks_export_ready_bridge_missing(tmp_path):
    csv_path = tmp_path / "registry.csv"
    write_csv(csv_path, [{
        "claim_id": "SYN-200",
        "case_question": "Which bridge record is still missing?",
        "visual_lane": "bridge_closure",
        "recommended_visual_type": "bridge_board",
        "source_status": "bridge_missing",
        "native_locator": "",
        "bridge_needed": "redacted source path",
        "conflict_type": "",
        "scale_rule": "not_applicable",
        "audience": "internal_review",
        "export_status": "export_ready",
    }])
    result = gate.audit(gate.read_rows(csv_path))
    assert result["passed"] is False
    assert any(error["code"] == "EXPORT_OVERCLAIM" for error in result["errors"])
