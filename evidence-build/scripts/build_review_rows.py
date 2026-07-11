#!/usr/bin/env python3
"""Build normalized review rows from a source CSV.

Expected input columns:
  item_id, source_anchor, issue, current_status, next_record_needed
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

PRIORITY_RULES = [
    ("native", "P1"),
    ("bank", "P1"),
    ("invoice", "P1"),
    ("signature", "P1"),
    ("metadata", "P2"),
    ("comparator", "P2"),
]


def classify_priority(text: str) -> str:
    low = text.lower()
    for term, priority in PRIORITY_RULES:
        if term in low:
            return priority
    return "P3"


def normalize(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for row in rows:
        needed = row.get("next_record_needed", "")
        out.append({
            "item_id": row.get("item_id", ""),
            "source_anchor": row.get("source_anchor", ""),
            "issue": row.get("issue", ""),
            "current_status": row.get("current_status", "Open"),
            "priority": classify_priority(" ".join(row.values())),
            "next_record_needed": needed,
            "review_note": row.get("review_note", ""),
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()
    with args.input_csv.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = normalize(rows)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item_id", "source_anchor", "issue", "current_status", "priority", "next_record_needed", "review_note"]
    with args.output_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
