#!/usr/bin/env python3
"""Create a reproducible inventory of image entries in a PDF."""
from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

try:
    import fitz
except ImportError as exc:
    raise SystemExit("Install requirements first: pip install -r evidence-build/requirements.txt") from exc


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inventory(pdf_path: Path) -> list[dict[str, object]]:
    doc = fitz.open(pdf_path)
    rows: list[dict[str, object]] = []
    for page_index in range(len(doc)):
        for n, img in enumerate(doc[page_index].get_images(full=True), start=1):
            xref = img[0]
            smask = img[1] or ""
            width = img[2]
            height = img[3]
            bpc = img[4]
            colorspace = img[5]
            try:
                payload = doc.extract_image(xref).get("image", b"")
            except Exception:
                payload = b""
            rows.append({
                "source_file": pdf_path.name,
                "page": page_index + 1,
                "image_no": n,
                "xref": xref,
                "smask_xref": smask,
                "width_px": width,
                "height_px": height,
                "bpc": bpc,
                "colorspace": colorspace,
                "bytes": len(payload),
                "sha256": sha(payload) if payload else "",
            })
    doc.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()
    rows = inventory(args.input_pdf)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = ["source_file", "page", "image_no", "xref", "smask_xref", "width_px", "height_px", "bpc", "colorspace", "bytes", "sha256"]
    with args.output_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
