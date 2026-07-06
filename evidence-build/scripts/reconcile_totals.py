#!/usr/bin/env python3
"""Reconcile table-row sums against stated document totals.

Input CSV columns:
  doc_id, stated_total, row_sum

Optional columns are carried through into the output.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

CENT = Decimal("0.01")


def money(value: str | int | float | Decimal) -> Decimal:
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    if not cleaned:
        return Decimal("0.00")
    return Decimal(cleaned).quantize(CENT, rounding=ROUND_HALF_UP)


def reconcile_rows(rows: list[dict[str, str]], tolerance: Decimal = CENT) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        stated = money(row.get("stated_total", "0"))
        row_sum = money(row.get("row_sum", "0"))
        variance = (row_sum - stated).quantize(CENT, rounding=ROUND_HALF_UP)
        status = "PASS" if abs(variance) <= tolerance else "REVIEW"
        updated = dict(row)
        updated["computed_variance"] = str(variance)
        updated["qa_status"] = status
        out.append(updated)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--tolerance", default="0.01")
    args = parser.parse_args()

    with args.input_csv.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    checked = reconcile_rows(rows, money(args.tolerance))
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(checked[0].keys()) if checked else ["doc_id", "stated_total", "row_sum", "computed_variance", "qa_status"]
    with args.output_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(checked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
