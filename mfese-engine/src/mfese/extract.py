from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import fitz

from .schemas import DocumentRole, ExtractedItem


_AMOUNT_RE = re.compile(r"(?<![A-Za-z0-9])\$?\(?\s*((?:\d{1,3}(?:,\d{3})+)|\d+)(?:\.(\d{2}))?\s*\)?")
_DATE_RE = re.compile(r"\b(?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])[-/](?:\d{2}|\d{4})\b")
_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_ENVELOPE_RE = re.compile(r"\b[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\b", re.I)
_INVOICE_RE = re.compile(r"\b(?:invoice\s*(?:no\.?|number|#)?\s*)?([A-Z0-9]{4,}(?:-[A-Z0-9]{2,})+)\b", re.I)
_ACCOUNT_RE = re.compile(r"\b(?:account|acct\.?|loan)\s*(?:no\.?|number|#)?\s*[:#]?\s*([0-9]{6,})\b", re.I)
_ADDRESS_RE = re.compile(r"\b\d{2,6}\s+(?:[NSEW]\.?\s+)?\d{1,5}\s+(?:[NSEW]\.?|North|South|East|West)\b[^\n,]{0,45}", re.I)

ROLE_RULES: list[tuple[DocumentRole, tuple[str, ...], float]] = [
    (DocumentRole.DRAW_REQUEST, ("draw request", "amount requested", "construction loan administration"), 1.0),
    (DocumentRole.LINE_ITEM_TRANSFER, ("line item transfer", "budget decreases", "budget increases"), 1.0),
    (DocumentRole.PROPOSAL, ("proposal and agreement", "proposal", "quote expires", "acceptance"), 0.95),
    (DocumentRole.ESTIMATE, ("estimate", "quotation", "quote"), 0.85),
    (DocumentRole.INVOICE, ("invoice", "invoice total", "amount due", "bill to", "ship to"), 0.9),
    (DocumentRole.PAYMENT_INSTRUMENT, ("pay to the order", "check number", "endorsement", "memo"), 0.85),
    (DocumentRole.BANK_STATEMENT, ("beginning balance", "ending balance", "deposits", "withdrawals"), 0.9),
    (DocumentRole.LIEN_WAIVER, ("waiver and release", "lien waiver", "conditional waiver"), 0.95),
    (DocumentRole.DELIVERY_RECORD, ("delivery", "delivered", "packing slip", "received by"), 0.8),
    (DocumentRole.BUDGET, ("budget", "scheduled value", "balance to finish", "cost breakdown"), 0.75),
    (DocumentRole.CONTRACT, ("contract", "agreement", "purchase price", "scope of work"), 0.7),
    (DocumentRole.EMAIL, ("from:", "sent:", "to:", "subject:"), 0.9),
]


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\u00a0", " ").split())


def text_sha256(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8", errors="replace")).hexdigest()


def extract_text(path: Path) -> tuple[str, list[str]]:
    if path.suffix.lower() == ".pdf":
        doc = fitz.open(path)
        pages = [page.get_text("text") for page in doc]
        doc.close()
        return "\n\f\n".join(pages), pages
    return "", []


def classify_role(text: str, filename: str, hint: DocumentRole | None = None) -> list[dict[str, Any]]:
    haystack = f"{filename}\n{text[:100000]}".lower()
    scores: dict[DocumentRole, float] = {}
    reasons: dict[DocumentRole, list[str]] = {}
    if hint:
        scores[hint] = 1.2
        reasons[hint] = ["manifest role_hint"]
    for role, phrases, base in ROLE_RULES:
        hits = [phrase for phrase in phrases if phrase in haystack]
        if hits:
            score = min(1.0, base * (0.65 + 0.18 * len(hits)))
            if score > scores.get(role, 0):
                scores[role] = score
                reasons[role] = hits
    if not scores:
        scores[DocumentRole.UNKNOWN] = 0.1
        reasons[DocumentRole.UNKNOWN] = ["no role rule matched"]
    return [
        {"role": role.value, "score": round(score, 4), "reasons": reasons.get(role, [])}
        for role, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
    ]


def _money_value(match: re.Match[str]) -> float | None:
    whole, cents = match.group(1), match.group(2)
    try:
        value = float(whole.replace(",", "") + (f".{cents}" if cents else ""))
    except ValueError:
        return None
    if value < 1:
        return None
    token = match.group(0)
    if 1900 <= value <= 2100 and "$" not in token and "," not in token and cents is None:
        return None
    return value


def extract_items(text: str, pages: list[str]) -> list[ExtractedItem]:
    items: list[ExtractedItem] = []
    for page_number, page_text in enumerate(pages, start=1):
        for match in _AMOUNT_RE.finditer(page_text):
            value = _money_value(match)
            if value is not None:
                items.append(ExtractedItem(kind="amount", value=value, normalized=f"{value:.2f}", page=page_number, source_method="regex_text"))
        for match in _DATE_RE.finditer(page_text):
            items.append(ExtractedItem(kind="date", value=match.group(0), normalized=match.group(0), page=page_number, source_method="regex_text"))
        for match in _ISO_DATE_RE.finditer(page_text):
            items.append(ExtractedItem(kind="date", value=match.group(0), normalized=match.group(0), page=page_number, source_method="regex_text"))
        for match in _ENVELOPE_RE.finditer(page_text):
            items.append(ExtractedItem(kind="envelope_id", value=match.group(0).upper(), normalized=match.group(0).upper(), page=page_number, source_method="regex_text"))
        for match in _ACCOUNT_RE.finditer(page_text):
            items.append(ExtractedItem(kind="account_number", value=match.group(1), normalized=match.group(1), page=page_number, source_method="regex_text"))
        for match in _ADDRESS_RE.finditer(page_text):
            value = normalize_text(match.group(0))
            items.append(ExtractedItem(kind="address", value=value, normalized=value.lower(), page=page_number, source_method="regex_text"))
    if "invoice" in text.lower():
        for page_number, page_text in enumerate(pages, start=1):
            for match in _INVOICE_RE.finditer(page_text):
                token = match.group(1).upper()
                if any(char.isdigit() for char in token):
                    items.append(ExtractedItem(kind="invoice_number_candidate", value=token, normalized=token, page=page_number, source_method="regex_context"))
    return items
