"""
PlanTakeoff Forensic Engine
Date: 2026-07-07

Hybrid rule-based + AI-assisted construction plan takeoff framework.

This engine is intentionally conservative. It extracts plan text, sheet metadata,
scale/dimension candidates, schedule-like rows, and rough quantity clues. It then
produces confidence-tiered outputs for forensic review. It does not pretend to
replace a professional estimator.

Usage:
  python -m tools.plan_takeoff_forensic_engine.plan_takeoff_engine \
    --input ./plans \
    --comparators ./comparators \
    --output ./outputs/plan_takeoff_run

Optional:
  --allow_hf_downloads enables optional Hugging Face hooks where installed.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Iterable, Optional, Any


SOURCE_STATUS = {
    "SOURCE_CLOSED",
    "SOURCE_ROUTED",
    "BRIDGE_MISSING",
    "SOURCE_CONFLICT",
    "DERIVED_ONLY",
    "LEAD_ONLY",
    "QUARANTINE",
}

SHEET_KEYWORDS = {
    "cover": ["cover sheet", "sheet index", "general notes"],
    "plot": ["plot plan", "site plan", "lot size", "setback"],
    "basement": ["basement floor plan", "lower level", "foundation plan"],
    "main_floor": ["main floor plan", "main level floor plan", "first floor"],
    "framing": ["framing plan", "floor framing", "roof framing", "beam", "joist"],
    "roof": ["roof plan", "roof framing", "truss", "pitch"],
    "elevation": ["elevation", "exterior elevation"],
    "foundation": ["foundation", "footing", "wall schedule", "foundation wall"],
    "schedule": ["schedule", "door", "window", "beam schedule", "footing schedule"],
}

DIMENSION_RE = re.compile(
    r"(?P<feet>\d{1,4})\s*['’]\s*(?:[- ]?\s*(?P<inch>\d{1,2})(?:\s*(?P<num>\d{1,2})/(?P<den>\d{1,2}))?\s*(?:\"|in)?)?",
    re.IGNORECASE,
)
SCALE_RE = re.compile(
    r"(?:scale\s*[:=]?\s*)?(?P<left>\d+/?\d*|\d+\s*/\s*\d+)\s*(?:\"|in)?\s*=\s*(?P<right>\d+)\s*['’]",
    re.IGNORECASE,
)
AREA_RE = re.compile(r"(?P<value>\d{2,6}(?:\.\d+)?)\s*(?:sq\.?\s*ft|sf|square\s*feet)", re.IGNORECASE)
CY_RE = re.compile(r"(?P<value>\d{1,5}(?:\.\d+)?)\s*(?:cu\.?\s*yd|cuyd|cy|cubic\s*yard)", re.IGNORECASE)
MONEY_RE = re.compile(r"\$\s*(?P<value>[0-9,]+(?:\.\d{2})?)")


@dataclass
class SourceFile:
    path: str
    filename: str
    extension: str
    size_bytes: int
    sha256: str
    modified_iso: str


@dataclass
class SheetRecord:
    source_path: str
    page_number: Optional[int]
    sheet_id: str
    sheet_title: str
    sheet_type: str
    scale_candidates: list[str] = field(default_factory=list)
    source_status: str = "SOURCE_ROUTED"
    notes: str = ""


@dataclass
class DimensionCandidate:
    source_path: str
    page_number: Optional[int]
    raw_text: str
    feet_decimal: Optional[float]
    confidence: str
    source_status: str
    context: str


@dataclass
class QuantityEstimate:
    lane: str
    source_path: str
    page_number: Optional[int]
    quantity_type: str
    value: Optional[float]
    unit: str
    method: str
    confidence: str
    source_status: str
    required_native_closure: str
    notes: str


@dataclass
class ComparisonRow:
    item: str
    plan_value: Optional[float]
    billed_or_claimed_value: Optional[float]
    unit: str
    delta: Optional[float]
    percent_delta: Optional[float]
    source_status: str
    pressure_point: str
    required_closure: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_mtime(path: Path) -> str:
    return dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def discover_files(paths: list[Path]) -> list[SourceFile]:
    out: list[SourceFile] = []
    allowed = {".pdf", ".txt", ".md", ".csv", ".xlsx", ".xls", ".json", ".jsonl"}
    for root in paths:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in allowed:
                continue
            try:
                out.append(SourceFile(
                    path=str(p),
                    filename=p.name,
                    extension=p.suffix.lower(),
                    size_bytes=p.stat().st_size,
                    sha256=sha256_file(p),
                    modified_iso=safe_mtime(p),
                ))
            except OSError:
                continue
    return out


def extract_text_from_pdf(path: Path) -> list[tuple[int, str]]:
    """Return [(page_number, text)]. Uses pypdf if installed."""
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return [(None, "PDF text extraction unavailable: install pypdf")]
    try:
        reader = PdfReader(str(path))
        rows = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                rows.append((i, page.extract_text() or ""))
            except Exception as exc:
                rows.append((i, f"PAGE_TEXT_ERROR: {exc}"))
        return rows
    except Exception as exc:
        return [(None, f"PDF_READ_ERROR: {exc}")]


def extract_text(path: Path) -> list[tuple[Optional[int], str]]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    if ext in {".txt", ".md", ".csv", ".json", ".jsonl"}:
        try:
            return [(None, path.read_text(errors="ignore"))]
        except Exception as exc:
            return [(None, f"TEXT_READ_ERROR: {exc}")]
    return [(None, "Binary or spreadsheet file; parse separately or export to CSV for better extraction.")]


def classify_sheet(text: str, filename: str) -> tuple[str, str]:
    combined = f"{filename}\n{text}".lower()
    best_type = "unknown"
    best_hits = 0
    for sheet_type, terms in SHEET_KEYWORDS.items():
        hits = sum(1 for t in terms if t in combined)
        if hits > best_hits:
            best_type = sheet_type
            best_hits = hits
    title = ""
    for line in text.splitlines()[:30]:
        clean = " ".join(line.split())
        if len(clean) > 5 and any(k in clean.lower() for k in ["sheet", "plan", "foundation", "framing", "elevation"]):
            title = clean[:160]
            break
    if not title:
        title = Path(filename).stem[:160]
    return best_type, title


def find_scales(text: str) -> list[str]:
    candidates = []
    for m in SCALE_RE.finditer(text):
        candidates.append(m.group(0).strip())
    # Common textual scale flags.
    for line in text.splitlines():
        if "scale" in line.lower() and len(line) < 120:
            s = " ".join(line.split())
            if s not in candidates:
                candidates.append(s)
    return candidates[:20]


def feet_decimal_from_match(m: re.Match[str]) -> Optional[float]:
    try:
        feet = float(m.group("feet"))
        inch = float(m.group("inch") or 0)
        num = float(m.group("num") or 0)
        den = float(m.group("den") or 1)
        return feet + (inch + (num / den if den else 0)) / 12.0
    except Exception:
        return None


def context_window(text: str, start: int, end: int, width: int = 80) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    return " ".join(text[left:right].split())[:300]


def find_dimensions(source_path: str, page: Optional[int], text: str) -> list[DimensionCandidate]:
    out: list[DimensionCandidate] = []
    for m in DIMENSION_RE.finditer(text):
        raw = m.group(0).strip()
        # Filter obvious noise: a lone 2018' etc. Unusual huge values become low confidence.
        val = feet_decimal_from_match(m)
        confidence = "medium"
        status = "SOURCE_ROUTED"
        if val is None:
            confidence = "low"
            status = "DERIVED_ONLY"
        elif val > 400:
            confidence = "low"
            status = "LEAD_ONLY"
        elif val < 1:
            confidence = "low"
        out.append(DimensionCandidate(
            source_path=source_path,
            page_number=page,
            raw_text=raw,
            feet_decimal=val,
            confidence=confidence,
            source_status=status,
            context=context_window(text, m.start(), m.end()),
        ))
    return out[:500]


def infer_quantities(source_path: str, page: Optional[int], text: str, sheet_type: str) -> list[QuantityEstimate]:
    out: list[QuantityEstimate] = []
    for m in AREA_RE.finditer(text):
        value = float(m.group("value"))
        lane = "slab_flatwork_area" if sheet_type in {"foundation", "basement", "main_floor", "plot"} else "area_candidate"
        out.append(QuantityEstimate(
            lane=lane,
            source_path=source_path,
            page_number=page,
            quantity_type="area",
            value=value,
            unit="sf",
            method="regex_area_extraction_from_plan_text",
            confidence="medium",
            source_status="SOURCE_ROUTED",
            required_native_closure="Verify page, scale, label, and whether the area is plan area, room area, slab area, or note text.",
            notes=context_window(text, m.start(), m.end()),
        ))
    for m in CY_RE.finditer(text):
        value = float(m.group("value"))
        out.append(QuantityEstimate(
            lane="concrete_volume_candidate",
            source_path=source_path,
            page_number=page,
            quantity_type="volume",
            value=value,
            unit="cy",
            method="regex_cubic_yard_extraction_from_text",
            confidence="medium",
            source_status="SOURCE_ROUTED",
            required_native_closure="Verify whether number is plan-derived, ticket-derived, invoice-derived, or narrative comparison.",
            notes=context_window(text, m.start(), m.end()),
        ))
    # Dimension density can flag sheets that need manual takeoff.
    dims = list(DIMENSION_RE.finditer(text))
    if sheet_type in {"foundation", "basement", "main_floor", "plot"} and len(dims) >= 8:
        out.append(QuantityEstimate(
            lane="manual_takeoff_priority",
            source_path=source_path,
            page_number=page,
            quantity_type="dimension_density",
            value=float(len(dims)),
            unit="dimension_candidates",
            method="dimension_count_priority_flag",
            confidence="high",
            source_status="SOURCE_ROUTED",
            required_native_closure="Render page image, calibrate scale, and perform estimator/manual measurement or CAD extraction.",
            notes="High density of dimensions suggests this page is useful for manual/professional takeoff.",
        ))
    return out


def read_comparator_values(comparator_dir: Optional[Path]) -> dict[str, float]:
    """Very conservative comparator reader. Reads CSV text for simple lane,value rows."""
    values: dict[str, float] = {}
    if not comparator_dir or not comparator_dir.exists():
        return values
    for p in comparator_dir.rglob("*.csv"):
        try:
            with p.open(newline="", errors="ignore") as f:
                for row in csv.DictReader(f):
                    lane = row.get("lane") or row.get("item") or row.get("description")
                    val = row.get("value") or row.get("quantity") or row.get("amount")
                    if not lane or not val:
                        continue
                    try:
                        values[lane.strip()] = float(str(val).replace(",", "").replace("$", ""))
                    except ValueError:
                        continue
        except Exception:
            continue
    return values


def compare_quantities(estimates: list[QuantityEstimate], comparator_values: dict[str, float]) -> list[ComparisonRow]:
    rows: list[ComparisonRow] = []
    if not comparator_values:
        return rows
    for e in estimates:
        if e.value is None:
            continue
        for key, comp in comparator_values.items():
            if key.lower() in {e.lane.lower(), e.quantity_type.lower()} or e.lane.lower() in key.lower():
                delta = comp - e.value
                pct = (delta / e.value * 100.0) if e.value else None
                status = "SOURCE_CONFLICT" if pct is not None and abs(pct) > 20 else "SOURCE_ROUTED"
                pressure = "Comparator/billed value materially departs from plan-extracted candidate." if status == "SOURCE_CONFLICT" else "Comparator value requires native closure against plan/source method."
                rows.append(ComparisonRow(
                    item=key,
                    plan_value=e.value,
                    billed_or_claimed_value=comp,
                    unit=e.unit,
                    delta=delta,
                    percent_delta=pct,
                    source_status=status,
                    pressure_point=pressure,
                    required_closure="Verify scale, plan page, estimator method, invoice/draw/ticket source, and whether units match.",
                ))
    return rows


def write_csv(path: Path, rows: list[Any], fieldnames: Optional[list[str]] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        if fieldnames:
            with path.open("w", newline="") as f:
                csv.DictWriter(f, fieldnames=fieldnames).writeheader()
        return
    dict_rows = [asdict(r) if hasattr(r, "__dataclass_fields__") else dict(r) for r in rows]
    if fieldnames is None:
        fieldnames = list(dict_rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(dict_rows)


def build_report(output: Path, sources: list[SourceFile], sheets: list[SheetRecord], dims: list[DimensionCandidate], estimates: list[QuantityEstimate], comps: list[ComparisonRow]) -> str:
    now = dt.datetime.now().isoformat(timespec="seconds")
    priority = [e for e in estimates if e.lane == "manual_takeoff_priority"]
    conflicts = [c for c in comps if c.source_status == "SOURCE_CONFLICT"]
    routed = [e for e in estimates if e.source_status == "SOURCE_ROUTED"]
    lines = []
    lines.append("# Professional Takeoff Forensic Report")
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append("")
    lines.append("## Purpose")
    lines.append("This report is a litigation-support takeoff screen. It identifies plan pages, schedule/table candidates, dimension candidates, quantity candidates, and comparison flags. It does not replace a retained estimator or native CAD/manual takeoff.")
    lines.append("")
    lines.append("## Run Summary")
    lines.append(f"- Source files scanned: {len(sources)}")
    lines.append(f"- Sheet/page records indexed: {len(sheets)}")
    lines.append(f"- Dimension candidates: {len(dims)}")
    lines.append(f"- Quantity estimates/candidates: {len(estimates)}")
    lines.append(f"- Comparison rows: {len(comps)}")
    lines.append(f"- Source-conflict comparison rows: {len(conflicts)}")
    lines.append("")
    lines.append("## Highest Priority Manual Takeoff Pages")
    if priority:
        for e in priority[:20]:
            lines.append(f"- {Path(e.source_path).name} page {e.page_number}: {int(e.value or 0)} dimension candidates. {e.required_native_closure}")
    else:
        lines.append("- No high-density dimension pages identified from extracted text. Render plan pages and calibrate scale manually if PDFs are image-based.")
    lines.append("")
    lines.append("## Quantity Candidate Limits")
    lines.append("Any quantity extracted from text/OCR is SOURCE_ROUTED unless independently verified against the plan page, scale, dimensions, and estimator method. Image-based plan measurement requires rendering pages and manual/CAD/vision verification.")
    lines.append("")
    lines.append("## Source Conflict Flags")
    if conflicts:
        for c in conflicts[:25]:
            pct = "" if c.percent_delta is None else f" ({c.percent_delta:.1f}%)"
            lines.append(f"- {c.item}: plan candidate {c.plan_value} {c.unit}, billed/claimed {c.billed_or_claimed_value} {c.unit}, delta {c.delta}{pct}. {c.pressure_point}")
    else:
        lines.append("- No numeric source-conflict rows generated from available comparator CSV values. This does not mean none exist; comparator workbooks may need export/normalization.")
    lines.append("")
    lines.append("## Attorney-Safe Pressure Language")
    lines.append("The plan/takeoff engine identified plan-supported quantity candidates and source gaps. Where billed or drawn quantities exceed plan-supported ranges, the issue should be closed through native plans, estimator workpapers, vendor invoices, tickets, draw packets, and payment records. AI-derived or OCR-derived figures remain source-routed until manually verified.")
    report = "\n".join(lines)
    (output / "professional_takeoff_report.md").write_text(report, encoding="utf-8")
    return report


def run(args: argparse.Namespace) -> dict[str, Any]:
    input_paths = [Path(p) for p in args.input]
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    comparator_dir = Path(args.comparators) if args.comparators else None

    sources = discover_files(input_paths)
    sheet_records: list[SheetRecord] = []
    dim_records: list[DimensionCandidate] = []
    quantity_records: list[QuantityEstimate] = []

    for src in sources:
        path = Path(src.path)
        pages = extract_text(path)
        for page_num, text in pages:
            sheet_type, title = classify_sheet(text, src.filename)
            scales = find_scales(text)
            status = "SOURCE_ROUTED" if text and "unavailable" not in text.lower() else "DERIVED_ONLY"
            sheet_records.append(SheetRecord(
                source_path=src.path,
                page_number=page_num,
                sheet_id=f"{src.filename}::p{page_num or 'na'}",
                sheet_title=title,
                sheet_type=sheet_type,
                scale_candidates=scales,
                source_status=status,
                notes="Scale requires manual verification before measurement." if scales else "No scale found in extracted text; page render/manual calibration required.",
            ))
            dim_records.extend(find_dimensions(src.path, page_num, text))
            quantity_records.extend(infer_quantities(src.path, page_num, text, sheet_type))

    comparator_values = read_comparator_values(comparator_dir)
    comparisons = compare_quantities(quantity_records, comparator_values)

    write_csv(output / "plan_manifest.csv", sources)
    write_csv(output / "sheet_index.csv", sheet_records)
    write_csv(output / "dimension_candidates.csv", dim_records)
    write_csv(output / "quantity_estimates.csv", quantity_records)
    write_csv(output / "invoice_draw_comparison.csv", comparisons)

    confidence_flags = []
    for e in quantity_records:
        if e.source_status != "SOURCE_CLOSED":
            confidence_flags.append({
                "source_path": e.source_path,
                "page_number": e.page_number,
                "lane": e.lane,
                "quantity_type": e.quantity_type,
                "value": e.value,
                "unit": e.unit,
                "confidence": e.confidence,
                "source_status": e.source_status,
                "required_native_closure": e.required_native_closure,
            })
    write_csv(output / "takeoff_confidence_flags.csv", confidence_flags)

    report = build_report(output, sources, sheet_records, dim_records, quantity_records, comparisons)

    summary = {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "source_files": len(sources),
        "sheet_records": len(sheet_records),
        "dimension_candidates": len(dim_records),
        "quantity_estimates": len(quantity_records),
        "comparison_rows": len(comparisons),
        "outputs": [
            "plan_manifest.csv",
            "sheet_index.csv",
            "dimension_candidates.csv",
            "quantity_estimates.csv",
            "takeoff_confidence_flags.csv",
            "invoice_draw_comparison.csv",
            "professional_takeoff_report.md",
        ],
        "hf_enabled": bool(args.allow_hf_downloads),
        "caution": "AI/OCR-derived quantities are source-routed until manual/native takeoff closure.",
    }
    (output / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Forensic construction plan takeoff screen.")
    parser.add_argument("--input", nargs="+", required=True, help="Plan/source folders to scan.")
    parser.add_argument("--comparators", default=None, help="Optional folder with normalized comparator CSVs.")
    parser.add_argument("--output", required=True, help="Output folder.")
    parser.add_argument("--allow_hf_downloads", action="store_true", help="Placeholder flag for optional Hugging Face model hooks.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    result = run(parse_args())
    print(json.dumps(result, indent=2))
