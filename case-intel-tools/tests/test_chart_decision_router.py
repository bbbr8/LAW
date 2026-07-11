import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "chart_decision_router.py"

spec = importlib.util.spec_from_file_location("chart_decision_router", MODULE_PATH)
router = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = router
spec.loader.exec_module(router)


def test_accounting_flow_with_amount_and_direction_routes_to_sankey():
    columns = router.normalize_columns(["date", "amount", "payor", "payee", "source_status"])
    result = router.choose_chart_type("accounting_flow", columns)
    assert result.recommended_visual_type == "sankey"
    assert result.scale_rule == "zero_baseline_required"


def test_navigation_routes_to_subway_map():
    columns = router.normalize_columns(["stage", "label", "next_stage", "source_status"])
    result = router.choose_chart_type("case_navigation", columns)
    assert result.recommended_visual_type == "subway_map"


def test_bridge_columns_route_to_bridge_board():
    columns = router.normalize_columns(["pressure_point", "bridge_needed", "custodian", "source_status"])
    result = router.choose_chart_type("unknown", columns)
    assert result.recommended_visual_type == "bridge_board"


def test_visual_document_routes_to_page_layout_callout():
    columns = router.normalize_columns(["document_type", "page_locator", "visual_issue", "source_status"])
    result = router.choose_chart_type("document_layout", columns)
    assert result.recommended_visual_type == "page_layout_callout"
