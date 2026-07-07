import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_registry(path):
    fieldnames = [
        "claim_id",
        "case_question",
        "visual_lane",
        "recommended_visual_type",
        "source_status",
        "native_locator",
        "drive_file_id",
        "bridge_needed",
        "conflict_type",
        "scale_rule",
        "export_status",
        "next_stage",
        "label",
        "stage_id",
    ]
    rows = [
        {
            "claim_id": "SYN-300",
            "case_question": "Which bridge record closes this synthetic row?",
            "visual_lane": "bridge_closure",
            "recommended_visual_type": "bridge_board",
            "source_status": "bridge_missing",
            "native_locator": "",
            "drive_file_id": "",
            "bridge_needed": "redacted source route",
            "conflict_type": "",
            "scale_rule": "not_applicable",
            "export_status": "needs_source_closure",
            "next_stage": "SYN-301",
            "label": "Bridge check",
            "stage_id": "SYN-300",
        },
        {
            "claim_id": "SYN-301",
            "case_question": "Where should this synthetic source-routed row go?",
            "visual_lane": "case_navigation",
            "recommended_visual_type": "subway_map",
            "source_status": "source_routed",
            "native_locator": "REDACTED_ROUTE",
            "drive_file_id": "",
            "bridge_needed": "",
            "conflict_type": "",
            "scale_rule": "not_applicable",
            "export_status": "review_ready",
            "next_stage": "",
            "label": "Source route",
            "stage_id": "SYN-301",
        },
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_bridge_board_generator_extracts_bridge_rows(tmp_path):
    tool = load_tool("bridge_board_generator")
    csv_path = tmp_path / "registry.csv"
    write_registry(csv_path)
    rows = tool.bridge_rows(tool.read_rows(csv_path))
    assert len(rows) == 1
    assert rows[0]["recommended_visual_type"] == "bridge_board"
    assert rows[0]["missing_bridge"] == "redacted source route"


def test_evidence_graph_exporter_creates_nodes_and_edges(tmp_path):
    tool = load_tool("evidence_graph_exporter")
    csv_path = tmp_path / "registry.csv"
    write_registry(csv_path)
    graph = tool.export_graph(tool.read_rows(csv_path))
    assert graph["nodes"]
    assert graph["edges"]
    assert any(edge["type"] == "has_source_status" for edge in graph["edges"])


def test_mermaid_case_spine_generator_outputs_flowchart(tmp_path):
    tool = load_tool("mermaid_case_spine_generator")
    csv_path = tmp_path / "registry.csv"
    write_registry(csv_path)
    output = tool.generate(tool.read_rows(csv_path))
    assert "flowchart LR" in output
    assert "SYN_300 --> SYN_301" in output
