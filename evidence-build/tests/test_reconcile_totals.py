from decimal import Decimal
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reconcile_totals.py"
spec = importlib.util.spec_from_file_location("reconcile_totals", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

money = module.money
reconcile_rows = module.reconcile_rows


def test_money_normalizes_currency():
    assert money("$1,234.567") == Decimal("1234.57")


def test_reconcile_rows_passes_small_variance():
    rows = [{"doc_id": "D1", "stated_total": "100.00", "row_sum": "100.01"}]
    out = reconcile_rows(rows, tolerance=Decimal("0.01"))
    assert out[0]["qa_status"] == "PASS"


def test_reconcile_rows_flags_review():
    rows = [{"doc_id": "D1", "stated_total": "100.00", "row_sum": "100.25"}]
    out = reconcile_rows(rows, tolerance=Decimal("0.01"))
    assert out[0]["qa_status"] == "REVIEW"
