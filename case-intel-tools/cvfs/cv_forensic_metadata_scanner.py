#!/usr/bin/env python3
"""CVFS v3 deterministic document-metadata scanner.

The scanner emits review signals and fingerprints. It never concludes fraud,
forgery, authorship, intent, authorization, payment application, or liability.
Native evidence remains in the source-of-truth system; GitHub stores code only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import fitz
import numpy as np

VERSION = "3.0.0"
BOUNDARY = (
    "Review-signal metadata only. Similarity and visual anomalies do not prove "
    "alteration, identity, intent, authorization, application, or liability."
)

HF_LOCAL_ROUTES = {
    "layout": "microsoft/layoutlmv3-base",
    "document_parse": "docling-project/SmolDocling-256M-preview",
    "table_detection": "microsoft/table-transformer-detection",
    "table_structure": "microsoft/table-transformer-structure-recognition",
    "visual_family": "facebook/dinov2-base",
    "zero_shot_visual": "google/siglip2-base-patch16-224",
    "region_segmentation": "facebook/sam2-hiera-base-plus",
}

TOKENS = {
    "startxref": rb"startxref",
    "eof": rb"%%EOF",
    "prev": rb"/Prev\s+\d+",
    "linearized": rb"/Linearized\b",
    "xref_stream": rb"/Type\s*/XRef\b",
    "object_stream": rb"/Type\s*/ObjStm\b",
    "acroform": rb"/AcroForm\b",
    "signature_dictionary": rb"/Type\s*/Sig\b|/FT\s*/Sig\b",
    "byte_range": rb"/ByteRange\s*\[",
    "javascript": rb"/JavaScript\b|/JS\b",
    "open_action": rb"/OpenAction\b",
    "additional_action": rb"/AA\b",
    "embedded_files": rb"/EmbeddedFiles\b",
    "optional_content": rb"/OCProperties\b|/OCG\b",
    "metadata_stream": rb"/Type\s*/Metadata\b",
    "piece_info": rb"/PieceInfo\b",
    "jbig2": rb"/JBIG2Decode\b",
    "dct": rb"/DCTDecode\b",
    "jpx": rb"/JPXDecode\b",
    "ccitt": rb"/CCITTFaxDecode\b",
    "flate": rb"/FlateDecode\b",
    "soft_mask": rb"/SMask\b",
    "icc_profile": rb"/ICCBased\b",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def phash(gray: np.ndarray, size: int = 16) -> str:
    small = cv2.resize(gray, (size * 4, size * 4), interpolation=cv2.INTER_AREA)
    coeff = cv2.dct(np.float32(small))[:size, :size]
    median = np.median(coeff[1:, 1:])
    bits = coeff > median
    return hex(int("".join("1" if x else "0" for x in bits.flat), 2))[2:].zfill(size * size // 4)


def dhash(gray: np.ndarray, size: int = 16) -> str:
    small = cv2.resize(gray, (size + 1, size), interpolation=cv2.INTER_AREA)
    bits = small[:, 1:] > small[:, :-1]
    return hex(int("".join("1" if x else "0" for x in bits.flat), 2))[2:].zfill(size * size // 4)


def hamming(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def entropy(gray: np.ndarray) -> float:
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
    p = hist / max(float(hist.sum()), 1.0)
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def render(page: fitz.Page, dpi: int) -> np.ndarray:
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False, colorspace=fitz.csRGB)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]


def raster_metrics(rgb: np.ndarray) -> dict[str, Any]:
    original_hash = sha256(rgb.tobytes())
    oh, ow = rgb.shape[:2]
    scale = min(1.0, 800 / max(oh, ow))
    if scale < 1:
        rgb = cv2.resize(rgb, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edge = cv2.Canny(gray, 80, 180)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return {
        "width_px": ow,
        "height_px": oh,
        "analysis_width_px": gray.shape[1],
        "analysis_height_px": gray.shape[0],
        "mean_luma": float(gray.mean()),
        "std_luma": float(gray.std()),
        "entropy": entropy(gray),
        "white_ratio_245": float((gray >= 245).mean()),
        "black_ratio_32": float((gray <= 32).mean()),
        "edge_density": float((edge > 0).mean()),
        "laplacian_variance": float(lap.var()),
        "phash": phash(gray),
        "dhash": dhash(gray),
        "raster_sha256": original_hash,
    }


def text_metrics(page: fitz.Page) -> dict[str, Any]:
    raw = page.get_text("rawdict")
    fonts: Counter[str] = Counter()
    sizes: Counter[str] = Counter()
    colors: Counter[str] = Counter()
    chars = invisible = duplicate = 0
    placements: Counter[tuple[str, tuple[float, ...]]] = Counter()
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = "".join(ch.get("c", "") for ch in span.get("chars", []))
                chars += len(text)
                font = str(span.get("font", ""))
                size = float(span.get("size", 0) or 0)
                color = int(span.get("color", 0) or 0)
                alpha = int(span.get("alpha", 255) or 255)
                fonts[font] += max(1, len(text))
                sizes[f"{size:.2f}"] += max(1, len(text))
                colors[str(color)] += max(1, len(text))
                rgb = ((color >> 16) & 255, (color >> 8) & 255, color & 255)
                if alpha <= 1 or all(v >= 245 for v in rgb):
                    invisible += len(text)
                key = (text.strip(), tuple(round(float(x), 1) for x in span.get("bbox", [])))
                if key[0]:
                    placements[key] += 1
    duplicate = sum(v - 1 for v in placements.values() if v > 1)
    return {
        "text_chars": chars,
        "invisible_like_text_chars": invisible,
        "duplicate_span_placements": duplicate,
        "dominant_fonts": fonts.most_common(8),
        "dominant_sizes": sizes.most_common(8),
        "dominant_colors": colors.most_common(8),
    }


def widgets(page: fitz.Page) -> list[dict[str, Any]]:
    out = []
    iterator = page.widgets()
    if not iterator:
        return out
    for item in iterator:
        out.append({
            "field_name": item.field_name,
            "field_type": item.field_type,
            "field_type_string": item.field_type_string,
            "field_flags": item.field_flags,
            "field_value": item.field_value,
            "rect": list(item.rect),
        })
    return out


def annotations(page: fitz.Page) -> list[dict[str, Any]]:
    out = []
    item = page.first_annot
    while item:
        out.append({"type": item.type[1], "rect": list(item.rect), "info": item.info or {}})
        item = item.next
    return out


def image_inventory(doc: fitz.Document, page: fitz.Page, locator: str, page_number: int) -> list[dict[str, Any]]:
    out = []
    keys = ["xref", "smask", "width", "height", "bpc", "colorspace", "alt_colorspace", "name", "filter", "referencer"]
    for row in page.get_images(full=True):
        record = {k: row[i] if i < len(row) else None for i, k in enumerate(keys)}
        xref = record.get("xref")
        if isinstance(xref, int) and xref > 0:
            try:
                extracted = doc.extract_image(xref)
                blob = extracted.get("image", b"")
                record.update({
                    "embedded_sha256": sha256(blob) if blob else None,
                    "embedded_size": len(blob),
                    "extracted_extension": extracted.get("ext"),
                })
            except Exception as error:
                record["extract_error"] = type(error).__name__
        out.append({"record_type": "embedded_image", "source_locator": locator, "page_number": page_number, **record})
    return out


def font_inventory(page: fitz.Page, locator: str, page_number: int) -> list[dict[str, Any]]:
    keys = ["xref", "extension", "font_type", "basefont", "resource_name", "encoding", "referencer"]
    return [
        {"record_type": "font", "source_locator": locator, "page_number": page_number,
         **{k: row[i] if i < len(row) else None for i, k in enumerate(keys)}}
        for row in page.get_fonts(full=True)
    ]


def iter_sources(input_path: Path) -> Iterable[tuple[Path, str, dict[str, Any] | None]]:
    if input_path.is_dir():
        for path in sorted(input_path.rglob("*.pdf")):
            yield path, str(path.relative_to(input_path)), None
        return
    if input_path.suffix.lower() == ".pdf":
        yield input_path, input_path.name, None
        return
    if input_path.suffix.lower() != ".zip":
        raise ValueError("Input must be a PDF, ZIP, or directory")
    archive_hash = sha256_file(input_path)
    with zipfile.ZipFile(input_path) as archive, tempfile.TemporaryDirectory(prefix="cvfs_v3_") as temp:
        root = Path(temp).resolve()
        for info in sorted(archive.infolist(), key=lambda value: value.filename.lower()):
            if info.is_dir() or not info.filename.lower().endswith(".pdf"):
                continue
            target = (root / info.filename).resolve()
            if root not in target.parents:
                raise ValueError(f"Unsafe ZIP path: {info.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
            yield target, info.filename, {
                "archive_sha256": archive_hash,
                "entry_path": info.filename,
                "entry_crc32": f"{info.CRC:08x}",
                "entry_compressed_size": info.compress_size,
                "entry_uncompressed_size": info.file_size,
                "entry_timestamp_local_unspecified": "%04d-%02d-%02dT%02d:%02d:%02d" % info.date_time,
            }


def scan_pdf(path: Path, locator: str, zip_metadata: dict[str, Any] | None, dpi: int):
    raw = path.read_bytes()
    document_hash = sha256(raw)
    doc = fitz.open(path)
    metadata = {k: v for k, v in (doc.metadata or {}).items() if v not in (None, "")}
    xmp = ""
    try:
        xmp = doc.get_xml_metadata() or ""
    except Exception:
        pass
    token_counts = {name: len(re.findall(pattern, raw)) for name, pattern in TOKENS.items()}
    document = {
        "record_type": "document",
        "scanner_version": VERSION,
        "generated_utc": now(),
        "source_locator": locator,
        "source_name": path.name,
        "source_sha256": document_hash,
        "source_size": len(raw),
        "zip_metadata": zip_metadata,
        "pdf_header": raw[:16].decode("latin1", errors="replace"),
        "page_count": doc.page_count,
        "xref_length": doc.xref_length(),
        "is_encrypted": bool(doc.is_encrypted),
        "needs_password": bool(doc.needs_pass),
        "is_repaired": bool(doc.is_repaired),
        "permissions": int(doc.permissions),
        "metadata": metadata,
        "xmp_sha256": sha256(xmp.encode()) if xmp else None,
        "xmp_length": len(xmp),
        "pdf_token_counts": token_counts,
        "hf_local_routes_not_executed": HF_LOCAL_ROUTES,
        "boundary": BOUNDARY,
    }
    page_rows, image_rows, font_rows = [], [], []
    for index, page in enumerate(doc):
        rgb = render(page, dpi)
        tm = text_metrics(page)
        blocks = page.get_text("dict").get("blocks", [])
        full_image = any(
            block.get("type") == 1 and
            ((block["bbox"][2] - block["bbox"][0]) * (block["bbox"][3] - block["bbox"][1])) /
            max(page.rect.width * page.rect.height, 1) > 0.75
            for block in blocks if "bbox" in block
        )
        if full_image and tm["text_chars"] > 20:
            page_mode = "hybrid_full_page_image_plus_text"
        elif full_image:
            page_mode = "scan_only_or_raster_page"
        elif tm["text_chars"] > 20:
            page_mode = "native_or_vector_text"
        else:
            page_mode = "sparse_or_blank"
        page_rows.append({
            "record_type": "page",
            "document_sha256": document_hash,
            "source_locator": locator,
            "page_number": index + 1,
            "page_xref": page.xref,
            "rotation": page.rotation,
            "mediabox": list(page.mediabox),
            "cropbox": list(page.cropbox),
            "bleedbox": list(page.bleedbox),
            "trimbox": list(page.trimbox),
            "artbox": list(page.artbox),
            "page_mode": page_mode,
            "image_block_count": sum(1 for block in blocks if block.get("type") == 1),
            "widget_count": len(widgets(page)),
            "annotation_count": len(annotations(page)),
            "text_layer": tm,
            "raster": raster_metrics(rgb),
            "boundary": BOUNDARY,
        })
        image_rows.extend(image_inventory(doc, page, locator, index + 1))
        font_rows.extend(font_inventory(page, locator, index + 1))
    doc.close()
    return document, page_rows, image_rows, font_rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def build_summary(documents, pages, images, fonts, errors) -> dict[str, Any]:
    producers = Counter(doc.get("metadata", {}).get("producer", "") for doc in documents)
    modes = Counter(page["page_mode"] for page in pages)
    exact_pages: dict[str, list[dict[str, Any]]] = defaultdict(list)
    image_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for page in pages:
        exact_pages[page["raster"]["raster_sha256"]].append({"source_locator": page["source_locator"], "page_number": page["page_number"]})
    for image in images:
        if image.get("embedded_sha256"):
            image_groups[image["embedded_sha256"]].append({"source_locator": image["source_locator"], "page_number": image["page_number"], "xref": image.get("xref")})
    near = []
    for left_index, left in enumerate(pages):
        for right in pages[left_index + 1:]:
            if left["raster"]["raster_sha256"] == right["raster"]["raster_sha256"]:
                continue
            distance = hamming(left["raster"]["phash"], right["raster"]["phash"])
            if distance <= 8:
                near.append({"phash_hamming": distance,
                             "left": {"source_locator": left["source_locator"], "page_number": left["page_number"]},
                             "right": {"source_locator": right["source_locator"], "page_number": right["page_number"]}})
    return {
        "schema": "cvfs_v3_scan_summary/v1",
        "generated_utc": now(),
        "scanner_version": VERSION,
        "document_count": len(documents),
        "page_count": len(pages),
        "embedded_image_records": len(images),
        "font_records": len(fonts),
        "page_modes": dict(modes),
        "producer_clusters": producers.most_common(),
        "exact_duplicate_page_groups": [
            {"raster_sha256": key, "occurrences": value}
            for key, value in exact_pages.items() if len(value) > 1
        ],
        "near_duplicate_page_pairs": sorted(near, key=lambda row: row["phash_hamming"]),
        "cross_file_embedded_image_reuse": [
            {"embedded_sha256": key, "occurrences": value}
            for key, value in image_groups.items()
            if len({item["source_locator"] for item in value}) > 1
        ],
        "errors": errors,
        "hf_private_local_model_routes": HF_LOCAL_ROUTES,
        "boundary": BOUNDARY,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--out", required=True)
    parser.add_argument("--dpi", type=int, default=48)
    args = parser.parse_args()
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    documents, pages, images, fonts, errors = [], [], [], [], []
    for path, locator, zip_metadata in iter_sources(Path(args.input)):
        try:
            document, page_rows, image_rows, font_rows = scan_pdf(path, locator, zip_metadata, args.dpi)
            documents.append(document)
            pages.extend(page_rows)
            images.extend(image_rows)
            fonts.extend(font_rows)
            print(f"{locator}: {document['page_count']} pages", flush=True)
        except Exception as error:
            errors.append({"source_locator": locator, "error_type": type(error).__name__, "error": str(error)})
    summary = build_summary(documents, pages, images, fonts, errors)
    write_jsonl(output / "documents.jsonl", documents)
    write_jsonl(output / "pages.jsonl", pages)
    write_jsonl(output / "embedded_images.jsonl", images)
    write_jsonl(output / "fonts.jsonl", fonts)
    write_jsonl(output / "errors.jsonl", errors)
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
