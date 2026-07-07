#!/usr/bin/env python3
"""
Fraud Clarity Router

Purpose:
    Convert evidence records into counsel-facing fraud-clarity review cards.

This script is intentionally conservative. It does not declare that fraud occurred.
It routes records to fraud-indicator categories and identifies reliance, semantic
conversion, authorization, damages, and bridge-record issues for counsel to evaluate.

Supported input:
    - JSON list of records
    - JSON object with "records", "items", "rows", or "evidence"
    - JSONL, one object per line
    - TXT / MD, one paragraph per record

Example:
    python scripts/fraud_clarity_router.py evidence.json --focus pivot --out fraud_review.md
    python scripts/fraud_clarity_router.py notes.txt --jsonl-out routed.jsonl --out routed.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


AMOUNT_RE = re.compile(r"\$?\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\b|\$\d+(?:\.\d{2})?")
DATE_RE = re.compile(
    r"\b(?:20\d{2}|19\d{2})[-/]\d{1,2}[-/]\d{1,2}\b|"
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)

KEYWORD_MAP: dict[str, list[str]] = {
    "representation": [
        "represented", "told", "said", "shown", "asked to sign", "same page",
        "agreed", "contract", "repc", "price", "cost breakdown", "budget",
        "estimate", "proposal", "offer", "value", "appraisal",
    ],
    "omission_or_nondisclosure": [
        "not disclosed", "undisclosed", "omitted", "missing", "without",
        "no approval", "no signed", "not told", "not provided", "hidden",
    ],
    "falsity_or_inconsistency": [
        "later", "changed", "inconsistent", "conflict", "versus", "vs",
        "delta", "increase", "overage", "recharacterized", "different",
    ],
    "materiality": [
        "loan", "closing", "financing", "borrower", "debt", "risk",
        "title", "lien", "price", "cost", "cash to close", "appraisal",
    ],
    "reliance": [
        "relied", "reliance", "decided", "chose", "instead", "pivot",
        "buy", "purchase", "build", "signed", "committed", "gave up",
        "other home", "already buying",
    ],
    "causation": [
        "caused", "because", "signed", "closed", "funded", "paid",
        "authorized", "draw", "released", "continued", "stayed",
    ],
    "damages_or_injury": [
        "owed", "balance", "damages", "credit", "reimbursement", "lien",
        "claim", "loss", "paid", "out of pocket", "cash", "debt",
    ],
    "bridge_record_needed": [
        "change order", "amendment", "owner approval", "signed approval",
        "invoice", "proof of payment", "ledger", "credit schedule",
        "reconciliation", "native workbook", "transmittal", "vendor proof",
    ],
    "semantic_conversion": [
        "estimate", "budget", "overage", "owner paid", "paid by owner",
        "nicer home", "upgrade", "allowance", "spec home", "same page",
        "recharacterized", "converted", "label",
    ],
    "draw_or_payment": [
        "draw", "wire", "payment", "bank", "funds control", "release",
        "disbursement", "invoice", "paid", "owner payment", "credit",
    ],
    "decision_pivot": [
        "other home", "already buying", "instead", "investment pitch",
        "jeff", "colby", "suited", "better", "safe", "safer", "upside",
        "decided to buy", "front borrower", "buyer/borrower",
    ],
}

BRIDGE_RECORD_DEFAULTS = {
    "representation": "Native owner-facing communication, signed agreement, REPC, cost breakdown, or authenticated transmittal.",
    "omission_or_nondisclosure": "Disclosure record showing the material fact was given to Bryce before commitment.",
    "falsity_or_inconsistency": "Native bridge record explaining the changed number or label.",
    "materiality": "Loan, appraisal, closing, title, or decision record showing the fact affected price, debt, risk, or commitment.",
    "reliance": "Pre-pivot communication or testimony tying the representation to Bryce's decision.",
    "causation": "Closing, payment, draw, signature, or funding record caused by the representation.",
    "damages_or_injury": "Payment ledger, bank record, draw ledger, invoice, lien notice, credit reconciliation, or claimed balance proof.",
    "bridge_record_needed": "Signed amendment, signed change order, owner approval, invoice, proof of payment, and credit reconciliation.",
    "semantic_conversion": "Record showing the changed label was disclosed, approved, and reconciled before enforcement.",
    "draw_or_payment": "Draw request, funds-control approval, payment proof, vendor invoice, and owner-credit ledger.",
    "decision_pivot": "Records showing the alternative home, what was offered instead, what Bryce relied on, and what he gave up.",
}


@dataclass
class EvidenceRecord:
    id: str
    text: str
    source: str = ""
    date: str = ""
    speaker: str = ""
    recipient: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutedRecord:
    record: EvidenceRecord
    categories: list[str]
    amounts: list[str]
    dates: list[str]
    source_tier: str
    fraud_clarity_answer: str
    plain_english_meaning: str
    why_bryce_cared: str
    why_counsel_should_care: str
    bridge_record_needed: str


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def first_present(mapping: dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return normalize_text(mapping[key])
    return ""


def load_records(path: Path) -> list[EvidenceRecord]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()

    if suffix == ".json":
        data = json.loads(raw)
        if isinstance(data, dict):
            for key in ("records", "items", "rows", "evidence", "results"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
            else:
                data = [data]
        if not isinstance(data, list):
            raise ValueError("JSON input must be a list or an object containing a records/items/rows/evidence/results list.")
        return [record_from_mapping(item, idx + 1, path.name) for idx, item in enumerate(data)]

    if suffix == ".jsonl":
        records: list[EvidenceRecord] = []
        for idx, line in enumerate(raw.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            records.append(record_from_mapping(json.loads(line), idx, path.name))
        return records

    # TXT / MD fallback: one paragraph per record.
    chunks = [c.strip() for c in re.split(r"\n\s*\n", raw) if c.strip()]
    return [
        EvidenceRecord(id=str(idx), text=chunk, source=path.name)
        for idx, chunk in enumerate(chunks, start=1)
    ]


def record_from_mapping(item: Any, idx: int, default_source: str) -> EvidenceRecord:
    if not isinstance(item, dict):
        return EvidenceRecord(id=str(idx), text=normalize_text(item), source=default_source)

    text = first_present(item, [
        "text", "body", "content", "snippet", "statement", "description",
        "summary", "note", "message", "email_body",
    ])
    if not text:
        # Preserve the whole mapping if no obvious text field exists.
        text = json.dumps(item, ensure_ascii=False, sort_keys=True)

    return EvidenceRecord(
        id=first_present(item, ["id", "record_id", "bates", "doc_id"]) or str(idx),
        text=text,
        source=first_present(item, ["source", "file", "filename", "document", "title"]) or default_source,
        date=first_present(item, ["date", "sent_at", "created", "created_at", "timestamp"]),
        speaker=first_present(item, ["speaker", "from", "author", "sender"]),
        recipient=first_present(item, ["recipient", "to", "audience"]),
        metadata=item,
    )


def classify_source_tier(record: EvidenceRecord) -> str:
    haystack = " ".join([record.source, record.text]).lower()
    if any(term in haystack for term in ["native", ".msg", ".eml", "signed", "bank", "wire", "invoice", "repc", "closing", "title"]):
        return "F0/native candidate"
    if any(term in haystack for term in ["ocr", "extract", "parsed", "export", "transcript", "bates"]):
        return "F1/extracted source"
    if any(term in haystack for term in ["analysis", "calculation", "timeline", "delta", "summary"]):
        return "F2/analysis"
    return "Open/source tier needs verification"


def classify_record(record: EvidenceRecord, focus: str | None = None) -> RoutedRecord:
    haystack = " ".join([
        record.text, record.source, record.date, record.speaker, record.recipient
    ]).lower()

    categories: list[str] = []
    for category, terms in KEYWORD_MAP.items():
        if any(term in haystack for term in terms):
            categories.append(category)

    if focus:
        focus = focus.lower()
        if focus == "pivot" and "decision_pivot" not in categories:
            if any(term in haystack for term in KEYWORD_MAP["decision_pivot"]):
                categories.append("decision_pivot")
        elif focus == "money" and "draw_or_payment" not in categories:
            if any(term in haystack for term in KEYWORD_MAP["draw_or_payment"]):
                categories.append("draw_or_payment")

    amounts = AMOUNT_RE.findall(record.text)
    dates = DATE_RE.findall(record.text)
    if record.date:
        dates.insert(0, record.date)

    source_tier = classify_source_tier(record)
    bridge_record_needed = choose_bridge_record(categories)

    return RoutedRecord(
        record=record,
        categories=categories or ["needs_manual_review"],
        amounts=amounts,
        dates=list(dict.fromkeys(dates)),
        source_tier=source_tier,
        fraud_clarity_answer=build_fraud_clarity_answer(categories),
        plain_english_meaning=build_plain_english_meaning(record, categories, amounts),
        why_bryce_cared=build_why_bryce_cared(categories, amounts),
        why_counsel_should_care=build_why_counsel_should_care(categories),
        bridge_record_needed=bridge_record_needed,
    )


def choose_bridge_record(categories: list[str]) -> str:
    if not categories:
        return "Native source verification and issue-specific bridge record."
    priority = [
        "decision_pivot", "semantic_conversion", "draw_or_payment", "damages_or_injury",
        "reliance", "falsity_or_inconsistency", "omission_or_nondisclosure",
        "representation", "bridge_record_needed",
    ]
    for category in priority:
        if category in categories:
            return BRIDGE_RECORD_DEFAULTS[category]
    return "; ".join(BRIDGE_RECORD_DEFAULTS[c] for c in categories[:3] if c in BRIDGE_RECORD_DEFAULTS)


def build_fraud_clarity_answer(categories: list[str]) -> str:
    if not categories:
        return "This record needs manual review before assigning a fraud-clarity category."

    readable = ", ".join(c.replace("_", " ") for c in categories)
    return (
        f"This record implicates: {readable}. Counsel should evaluate whether it supports "
        "misrepresentation, omission, reliance, semantic conversion, unauthorized cost shift, "
        "damages, or bridge-record pressure."
    )


def build_plain_english_meaning(record: EvidenceRecord, categories: list[str], amounts: list[str]) -> str:
    amount_part = f" It includes figure(s): {', '.join(amounts)}." if amounts else ""
    if "decision_pivot" in categories:
        return (
            "This may help explain why Bryce chose the Jeff / Colby / Suited path instead of "
            f"the home he was already buying.{amount_part}"
        )
    if "semantic_conversion" in categories:
        return (
            "This may show a label or number changing meaning, such as contract price becoming "
            f"budget, estimate, overage, or owner-paid debt.{amount_part}"
        )
    if "draw_or_payment" in categories:
        return (
            "This may connect a representation to money movement, draw authorization, payment proof, "
            f"or credit treatment.{amount_part}"
        )
    return (
        "This record may shape what Bryce understood, what later changed, and what proof link is still needed."
        + amount_part
    )


def build_why_bryce_cared(categories: list[str], amounts: list[str]) -> str:
    money = f" The amount(s) {', '.join(amounts)} should be decoded into land, construction, loan, owner payment, credit, or claimed debt buckets." if amounts else ""
    if "decision_pivot" in categories or "reliance" in categories:
        return (
            "This mattered because reliance begins at the commitment decision, not just at final accounting."
            + money
        )
    if "materiality" in categories:
        return (
            "This mattered because the fact could affect price, debt, financing, title risk, or whether Bryce would proceed."
            + money
        )
    if "damages_or_injury" in categories or "draw_or_payment" in categories:
        return (
            "This mattered because it could affect money Bryce paid, credit he should receive, debt claimed against him, or lien/title exposure."
            + money
        )
    return "This mattered if it affected Bryce's understanding, authorization, payment decision, or risk at the time."


def build_why_counsel_should_care(categories: list[str]) -> str:
    if "bridge_record_needed" in categories or "semantic_conversion" in categories:
        return (
            "Counsel should test whether the adverse version has the authenticated bridge records needed "
            "to convert the earlier representation into the later claimed obligation."
        )
    if "decision_pivot" in categories:
        return (
            "Counsel should test inducement and reliance: what Bryce was told before giving up the alternative path."
        )
    if "draw_or_payment" in categories:
        return (
            "Counsel should test authorization, vendor proof, payment proof, and credit reconciliation."
        )
    return (
        "Counsel should determine whether the record is a native source, an extracted source, an analysis point, "
        "or an open proof gap."
    )


def markdown_card(routed: RoutedRecord) -> str:
    r = routed.record
    lines = [
        f"## Record {r.id}",
        "",
        f"**Source:** {r.source or 'Unknown'}",
        f"**Date:** {', '.join(routed.dates) if routed.dates else (r.date or 'Unknown')}",
        f"**Speaker:** {r.speaker or 'Unknown'}",
        f"**Recipient/Audience:** {r.recipient or 'Unknown'}",
        f"**Source tier:** {routed.source_tier}",
        f"**Categories:** {', '.join(routed.categories)}",
        f"**Amounts:** {', '.join(routed.amounts) if routed.amounts else 'None detected'}",
        "",
        "**Relevant text:**",
        "",
        blockquote(trim_text(r.text, 1200)),
        "",
        "**Fraud-clarity answer:**",
        routed.fraud_clarity_answer,
        "",
        "**Plain-English meaning:**",
        routed.plain_english_meaning,
        "",
        "**Why Bryce cared at the time:**",
        routed.why_bryce_cared,
        "",
        "**Why counsel should care now:**",
        routed.why_counsel_should_care,
        "",
        "**Bridge record needed:**",
        routed.bridge_record_needed,
        "",
    ]
    return "\n".join(lines)


def blockquote(text: str) -> str:
    return "\n".join("> " + line for line in text.splitlines())


def trim_text(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + " … [truncated]"


def render_markdown(routed_records: list[RoutedRecord], title: str) -> str:
    count_by_category: dict[str, int] = {}
    for routed in routed_records:
        for cat in routed.categories:
            count_by_category[cat] = count_by_category.get(cat, 0) + 1

    category_lines = "\n".join(
        f"- {cat}: {count}"
        for cat, count in sorted(count_by_category.items(), key=lambda kv: (-kv[1], kv[0]))
    )

    header = f"""# {title}

Generated by `fraud_clarity_router.py`.

## Summary

- Records reviewed: {len(routed_records)}
- This report routes fraud indicators; it does not make legal conclusions.
- Every figure should be separately decoded into land, construction, loan, draw, owner payment, credit, and claimed-debt buckets.
- Every adverse explanation should be tested against the bridge record that should exist if it is true.

## Category counts

{category_lines or "- No categories detected."}

---
"""
    return header + "\n\n".join(markdown_card(r) for r in routed_records)


def write_jsonl(routed_records: list[RoutedRecord], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for rr in routed_records:
            payload = {
                "id": rr.record.id,
                "source": rr.record.source,
                "date": rr.record.date,
                "speaker": rr.record.speaker,
                "recipient": rr.record.recipient,
                "categories": rr.categories,
                "amounts": rr.amounts,
                "dates": rr.dates,
                "source_tier": rr.source_tier,
                "fraud_clarity_answer": rr.fraud_clarity_answer,
                "plain_english_meaning": rr.plain_english_meaning,
                "why_bryce_cared": rr.why_bryce_cared,
                "why_counsel_should_care": rr.why_counsel_should_care,
                "bridge_record_needed": rr.bridge_record_needed,
                "text": rr.record.text,
            }
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route evidence records into fraud-clarity review cards.")
    parser.add_argument("input", type=Path, help="Input evidence file: .json, .jsonl, .txt, or .md")
    parser.add_argument("--out", type=Path, default=Path("fraud_clarity_review.md"), help="Markdown output path")
    parser.add_argument("--jsonl-out", type=Path, default=None, help="Optional JSONL output path")
    parser.add_argument("--focus", choices=["pivot", "money"], default=None, help="Optional routing focus")
    parser.add_argument("--title", default="Fraud Clarity Routed Evidence Review", help="Markdown report title")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if not args.input.exists():
        print(f"Input file does not exist: {args.input}", file=sys.stderr)
        return 2

    try:
        records = load_records(args.input)
        routed = [classify_record(record, focus=args.focus) for record in records]
        args.out.write_text(render_markdown(routed, args.title), encoding="utf-8")
        if args.jsonl_out:
            write_jsonl(routed, args.jsonl_out)
    except Exception as exc:
        print(f"Failed to route records: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote Markdown report: {args.out}")
    if args.jsonl_out:
        print(f"Wrote JSONL report: {args.jsonl_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
