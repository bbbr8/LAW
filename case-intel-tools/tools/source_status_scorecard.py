#!/usr/bin/env python3
"""Create a source-status summary from a redacted visual registry CSV."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

WEIGHT = {
    "native_closed": 4,
    "source_routed": 3,
    "derived_analysis": 2,
    "ocr_derived": 2,
    "counsel_review": 1,
    "bridge_missing": 0,
    "source_conflict": 0,
    "summary_only": 0,
}

NEEDS_ACTION = {"bridge_missing", "source_conflict", "summary_only"}


def norm(value):
    return str(value or "").strip().lower().replace(" ", "_")


def read_rows(path):
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [norm(name) for name in (reader.fieldnames or [])]
        return list(reader)


def action_for(status):
    if status == "bridge_missing":
        return "send_to_bridge_board"
    if status == "source_conflict":
        return "send_to_contradiction_matrix"
    if status == "summary_only":
        return "find_source_support"
    return "review"


def score(rows):
    status_counts = Counter()
    export_counts = Counter()
    lanes = defaultdict(Counter)
    action_rows = []
    points = 0
    known = 0

    for row in rows:
        status = norm(row.get("source_status")) or "missing"
        lane = norm(row.get("visual_lane")) or "unknown"
        export_status = norm(row.get("export_status")) or "missing"
        claim_id = str(row.get("claim_id") or "").strip()

        status_counts[status] += 1
        export_counts[export_status] += 1
        lanes[lane][status] += 1

        if status in WEIGHT:
            points += WEIGHT[status]
            known += 1

        if status in NEEDS_ACTION or export_status in {"needs_source_closure", "needs_design_fix"}:
            action_rows.append({
                "claim_id": claim_id,
                "visual_lane": lane,
                "source_status": status,
                "export_status": export_status,
                "recommended_action": action_for(status),
            })

    readiness = round((points / (known * 4)) * 100, 1) if known else 0.0
    return {
        "rows": len(rows),
        "readiness_percent": readiness,
        "status_counts": dict(status_counts),
        "export_counts": dict(export_counts),
        "lane_status_counts": {lane: dict(counts) for lane, counts in lanes.items()},
        "action_rows": action_rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Build a source-status scorecard from CSV.")
    parser.add_argument("csv_path")
    args = parser.parse_args()
    print(json.dumps(score(read_rows(args.csv_path)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
