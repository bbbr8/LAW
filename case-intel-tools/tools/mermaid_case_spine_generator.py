#!/usr/bin/env python3
"""Generate a Mermaid case-spine diagram from a redacted CSV.

Expected columns: stage_id, label, next_stage, source_status.
"""

import argparse
import csv
from pathlib import Path

STATUS_CLASS = {
    "native_closed": "nativeClosed",
    "source_routed": "sourceRouted",
    "bridge_missing": "bridgeMissing",
    "source_conflict": "sourceConflict",
    "ocr_derived": "ocrDerived",
    "summary_only": "summaryOnly",
    "derived_analysis": "derivedAnalysis",
    "counsel_review": "reviewNeeded",
}


def safe_id(value):
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in str(value or ""))
    return cleaned.strip("_") or "node"


def read_rows(path):
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [str(name).strip().lower().replace(" ", "_") for name in (reader.fieldnames or [])]
        return list(reader)


def generate(rows):
    lines = ["flowchart LR"]
    lines.append("  classDef nativeClosed stroke-width:3px;")
    lines.append("  classDef sourceRouted stroke-width:2px;")
    lines.append("  classDef bridgeMissing stroke-dasharray: 5 5;")
    lines.append("  classDef sourceConflict stroke-dasharray: 2 2;")
    lines.append("  classDef ocrDerived stroke-dasharray: 8 3;")
    lines.append("  classDef summaryOnly stroke-dasharray: 1 4;")
    lines.append("  classDef derivedAnalysis stroke-width:1px;")
    lines.append("  classDef reviewNeeded stroke-width:2px;")

    ids = set()
    for row in rows:
        node_id = safe_id(row.get("stage_id") or row.get("claim_id") or row.get("label"))
        label = str(row.get("label") or row.get("case_question") or node_id).replace('"', "'")
        status = str(row.get("source_status") or "").strip().lower()
        class_name = STATUS_CLASS.get(status, "reviewNeeded")
        ids.add(node_id)
        lines.append(f'  {node_id}["{label}"]')
        lines.append(f"  class {node_id} {class_name}")

    for row in rows:
        node_id = safe_id(row.get("stage_id") or row.get("claim_id") or row.get("label"))
        next_stage = str(row.get("next_stage") or "").strip()
        if next_stage:
            lines.append(f"  {node_id} --> {safe_id(next_stage)}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate Mermaid case-spine diagram from CSV.")
    parser.add_argument("csv_path")
    args = parser.parse_args()
    print(generate(read_rows(args.csv_path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
