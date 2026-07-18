#!/usr/bin/env python3
"""Generate privacy-safe synthetic construction-document vision fixtures.

The generator creates fictional invoice/draw pages, region annotations, expected
text, and controlled degradations. It never samples native case files or real
signatures. Use the output to compare layout/OCR models and to identify which
image conditions cause failures before applying a model to case material.

Optional dependency: Pillow (`python -m pip install pillow`).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import random
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
except ImportError as exc:  # pragma: no cover - handled by CLI
    raise SystemExit("Pillow is required: python -m pip install pillow") from exc

PAGE_WIDTH = 1700
PAGE_HEIGHT = 2200
MARGIN = 110
SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class Region:
    label: str
    bbox: tuple[int, int, int, int]
    text: str
    attributes: dict[str, Any]


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    seed: int
    document_type: str
    image_path: str
    parent_fixture_id: str | None
    transform: dict[str, Any]
    expected_fields: dict[str, str]
    regions: list[Region]
    image_sha256: str
    created_at: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_png(image: Image.Image, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    payload = buffer.getvalue()
    path.write_bytes(payload)
    return sha256_bytes(payload)


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def money(value: float) -> str:
    return f"${value:,.2f}"


def fake_date(rng: random.Random) -> str:
    year = rng.choice([2018, 2019, 2020])
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    return f"{month:02d}/{day:02d}/{year}"


def draw_text_region(
    draw: ImageDraw.ImageDraw,
    regions: list[Region],
    xy: tuple[int, int],
    text: str,
    *,
    label: str,
    text_font: ImageFont.ImageFont,
    attributes: dict[str, Any] | None = None,
) -> tuple[int, int, int, int]:
    bbox = draw.textbbox(xy, text, font=text_font)
    draw.text(xy, text, fill=0, font=text_font)
    regions.append(Region(label=label, bbox=bbox, text=text, attributes=attributes or {}))
    return bbox


def draw_abstract_signature(
    draw: ImageDraw.ImageDraw,
    rng: random.Random,
    box: tuple[int, int, int, int],
) -> None:
    """Draw a synthetic squiggle that is explicitly not based on a real signature."""
    x0, y0, x1, y1 = box
    width = x1 - x0
    height = y1 - y0
    points: list[tuple[float, float]] = []
    phases = rng.uniform(0, math.pi * 2)
    for i in range(40):
        t = i / 39
        x = x0 + width * t
        y = y0 + height * (0.5 + 0.28 * math.sin(10 * t + phases))
        y += rng.uniform(-height * 0.08, height * 0.08)
        points.append((x, y))
    draw.line(points, fill=20, width=4, joint="curve")
    draw.line([(x0 + width * 0.15, y1 - 8), (x1, y1 - 8)], fill=60, width=2)


def build_invoice(seed: int) -> tuple[Image.Image, dict[str, str], list[Region]]:
    rng = random.Random(seed)
    image = Image.new("L", (PAGE_WIDTH, PAGE_HEIGHT), color=255)
    draw = ImageDraw.Draw(image)
    regions: list[Region] = []

    vendor = rng.choice(["Synthetic Ridge Builders", "Example Peak Concrete", "Fictional Valley Millwork"])
    invoice_no = f"SYN-{rng.randint(10000, 99999)}"
    invoice_date = fake_date(rng)
    customer = "TEST OWNER — SYNTHETIC ONLY"
    project = f"LAB PROJECT {rng.randint(100, 999)}"

    draw_text_region(draw, regions, (MARGIN, 90), vendor, label="vendor_name", text_font=font(48, bold=True))
    draw_text_region(draw, regions, (MARGIN, 155), "PRIVACY-SAFE SYNTHETIC DOCUMENT", label="synthetic_banner", text_font=font(26, bold=True))
    draw_text_region(draw, regions, (1180, 95), "INVOICE", label="document_title", text_font=font(54, bold=True))
    draw_text_region(draw, regions, (1180, 175), invoice_no, label="invoice_number", text_font=font(30))
    draw_text_region(draw, regions, (1180, 220), invoice_date, label="invoice_date", text_font=font(30))

    draw.rectangle((MARGIN, 300, PAGE_WIDTH - MARGIN, 520), outline=0, width=3)
    draw_text_region(draw, regions, (MARGIN + 25, 330), "BILL TO", label="section_header", text_font=font(26, bold=True))
    draw_text_region(draw, regions, (MARGIN + 25, 380), customer, label="customer_name", text_font=font(30))
    draw_text_region(draw, regions, (MARGIN + 25, 430), project, label="project_name", text_font=font(30))

    table_top = 620
    row_h = 86
    columns = [MARGIN, 260, 1060, 1250, PAGE_WIDTH - MARGIN]
    headers = ["QTY", "DESCRIPTION", "UNIT", "AMOUNT"]
    for x in columns:
        draw.line((x, table_top, x, table_top + row_h * 7), fill=0, width=3)
    for row in range(8):
        y = table_top + row * row_h
        draw.line((MARGIN, y, PAGE_WIDTH - MARGIN, y), fill=0, width=3)
    for index, header in enumerate(headers):
        x = columns[index] + 18
        draw_text_region(draw, regions, (x, table_top + 24), header, label="table_header", text_font=font(25, bold=True), attributes={"column": index})

    descriptions = [
        "Footing and foundation labor",
        "Framing material package",
        "Electrical rough-in allowance",
        "Cabinet fabrication deposit",
        "Concrete flatwork",
        "Project supervision",
    ]
    quantities = [1, 1, rng.randint(4, 12), 1, rng.randint(80, 240), rng.randint(1, 3)]
    units = ["LS", "LS", "EA", "LS", "SF", "MO"]
    prices = [rng.uniform(4000, 60000) for _ in descriptions]
    total = 0.0
    for row_index, (description, qty, unit, unit_price) in enumerate(zip(descriptions, quantities, units, prices), start=1):
        amount = qty * unit_price
        total += amount
        y = table_top + row_index * row_h + 24
        cells = [str(qty), description, unit, money(amount)]
        for col_index, cell in enumerate(cells):
            x = columns[col_index] + 18
            draw_text_region(
                draw,
                regions,
                (x, y),
                cell,
                label="line_item_cell",
                text_font=font(23),
                attributes={"row": row_index, "column": col_index},
            )

    table_bottom = table_top + row_h * 7
    regions.append(Region("line_item_table", (MARGIN, table_top, PAGE_WIDTH - MARGIN, table_bottom), "", {"rows": 7, "columns": 4}))

    subtotal = total
    tax = subtotal * rng.choice([0.0, 0.047, 0.061])
    grand_total = subtotal + tax
    totals_x = 1040
    totals_y = table_bottom + 80
    for idx, (label, value) in enumerate([("SUBTOTAL", subtotal), ("TAX", tax), ("TOTAL", grand_total)]):
        y = totals_y + idx * 66
        draw_text_region(draw, regions, (totals_x, y), label, label="total_label", text_font=font(28, bold=label == "TOTAL"))
        draw_text_region(draw, regions, (1330, y), money(value), label="total_value", text_font=font(28, bold=label == "TOTAL"), attributes={"kind": label.lower()})

    signature_box = (MARGIN, 1660, 720, 1850)
    draw.rectangle(signature_box, outline=80, width=2)
    draw_abstract_signature(draw, rng, (MARGIN + 30, 1700, 680, 1805))
    regions.append(Region("synthetic_signature", signature_box, "", {"is_real_signature": False}))
    draw_text_region(draw, regions, (MARGIN, 1880), "Synthetic authorization mark — not a real signature", label="signature_disclaimer", text_font=font(22))

    stamp_box = (1120, 1660, 1510, 1900)
    draw.ellipse(stamp_box, outline=75, width=8)
    draw_text_region(draw, regions, (1180, 1740), "TEST ONLY", label="synthetic_stamp", text_font=font(42, bold=True), attributes={"is_real_stamp": False})

    expected_fields = {
        "vendor_name": vendor,
        "invoice_number": invoice_no,
        "invoice_date": invoice_date,
        "customer_name": customer,
        "project_name": project,
        "total": money(grand_total),
    }
    return image, expected_fields, regions


def apply_transform(image: Image.Image, rng: random.Random, transform_name: str) -> tuple[Image.Image, dict[str, Any]]:
    if transform_name == "clean":
        return image.copy(), {"name": "clean"}
    if transform_name == "rotate":
        angle = rng.uniform(-4.0, 4.0)
        return image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=255), {"name": "rotate", "angle_degrees": angle}
    if transform_name == "blur":
        radius = rng.uniform(0.8, 2.4)
        return image.filter(ImageFilter.GaussianBlur(radius)), {"name": "blur", "radius": radius}
    if transform_name == "low_contrast":
        factor = rng.uniform(0.35, 0.7)
        return ImageEnhance.Contrast(image).enhance(factor), {"name": "low_contrast", "factor": factor}
    if transform_name == "jpeg":
        quality = rng.randint(18, 48)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        return Image.open(buffer).convert("L"), {"name": "jpeg", "quality": quality}
    if transform_name == "occlusion":
        output = image.copy()
        draw = ImageDraw.Draw(output)
        width = rng.randint(180, 520)
        height = rng.randint(80, 220)
        x = rng.randint(MARGIN, PAGE_WIDTH - MARGIN - width)
        y = rng.randint(500, PAGE_HEIGHT - 350 - height)
        shade = rng.randint(215, 250)
        draw.rectangle((x, y, x + width, y + height), fill=shade)
        return output, {"name": "occlusion", "bbox": [x, y, x + width, y + height], "shade": shade}
    if transform_name == "shear":
        shear = rng.uniform(-0.035, 0.035)
        matrix = (1, shear, -shear * PAGE_HEIGHT / 2, 0, 1, 0)
        output = image.transform(image.size, Image.Transform.AFFINE, matrix, resample=Image.Resampling.BICUBIC, fillcolor=255)
        return output, {"name": "shear", "factor": shear}
    raise ValueError(f"unknown transform: {transform_name}")


def generate_dataset(output_dir: Path, count: int, seed: int, transforms: Sequence[str]) -> list[Fixture]:
    fixtures: list[Fixture] = []
    manifest_path = output_dir / "manifest.jsonl"
    output_dir.mkdir(parents=True, exist_ok=True)

    with manifest_path.open("w", encoding="utf-8") as manifest:
        for index in range(count):
            fixture_seed = seed + index
            base_image, expected_fields, regions = build_invoice(fixture_seed)
            base_id = f"syn_invoice_{fixture_seed:08d}"
            for variant_index, transform_name in enumerate(transforms):
                rng = random.Random((fixture_seed * 1009) + variant_index)
                transformed, transform = apply_transform(base_image, rng, transform_name)
                fixture_id = f"{base_id}_{transform_name}"
                image_path = output_dir / "images" / f"{fixture_id}.png"
                image_hash = save_png(transformed, image_path)
                fixture = Fixture(
                    fixture_id=fixture_id,
                    seed=fixture_seed,
                    document_type="synthetic_construction_invoice",
                    image_path=str(image_path),
                    parent_fixture_id=None if transform_name == "clean" else f"{base_id}_clean",
                    transform=transform,
                    expected_fields=expected_fields,
                    regions=regions,
                    image_sha256=image_hash,
                    created_at=utc_now(),
                )
                fixtures.append(fixture)
                record = asdict(fixture)
                record["schema_version"] = SCHEMA_VERSION
                record["evaluation_modes"] = ["page_classification", "field_ocr", "region_detection_on_clean"]
                record["privacy"] = {
                    "contains_native_case_data": False,
                    "contains_real_signature": False,
                    "synthetic_only": True,
                }
                manifest.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    return fixtures


def summarize(fixtures: Iterable[Fixture]) -> dict[str, Any]:
    fixture_list = list(fixtures)
    transforms: dict[str, int] = {}
    for fixture in fixture_list:
        name = str(fixture.transform.get("name", "unknown"))
        transforms[name] = transforms.get(name, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "fixture_count": len(fixture_list),
        "transforms": transforms,
        "privacy": {
            "native_case_files_used": False,
            "real_person_names_used": False,
            "real_signatures_used": False,
        },
    }


def parse_transforms(value: str) -> list[str]:
    allowed = {"clean", "rotate", "blur", "low_contrast", "jpeg", "occlusion", "shear"}
    result = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(result) - allowed)
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown transforms: {', '.join(unknown)}")
    if "clean" not in result:
        result.insert(0, "clean")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("synthetic_case_vision_dataset"))
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20260718)
    parser.add_argument(
        "--transforms",
        type=parse_transforms,
        default=parse_transforms("clean,rotate,blur,low_contrast,jpeg,occlusion,shear"),
        help="comma-separated transform list",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.count < 1 or args.count > 10_000:
        print("error: --count must be between 1 and 10000", file=sys.stderr)
        return 2
    try:
        fixtures = generate_dataset(args.output, args.count, args.seed, args.transforms)
        print(json.dumps(summarize(fixtures), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
