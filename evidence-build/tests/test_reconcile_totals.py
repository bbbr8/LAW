from decimal import Decimal

from evidence_build.scripts.reconcile_totals import money, reconcile_rows


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
