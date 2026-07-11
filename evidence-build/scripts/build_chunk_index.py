#!/usr/bin/env python3
"""Build a simple source-grounded JSONL chunk index from CSV/TSV exports.

This creates chunk metadata for later embedding or reranking. It does not call a model.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def row_text(row: dict[str, str]) -> str:
    parts = []
    for key, value in row.items():
        if value:
            parts.append(f"{key}: {value}")
    return " | ".join(parts)


def stable_id(source_name: str, row_no: int, text: str) -> str:
    digest = hashlib.sha256(f"{source_name}:{row_no}:{text}".encode("utf-8")).hexdigest()[:16]
    return f"chunk-{digest}"


def read_table(path: Path) -> list[dict[str, str]]:
    sample = path.read_text(encoding="utf-8", errors="replace")[:4096]
    dialect = csv.Sniffer().sniff(sample, delimiters=",\t")
    with path.open(newline="", encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh, dialect=dialect))


def build_chunks(files: list[Path]) -> list[dict[str, str]]:
    chunks = []
    for path in files:
        rows = read_table(path)
        for idx, row in enumerate(rows, start=1):
            text = row_text(row)
            if not text:
                continue
            chunks.append({
                "chunk_id": stable_id(path.name, idx, text),
                "source_file": path.name,
                "row_number": idx,
                "text": text,
                "source_anchor": row.get("source_anchor", row.get("source_id", row.get("doc_id", ""))),
            })
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("tables", nargs="+", type=Path)
    args = parser.parse_args()
    chunks = build_chunks(args.tables)
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
