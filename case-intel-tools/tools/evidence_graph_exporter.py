#!/usr/bin/env python3
"""Export a redacted visual registry CSV as a simple evidence graph JSON.

The graph is for navigation and review routing. It is not a proof conclusion.
"""

import argparse
import csv
import json
from pathlib import Path


def clean(value):
    return str(value or "").strip()


def node_id(prefix, value):
    raw = clean(value) or "unknown"
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw).strip("_")
    return f"{prefix}_{safe[:80]}"


def read_rows(path):
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [str(name).strip().lower().replace(" ", "_") for name in (reader.fieldnames or [])]
        return list(reader)


def add_node(nodes, node):
    nodes[node["id"]] = node


def export_graph(rows):
    nodes = {}
    edges = []
    for row in rows:
        claim = clean(row.get("claim_id")) or clean(row.get("case_question")) or "unknown_claim"
        lane = clean(row.get("visual_lane")) or "unknown_lane"
        status = clean(row.get("source_status")) or "unknown_status"
        visual = clean(row.get("recommended_visual_type")) or "table"
        bridge = clean(row.get("bridge_needed"))
        locator = clean(row.get("native_locator")) or clean(row.get("drive_file_id")) or clean(row.get("source_locator"))

        claim_id = node_id("claim", claim)
        lane_id = node_id("lane", lane)
        status_id = node_id("status", status)
        visual_id = node_id("visual", visual)

        add_node(nodes, {"id": claim_id, "type": "claim", "label": claim, "question": clean(row.get("case_question"))})
        add_node(nodes, {"id": lane_id, "type": "lane", "label": lane})
        add_node(nodes, {"id": status_id, "type": "source_status", "label": status})
        add_node(nodes, {"id": visual_id, "type": "visual_type", "label": visual})

        edges.append({"source": claim_id, "target": lane_id, "type": "routed_to_lane"})
        edges.append({"source": claim_id, "target": status_id, "type": "has_source_status"})
        edges.append({"source": claim_id, "target": visual_id, "type": "should_render_as"})

        if locator:
            locator_id = node_id("source", locator)
            add_node(nodes, {"id": locator_id, "type": "source_locator", "label": locator})
            edges.append({"source": claim_id, "target": locator_id, "type": "routes_to_source"})

        if bridge:
            bridge_id = node_id("bridge", bridge)
            add_node(nodes, {"id": bridge_id, "type": "bridge_needed", "label": bridge})
            edges.append({"source": claim_id, "target": bridge_id, "type": "requires_bridge"})

    return {"nodes": list(nodes.values()), "edges": edges}


def main():
    parser = argparse.ArgumentParser(description="Export visual registry as evidence graph JSON.")
    parser.add_argument("csv_path")
    args = parser.parse_args()
    print(json.dumps(export_graph(read_rows(args.csv_path)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
