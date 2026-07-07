#!/usr/bin/env python3
"""
Case Control Engine

Deterministic evidence router for source closure, decision-pivot reliance, money buckets,
draw authorization, statement contradiction, discovery targets, exhibit cards, timeline state,
non-delivered scope, and bank/gatekeeper review.
"""
from __future__ import annotations

import argparse, csv, json, re, sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

DATE_RE = re.compile(r"\b(?:20\d{2}|19\d{2})[-/]\d{1,2}[-/]\d{1,2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b", re.I)
AMOUNT_RE = re.compile(r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\b")

LANES = {
    "contract_baseline": ["contract", "repc", "signed construction", "baseline", "791,456", "construction price", "cost breakdown"],
    "decision_pivot_reliance": ["other home", "already buying", "instead", "decided", "chose", "reliance", "relied", "pivot", "colby", "jeff", "suited", "investment pitch"],
    "semantic_conversion": ["estimate", "budget", "overage", "owner paid", "paid by owner", "upgrade", "nicer home", "same page", "allowance", "spec home", "converted", "recharacterized", "label"],
    "money_bucket": ["paid", "payment", "wire", "credit", "reimbursement", "draw", "invoice", "balance", "cash", "funded", "loan", "owed"],
    "draw_authorization": ["draw", "signature", "signed", "authorization", "funds control", "bank", "disbursement", "borrower", "approval", "layered"],
    "statement_contradiction": ["said", "claimed", "testified", "statement", "deposition", "email", "text", "contradict", "inconsistent", "conflict"],
    "non_delivered_scope": ["not delivered", "non-delivered", "solar", "pool", "fence", "outdoor kitchen", "motorized blinds", "water feature", "splash pad", "shop", "mancave", "landscaping", "suspended slab"],
    "bank_gatekeeper": ["bank", "fortis", "central bank", "lender", "wire", "loan", "draw", "funds control", "borrower authorization", "appraisal"],
    "public_record_pattern": ["entity", "property", "public record", "lien", "release", "affiliates", "lot", "title", "recorded"],
}

ELEMENTS = {
    "representation": ["told", "represented", "shown", "statement", "said", "agreed", "contract", "proposal", "offer", "appraisal", "same page"],
    "omission": ["not disclosed", "undisclosed", "omitted", "missing", "without", "not told", "not provided", "hidden"],
    "reliance": ["relied", "decided", "chose", "signed", "closed", "funded", "paid", "committed", "gave up", "instead"],
    "materiality": ["price", "cost", "loan", "debt", "risk", "lien", "title", "financing", "cash to close", "value"],
    "falsity_or_inconsistency": ["changed", "later", "conflict", "inconsistent", "different", "delta", "increase", "versus", "vs"],
    "causation": ["caused", "because", "therefore", "resulted", "funded", "wire", "draw", "closed", "signed"],
    "damages": ["damage", "loss", "owed", "balance", "credit", "reimbursement", "lien", "paid", "claim", "debt"],
    "knowledge_intent_pressure": ["pattern", "repeated", "benefit", "missing bridge", "no bridge", "without approval", "changed meaning"],
}

BUCKETS = {
    "land": ["land", "lot", "site"],
    "signed_construction": ["construction price", "signed construction", "contract", "repc", "baseline"],
    "loan_funded_draw": ["draw", "loan", "funded", "wire", "disbursement"],
    "owner_cash_advance": ["owner payment", "cash", "advance", "paid by bryce", "out of pocket"],
    "reimbursement_expected": ["reimbursement", "reimburse", "credit back", "bridge loan timing"],
    "vendor_invoice": ["invoice", "vendor", "subcontractor", "receipt"],
    "claimed_overage": ["overage", "extra", "upgrade", "nicer home"],
    "claimed_balance": ["balance", "owed", "final accounting", "claim"],
    "credit_owed_to_bryce": ["credit", "owner credit", "reimbursement", "offset"],
    "lien_title_payoff": ["lien", "title", "payoff", "release", "recorded"],
}

BRIDGE = {
    "contract_baseline": "Signed amendment, signed change order, authenticated owner-facing budget approval, and native workbook transmittal.",
    "decision_pivot_reliance": "Pre-pivot communication, original-home record, replacement-pitch record, value/cost representation, and record showing what Bryce gave up.",
    "semantic_conversion": "Native record proving the changed label was disclosed, authorized, and reconciled before being enforced against Bryce.",
    "money_bucket": "Payment ledger, bank record, invoice, proof of payment, owner-credit schedule, and reconciliation tying the money to the correct bucket.",
    "draw_authorization": "Native draw package, borrower authorization, email transmittal, signature metadata, funds-control approval, vendor support, and payment proof.",
    "statement_contradiction": "Exact statement, native record response, source conflict map, and deposition lock-in question.",
    "non_delivered_scope": "Scope representation, funding/payment proof, delivery proof, punch-list/warranty record, and credit/reduction ledger.",
    "bank_gatekeeper": "Loan-file draw package, bank review log, borrower authorization, disbursement record, appraisal/budget file, and exception notes.",
}

TIMELINE = [
    ("original_home_path", ["other home", "already buying", "original home"]),
    ("investment_or_replacement_pitch", ["investment pitch", "instead", "offer", "opportunity", "colby", "jeff"]),
    ("signed_baseline", ["repc", "contract", "signed construction", "791,456", "baseline"]),
    ("loan_appraisal_support", ["loan", "appraisal", "lender", "fortis", "ltv"]),
    ("owner_advances", ["owner payment", "advance", "cash", "reimbursement", "paid by bryce"]),
    ("draw_submissions", ["draw", "signature", "funds control", "disbursement"]),
    ("budget_expansion", ["budget", "1,339,826", "overage", "increase", "estimate"]),
    ("credit_confusion", ["credit", "reimbursement", "owner paid", "paid by owner"]),
    ("final_balance_claim", ["balance", "owed", "final accounting", "claim"]),
    ("litigation_use", ["deposition", "lawsuit", "litigation", "exhibit", "produced"]),
]

@dataclass
class Record:
    record_id: str
    text: str
    source: str = ""
    date: str = ""
    speaker: str = ""
    recipient: str = ""
    page: str = ""
    source_tier: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def clean(v: Any) -> str:
    if v is None: return ""
    if isinstance(v, str): return v.strip()
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def first(d: dict[str, Any], keys: list[str]) -> str:
    for k in keys:
        if d.get(k) not in (None, ""):
            return clean(d[k])
    return ""


def make_record(item: Any, idx: int, src: str) -> Record:
    if not isinstance(item, dict):
        return Record(str(idx), clean(item), src)
    text = first(item, ["text", "body", "content", "snippet", "statement", "description", "summary", "note", "message", "email_body"])
    if not text:
        text = json.dumps(item, ensure_ascii=False, sort_keys=True)
    return Record(
        first(item, ["id", "record_id", "bates", "doc_id", "exhibit"]) or str(idx),
        text,
        first(item, ["source", "file", "filename", "document", "title"]) or src,
        first(item, ["date", "sent_at", "created", "created_at", "timestamp"]),
        first(item, ["speaker", "from", "author", "sender"]),
        first(item, ["recipient", "to", "audience"]),
        first(item, ["page", "pages", "bates_page"]),
        first(item, ["source_tier", "tier", "proof_tier"]),
        item,
    )


def load_records(path: Path) -> list[Record]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()
    if ext == ".json":
        data = json.loads(raw)
        if isinstance(data, dict):
            for k in ["records", "items", "rows", "evidence", "results"]:
                if isinstance(data.get(k), list):
                    data = data[k]; break
            else: data = [data]
        return [make_record(x, i+1, path.name) for i, x in enumerate(data)]
    if ext == ".jsonl":
        return [make_record(json.loads(line), i+1, path.name) for i, line in enumerate(raw.splitlines()) if line.strip()]
    if ext == ".csv":
        return [make_record(row, i+1, path.name) for i, row in enumerate(csv.DictReader(raw.splitlines()))]
    chunks = [c.strip() for c in re.split(r"\n\s*\n", raw) if c.strip()]
    return [Record(str(i), c, path.name) for i, c in enumerate(chunks, 1)]


def detect(text: str, mapping: dict[str, list[str]]) -> list[str]:
    h = text.lower()
    return [label for label, terms in mapping.items() if any(t.lower() in h for t in terms)]


def status(rec: Record, lanes: list[str]) -> str:
    h = " ".join([rec.text, rec.source, rec.source_tier]).lower()
    if any(t in h for t in ["conflict", "inconsistent", "contradict", "different", "versus", "vs", "later changed"]):
        return "SOURCE_CONFLICT"
    native = any(t in h for t in ["native", ".msg", ".eml", "signed", "bank record", "wire", "invoice", "repc", "closing", "title", "metadata", "f0"])
    gap = any(t in h for t in ["missing", "no signed", "without approval", "bridge", "not provided", "undisclosed", "open"])
    if native and not gap:
        return "SOURCE_CLOSED"
    if gap or "semantic_conversion" in lanes or "draw_authorization" in lanes:
        return "BRIDGE_MISSING"
    if any(t in h for t in ["testified", "deposition", "statement", "claimed", "said"]):
        return "DEPOSITION_CLOSURE_NEEDED"
    if rec.source or rec.source_tier:
        return "SOURCE_ROUTED"
    return "DISCOVERY_TARGET"


def timeline(rec: Record) -> str:
    h = " ".join([rec.text, rec.source]).lower()
    for state, terms in TIMELINE:
        if any(t in h for t in terms):
            return state
    return "unassigned_state"


def bridge(lanes: list[str]) -> str:
    for lane in ["decision_pivot_reliance", "contract_baseline", "semantic_conversion", "money_bucket", "draw_authorization", "statement_contradiction", "non_delivered_scope", "bank_gatekeeper"]:
        if lane in lanes:
            return BRIDGE[lane]
    return "Native source verification and issue-specific bridge record."


def discovery(lanes: list[str], amounts: list[str]) -> str:
    amt = f" including amounts {', '.join(amounts)}" if amounts else ""
    if "decision_pivot_reliance" in lanes:
        return "Produce all pre-commitment communications, drafts, offers, comparative-home records, cost/value statements, financing representations, and records showing why Bryce entered this transaction instead of the original path."
    if "draw_authorization" in lanes:
        return "Produce the complete native draw package, borrower authorization, signature metadata, bank/funds-control transmittals, vendor invoices, payment proof, and owner notice records" + amt + "."
    if "semantic_conversion" in lanes:
        return "Produce every native record converting the earlier label/number into the later claimed obligation, including signed changes, owner approvals, workbook transmittals, and reconciliation records" + amt + "."
    if "money_bucket" in lanes:
        return "Produce ledger, bank records, vendor invoices, proof of payment, owner-credit schedule, and reconciliation proving the correct bucket and credit treatment" + amt + "."
    return "Produce the native source and bridge record required to support or disprove the routed issue."


def depo(lanes: list[str], amounts: list[str]) -> str:
    amt = f" for {', '.join(amounts)}" if amounts else ""
    if "decision_pivot_reliance" in lanes:
        return "Identify every statement, document, and figure you contend Bryce received before choosing the Jeff / Colby / Suited transaction instead of the home he was already buying."
    if "contract_baseline" in lanes or "semantic_conversion" in lanes:
        return "Identify the exact owner-signed document that authorized the claimed obligation above the signed baseline" + amt + "."
    if "draw_authorization" in lanes:
        return "Identify who submitted this draw, who authorized it, what native signature record exists, what bank/funds-control record approved it, and what vendor payment proves each line item" + amt + "."
    if "money_bucket" in lanes:
        return "Identify the bucket you assign this money to, who paid it, who received it, whether Bryce received credit, and the record proving that credit treatment" + amt + "."
    if "statement_contradiction" in lanes:
        return "State the factual basis for this statement and identify every document that supports or contradicts it."
    return "Identify the native source and bridge record that supports your version of this issue."


def plain(lanes: list[str]) -> str:
    if "decision_pivot_reliance" in lanes:
        return "This may explain why Bryce changed course and chose this transaction rather than the home he was already buying."
    if "semantic_conversion" in lanes:
        return "This may show a number or label changing meaning after Bryce was already committed."
    if "money_bucket" in lanes:
        return "This must be sorted into the correct money bucket before deciding whether Bryce was charged, credited, reimbursed, or exposed to a false balance."
    if "draw_authorization" in lanes:
        return "This tests whether money was requested or released with proper borrower authorization and support."
    if "statement_contradiction" in lanes:
        return "This converts a statement into a testable source issue."
    return "This record needs source-status review and bridge-record routing."


def route(rec: Record) -> dict[str, Any]:
    alltext = " ".join([rec.text, rec.source, rec.speaker, rec.recipient, rec.source_tier])
    lanes = detect(alltext, LANES) or ["manual_review"]
    elems = detect(alltext, ELEMENTS) or ["element_review_needed"]
    buckets = detect(alltext, BUCKETS)
    amounts = list(dict.fromkeys(AMOUNT_RE.findall(rec.text)))
    if amounts and not buckets: buckets = ["bucket_review_needed"]
    dates = list(dict.fromkeys(([rec.date] if rec.date else []) + DATE_RE.findall(rec.text)))
    st = status(rec, lanes)
    br = bridge(lanes)
    return {
        "record_id": rec.record_id,
        "source": rec.source,
        "date": rec.date or (dates[0] if dates else ""),
        "speaker": rec.speaker,
        "recipient": rec.recipient,
        "page": rec.page,
        "text": rec.text,
        "amounts": amounts,
        "dates": dates,
        "lanes": lanes,
        "fraud_elements": elems,
        "money_buckets": buckets,
        "timeline_state": timeline(rec),
        "source_status": st,
        "bridge_record_needed": br,
        "fraud_clarity_answer": f"Record supports these pressure lanes: {', '.join(lanes)}. Source status: {st}.",
        "plain_english_meaning": plain(lanes),
        "why_bryce_cared": "The record affects reliance, authorization, money, credit, risk, or damages depending on the routed lane.",
        "why_counsel_should_care": "Counsel can use this record to target source closure, deposition lock-in, or discovery production.",
        "discovery_target": discovery(lanes, amounts),
        "deposition_question": depo(lanes, amounts),
        "exhibit_card_title": f"{lanes[0].replace('_',' ').title()} — {rec.source or rec.record_id}",
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def quote(text: str, limit=850) -> str:
    text = text.strip()
    if len(text) > limit: text = text[:limit-20].rstrip() + " … [truncated]"
    return "\n".join("> " + line for line in text.splitlines())


def record_md(r: dict[str, Any]) -> str:
    return f"""## {r['exhibit_card_title']}

**Record ID:** {r['record_id']}  
**Source:** {r['source'] or 'Unknown'}  
**Date:** {r['date'] or 'Unknown'}  
**Speaker:** {r['speaker'] or 'Unknown'}  
**Recipient/Audience:** {r['recipient'] or 'Unknown'}  
**Page/Bates:** {r['page'] or 'Unknown'}  
**Source status:** {r['source_status']}  
**Lanes:** {', '.join(r['lanes'])}  
**Fraud elements:** {', '.join(r['fraud_elements'])}  
**Money buckets:** {', '.join(r['money_buckets']) if r['money_buckets'] else 'None detected'}  
**Amounts:** {', '.join(r['amounts']) if r['amounts'] else 'None detected'}  
**Timeline state:** {r['timeline_state']}

**Relevant text:**

{quote(r['text'])}

**Fraud-clarity answer:**  
{r['fraud_clarity_answer']}

**Plain-English meaning:**  
{r['plain_english_meaning']}

**Bridge record needed:**  
{r['bridge_record_needed']}

**Discovery target:**  
{r['discovery_target']}

**Deposition closure question:**  
{r['deposition_question']}

---
"""


def report(rows: list[dict[str, Any]]) -> str:
    counts = {}
    lanes = {}
    for r in rows:
        counts[r['source_status']] = counts.get(r['source_status'], 0) + 1
        for lane in r['lanes']:
            lanes[lane] = lanes.get(lane, 0) + 1
    parts = ["# Case Control System Report", "", f"Records reviewed: {len(rows)}", "", "## Source-status counts"]
    parts += [f"- {k}: {v}" for k, v in sorted(counts.items())]
    parts += ["", "## Lane counts"]
    parts += [f"- {k}: {v}" for k, v in sorted(lanes.items(), key=lambda kv: (-kv[1], kv[0]))]
    parts += ["", "---", ""]
    parts += [record_md(r) for r in rows]
    return "\n".join(parts)


def write_outputs(rows: list[dict[str, Any]], out: Path):
    out.mkdir(parents=True, exist_ok=True)
    (out / "routed_records.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    (out / "full_case_control_report.md").write_text(report(rows), encoding="utf-8")
    (out / "02_decision_pivot_binder.md").write_text("# Decision-Pivot Reliance Binder\n\n" + "\n".join(record_md(r) for r in rows if "decision_pivot_reliance" in r['lanes'] or r['timeline_state'] in ["original_home_path","investment_or_replacement_pitch"]), encoding="utf-8")
    (out / "06_discovery_targets.md").write_text("# Discovery Targets\n\n" + "\n".join(f"## {r['exhibit_card_title']}\n\n**Status:** {r['source_status']}\n\n**Bridge:** {r['bridge_record_needed']}\n\n**Request:** {r['discovery_target']}\n\n**Deposition:** {r['deposition_question']}\n" for r in rows), encoding="utf-8")
    (out / "07_exhibit_cards.md").write_text("# Exhibit Cards\n\n" + "\n".join(record_md(r) for r in rows), encoding="utf-8")
    (out / "08_timeline_state_machine.md").write_text("# Timeline State Machine\n\n" + "\n".join(f"- **{r['timeline_state']}** — {r['date'] or 'Unknown date'} — {r['plain_english_meaning']} Source status: {r['source_status']}." for r in rows), encoding="utf-8")
    write_csv(out / "01_source_closure_matrix.csv", rows, ["record_id","source","date","speaker","recipient","page","source_status","lanes","fraud_elements","bridge_record_needed","discovery_target","deposition_question"])
    write_csv(out / "03_money_bucket_reconciliation.csv", rows, ["record_id","source","date","amounts","money_buckets","source_status","plain_english_meaning","bridge_record_needed"])
    write_csv(out / "04_draw_authorization_validator.csv", [r for r in rows if "draw_authorization" in r['lanes'] or "bank_gatekeeper" in r['lanes']], ["record_id","source","date","amounts","source_status","bridge_record_needed","discovery_target","deposition_question"])
    write_csv(out / "05_statement_contradiction_ledger.csv", [r for r in rows if "statement_contradiction" in r['lanes'] or r['source_status'] == "SOURCE_CONFLICT"], ["record_id","source","date","speaker","recipient","source_status","fraud_clarity_answer","bridge_record_needed","deposition_question"])
    write_csv(out / "09_nondelivered_scope_ledger.csv", [r for r in rows if "non_delivered_scope" in r['lanes']], ["record_id","source","date","amounts","source_status","plain_english_meaning","bridge_record_needed","discovery_target"])
    (out / "10_bank_gatekeeper_lane.md").write_text("# Bank / Gatekeeper Lane\n\n" + "\n".join(record_md(r) for r in rows if "bank_gatekeeper" in r['lanes'] or "draw_authorization" in r['lanes']), encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--out-dir", type=Path, default=Path("case_control_out"))
    p.add_argument("--focus", choices=["pivot","money","draws","all"], default="all")
    args = p.parse_args(argv)
    if not args.input.exists():
        print(f"Input does not exist: {args.input}", file=sys.stderr); return 2
    rows = [route(r) for r in load_records(args.input)]
    write_outputs(rows, args.out_dir)
    print(f"Wrote {len(rows)} routed records to {args.out_dir}")
    print(f"Primary report: {args.out_dir / 'full_case_control_report.md'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
