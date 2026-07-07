#!/usr/bin/env python3
"""Generate a concise Markdown report from a redacted visual registry CSV."""

import argparse
import csv
from collections import Counter
from pathlib import Path

BLOCKING = {"bridge_missing", "source_conflict", "summary_only"}


def norm(value):
    return str(value or "").strip()


def key(value):
    return norm(value).lower().replace(" ", "_") or "missing"


def read_rows(path):
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [key(name) for name in (reader.fieldnames or [])]
        return list(reader)


def table(title, counts):
    lines = [f"## {title}", "", "| Item | Count |", "| --- | ---: |"]
    for item, count in sorted(counts.items()):
        lines.append(f"| {item} | {count} |")
    lines.append("")
    return lines


def generate_report(rows):
    status_counts = Counter(key(row.get("source_status")) for row in rows)
    lane_counts = Counter(key(row.get("visual_lane")) for row in rows)
    visual_counts = Counter(key(row.get("recommended_visual_type")) for row in rows)
    export_counts = Counter(key(row.get("export_status")) for row in rows)

    blockers = []
    for row in rows:
        status = key(row.get("source_status"))
        export_status = key(row.get("export_status"))
        if status in BLOCKING or export_status in {"needs_source_closure", "needs_design_fix"}:
            blockers.append(row)

    lines = [
        "# Visual Registry Experiment Report",
        "",
        "Status: generated from redacted/synthetic registry rows.",
        "",
        f"Total rows: {len(rows)}",
        f"Blocking/action rows: {len(blockers)}",
        "",
        "## Source-status conclusion",
        "",
    ]

    if blockers:
        lines.append("The registry contains rows that require bridge closure, conflict routing, source support, or design repair before export.")
    else:
        lines.append("The registry does not contain blocking rows under the current synthetic test rules.")
    lines.append("")

    lines.extend(table("Source status counts", status_counts))
    lines.extend(table("Visual lane counts", lane_counts))
    lines.extend(table("Recommended visual counts", visual_counts))
    lines.extend(table("Export status counts", export_counts))

    lines.append("## Action rows")
    lines.append("")
    if not blockers:
        lines.append("No action rows detected.")
    else:
        lines.append("| Claim ID | Lane | Status | Export | Required route |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in blockers:
            claim_id = norm(row.get("claim_id")) or "missing"
            lane = key(row.get("visual_lane"))
            status = key(row.get("source_status"))
            export_status = key(row.get("export_status"))
            if status == "bridge_missing":
                route = "bridge_board"
            elif status == "source_conflict":
                route = "contradiction_matrix"
            elif status == "summary_only":
                route = "source_support_search"
            elif export_status == "needs_design_fix":
                route = "visual_design_auditor"
            else:
                route = "source_closure"
            lines.append(f"| {claim_id} | {lane} | {status} | {export_status} | {route} |")
    lines.append("")

    lines.append("## Boundary")
    lines.append("")
    lines.append("This report routes review work. It does not close native proof, authenticate a record, or replace attorney/expert/accounting review.")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate Markdown report from visual registry CSV.")
    parser.add_argument("csv_path")
    args = parser.parse_args()
    print(generate_report(read_rows(args.csv_path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
