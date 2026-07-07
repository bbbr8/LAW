#!/usr/bin/env python3
"""Generate a bridge-closure board from a redacted visual registry CSV."""

import argparse
import csv
import json
from pathlib import Path


def norm(value):
    return str(value or "").strip()


def read_rows(path):
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [str(name).strip().lower().replace(" ", "_") for name in (reader.fieldnames or [])]
        return list(reader)


def bridge_rows(rows):
    output = []
    for row in rows:
        status = norm(row.get("source_status")).lower()
        bridge_needed = norm(row.get("bridge_needed"))
        export_status = norm(row.get("export_status")).lower()
        if status == "bridge_missing" or bridge_needed or export_status == "needs_source_closure":
            output.append({
                "claim_id": norm(row.get("claim_id")),
                "case_question": norm(row.get("case_question")),
                "visual_lane": norm(row.get("visual_lane")),
                "source_status": status,
                "missing_bridge": bridge_needed or "define_missing_bridge",
                "likely_custodian": norm(row.get("likely_custodian")) or "identify_custodian",
                "next_action": norm(row.get("next_action")) or "request_or_route_native_source",
                "recommended_visual_type": "bridge_board",
                "export_status": "needs_source_closure",
            })
    return output


def main():
    parser = argparse.ArgumentParser(description="Generate bridge-board rows from a visual registry CSV.")
    parser.add_argument("csv_path")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    args = parser.parse_args()

    rows = bridge_rows(read_rows(args.csv_path))
    if args.format == "json":
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        fieldnames = ["claim_id", "case_question", "visual_lane", "source_status", "missing_bridge", "likely_custodian", "next_action", "recommended_visual_type", "export_status"]
        writer = csv.DictWriter(__import__("sys").stdout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
