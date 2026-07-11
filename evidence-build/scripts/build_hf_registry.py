#!/usr/bin/env python3
"""Convert the local Hugging Face model registry YAML into CSV/JSONL outputs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml

FIELDS = ["id", "task", "stage", "priority", "input", "output", "boundary", "url"]


def load_registry(path: Path) -> list[dict[str, str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    models = data.get("models", [])
    return [{field: str(model.get(field, "")) for field in FIELDS} for model in models]


def write_csv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("registry_yml", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--jsonl", type=Path)
    args = parser.parse_args()
    rows = load_registry(args.registry_yml)
    write_csv(rows, args.output_csv)
    if args.jsonl:
        write_jsonl(rows, args.jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
