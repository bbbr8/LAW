#!/usr/bin/env python3
"""Source-bound, branch-preserving case-review portal engine.

Native records control. Model outputs are DERIVED_ONLY candidates and cannot
self-promote to accepted findings.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable
import argparse, copy, hashlib, json, re, statistics, uuid


class SourceStatus(str, Enum):
    NATIVE_VERIFIED="NATIVE_VERIFIED"; CERTIFIED_COPY="CERTIFIED_COPY"
    SOURCE_EXTRACT="SOURCE_EXTRACT"; COPY="COPY"; OCR="OCR"; SUMMARY="SUMMARY"
    DERIVED_ONLY="DERIVED_ONLY"; INFERRED="INFERRED"; UNKNOWN="UNKNOWN"

class ReviewStatus(str, Enum):
    PROPOSED="PROPOSED"; ACCEPTED="ACCEPTED"; REJECTED="REJECTED"
    NEEDS_SOURCE="NEEDS_SOURCE"; DISPUTED="DISPUTED"; SUPERSEDED="SUPERSEDED"

class TruthStatus(str, Enum):
    PROVEN_TRUE="PROVEN_TRUE"; PROVEN_FALSE="PROVEN_FALSE"
    LIKELY_TRUE="LIKELY_TRUE"; LIKELY_FALSE="LIKELY_FALSE"
    MIXED="PARTLY_TRUE_MIXED"; UNRESOLVED="UNRESOLVED"; MISFRAMED="MISFRAMED"

class BranchStatus(str, Enum):
    SURVIVES="SURVIVES"; WEAKENED="WEAKENED"; DEFEATED="DEFEATED"; UNTESTED="UNTESTED"


def norm(v: Any) -> str:
    return re.sub(r"[^a-z0-9]+","_",str(v or "").strip().lower()).strip("_")

def parse_dt(v: str|None):
    if not v: return None
    try:
        d=datetime.fromisoformat(v.replace("Z","+00:00"))
        return d.replace(tzinfo=d.tzinfo or timezone.utc).astimezone(timezone.utc)
    except ValueError: return None

def mean(xs: Iterable[float], default=0.0):
    xs=list(xs); return statistics.mean(xs) if xs else default

def source_strength(s: SourceStatus):
    return {SourceStatus.NATIVE_VERIFIED:1,SourceStatus.CERTIFIED_COPY:.95,
      SourceStatus.SOURCE_EXTRACT:.8,SourceStatus.COPY:.72,SourceStatus.OCR:.62,
      SourceStatus.SUMMARY:.45,SourceStatus.DERIVED_ONLY:.3,
      SourceStatus.INFERRED:.2,SourceStatus.UNKNOWN:.15}.get(s,.15)

def enum_value(cls, value, default):
    try: return cls(value)
    except (ValueError,TypeError): return default

def ready(v):
    if isinstance(v,Enum): return v.value
    if isinstance(v,dict): return {k:ready(x) for k,x in v.items()}
    if isinstance(v,list): return [ready(x) for x in v]
    return v


@dataclass
class Anchor:
    anchor_id:str; record_id:str; exact_text:str=""
    document_id:str|None=None; page:int|None=None; bates_start:str|None=None
    bates_end:str|None=None; bbox:list[float]|None=None
    character_start:int|None=None; character_end:int|None=None
    extraction_method:str="native_text"; confidence:float=1.0
    def locatable(self): return bool(self.record_id and (self.page is not None or self.bates_start or self.exact_text))

@dataclass
class Claim:
    claim_id:str; subject_id:str; predicate:str; value:Any
    value_type:str="text"; scope:str="general"; effective_at:str|None=None
    asserted_at:str|None=None; source_record_id:str|None=None
    anchor_ids:list[str]=field(default_factory=list); confidence:float=1.0
    source_status:SourceStatus=SourceStatus.UNKNOWN
    review_status:ReviewStatus=ReviewStatus.PROPOSED
    qualifiers:dict[str,Any]=field(default_factory=dict)
    def key(self): return norm(self.subject_id),norm(self.predicate),norm(self.scope)
    def signature(self):
        if self.value_type=="money":
            try:return f"{float(self.value):.2f}"
            except (ValueError,TypeError):pass
        return json.dumps(self.value,sort_keys=True) if isinstance(self.value,(dict,list)) else str(self.value).strip().lower()

@dataclass
class Transaction:
    transaction_id:str; amount:float; date:str|None=None; payer:str|None=None
    payee:str|None=None; account_id:str|None=None; project_id:str|None=None
    lot_id:str|None=None; purpose:str|None=None; category:str|None=None
    source_record_id:str|None=None; anchor_ids:list[str]=field(default_factory=list)
    authorization_status:str="UNKNOWN"; credit_status:str="UNKNOWN"
    transaction_type:str="UNKNOWN"; metadata:dict[str,Any]=field(default_factory=dict)

@dataclass
class ModelCandidate:
    candidate_id:str; model_name:str; task:str; output:Any; confidence:float
    source_record_ids:list[str]; anchor_ids:list[str]=field(default_factory=list)
    model_revision:str|None=None; source_status:SourceStatus=SourceStatus.DERIVED_ONLY
    review_status:ReviewStatus=ReviewStatus.PROPOSED
    def violations(self):
        out=[]
        if self.source_status!=SourceStatus.DERIVED_ONLY:out.append("model output must enter as DERIVED_ONLY")
        if self.review_status==ReviewStatus.ACCEPTED:out.append("model cannot accept its own output")
        if not self.source_record_ids:out.append("model output must name source records")
        return out

@dataclass
class Record:
    record_id:str; text:str; source_family:str
    source_status:SourceStatus=SourceStatus.UNKNOWN; document_id:str|None=None
    created_at:str|None=None; received_at:str|None=None; event_at:str|None=None
    observed_at:str|None=None; litigation_used_at:str|None=None
    custodian:str|None=None; content_hash:str|None=None
    parent_record_id:str|None=None; related_record_ids:list[str]=field(default_factory=list)
    labels:list[str]=field(default_factory=list); metadata:dict[str,Any]=field(default_factory=dict)
    anchors:list[Anchor]=field(default_factory=list); claims:list[Claim]=field(default_factory=list)
    transactions:list[Transaction]=field(default_factory=list)
    model_candidates:list[ModelCandidate]=field(default_factory=list)
    def finalize(self):
        if not self.content_hash and self.text:
            self.content_hash=hashlib.sha256(self.text.encode()).hexdigest()
        return self

@dataclass
class Observation:
    observation_id:str; portal_id:str; statement:str; severity:str
    record_ids:list[str]; anchor_ids:list[str]=field(default_factory=list)
    tags:list[str]=field(default_factory=list); rule_id:str|None=None
    limitations:list[str]=field(default_factory=list)
    review_status:ReviewStatus=ReviewStatus.PROPOSED

@dataclass
class Branch:
    branch_id:str; hypothesis:str; expected_signals:list[str]
    falsifier:str; status:BranchStatus=BranchStatus.UNTESTED
    supporting_record_ids:list[str]=field(default_factory=list)
    contrary_record_ids:list[str]=field(default_factory=list)
    reopen_trigger:str="new native evidence"

@dataclass
class PortalResult:
    portal_id:str; observations:list[Observation]=field(default_factory=list)
    branches:list[Branch]=field(default_factory=list); bridge_records:list[str]=field(default_factory=list)
    opened_portals:list[str]=field(default_factory=list); metrics:dict[str,Any]=field(default_factory=dict)
    limitations:list[str]=field(default_factory=list)

@dataclass
class Report:
    run_id:str; generated_at:str; question:str; routed_portals:list[str]
    truth_status:TruthStatus; review_status:ReviewStatus; direct_answer:str
    portal_results:list[PortalResult]; open_variables:list[str]
    bridge_records:list[str]; reasoning_trace:list[dict[str,Any]]
    reopen_triggers:list[str]; model_policy_violations:list[dict[str,Any]]
    audit:dict[str,Any]
    def to_dict(self):return ready(asdict(self))


def obs(pid, statement, severity, records, tags=(), rule_id=None, limitations=()):
    return Observation(f"OBS-{uuid.uuid4().hex[:10]}",pid,statement,severity,
      [r.record_id for r in records],
      [a.anchor_id for r in records for a in r.anchors if a.locatable()],
      list(tags),rule_id,list(limitations))


class Portal:
    portal_id=""
    def run(self, question:str, records:list[Record], prior:dict[str,PortalResult])->PortalResult:
        raise NotImplementedError


class SourcePortal(Portal):
    portal_id="source_integrity"
    def run(self,q,rs,p):
        o=[]; b=[]
        weak=[r for r in rs if source_strength(r.source_status)<.6]
        no_anchor=[r for r in rs if not any(a.locatable() for a in r.anchors)]
        no_cust=[r for r in rs if not r.custodian]
        if weak:o.append(obs(self.portal_id,f"{len(weak)} weak/derived source record(s) need native closure.","HIGH",weak,["NATIVE_CLOSURE_REQUIRED"],"SRC-1"))
        if no_anchor:o.append(obs(self.portal_id,f"{len(no_anchor)} record(s) lack exact page/Bates/text anchors.","HIGH",no_anchor,["SOURCE_LOCATOR_GAP"],"SRC-2"))
        if no_cust:o.append(obs(self.portal_id,f"{len(no_cust)} record(s) lack an identified custodian.","MEDIUM",no_cust,["CUSTODIAN_GAP"],"SRC-3"))
        if weak:b.append("native/certified source behind each weak-source record")
        if no_anchor:b.append("exact page/Bates/text anchors for proof-facing claims")
        if no_cust:b.append("custodian and acquisition path")
        score=mean(.45*source_strength(r.source_status)+.2*bool(r.content_hash)+.2*any(a.locatable() for a in r.anchors)+.15*bool(r.custodian) for r in rs)
        return PortalResult(self.portal_id,o,bridge_records=b,opened_portals=["bridge_records"] if o else [],metrics={"source_integrity":round(score*100,2)})


class IdentityPortal(Portal):
    portal_id="identity_firewall"
    def run(self,q,rs,p):
        o=[]; b=[]; prefix=defaultdict(lambda:{"loans":set(),"rows":[]})
        for r in rs:
            px=norm(r.metadata.get("bates_prefix")); loan=norm(r.metadata.get("loan_id"))
            if px:
                prefix[px]["rows"].append(r)
                if loan:prefix[px]["loans"].add(loan)
        for px,x in prefix.items():
            if len(x["loans"])>1:
                o.append(obs(self.portal_id,f"Prefix {px} spans multiple loan identities: {sorted(x['loans'])}.","CRITICAL",x["rows"],["IDENTITY_FIREWALL"],"ID-1"))
        money=[r for r in rs if r.transactions]
        missing=[r for r in money if not any(r.metadata.get(k) for k in ("loan_id","lot_id","project_id","address"))]
        if missing:o.append(obs(self.portal_id,f"{len(missing)} money record(s) lack resolved loan/lot/project/address identity.","HIGH",missing,["MONEY_IDENTITY_GAP"],"ID-2"))
        if o:b.append("canonical borrower, loan, lot, project, address, account and Bates-family mapping")
        return PortalResult(self.portal_id,o,bridge_records=b,opened_portals=["money_flow"] if o else [],metrics={"identity_events":len(o)})


class TimelinePortal(Portal):
    portal_id="timeline_knowledge"
    def run(self,q,rs,p):
        o=[];b=[]
        after=[r for r in rs if parse_dt(r.event_at) and parse_dt(r.received_at) and parse_dt(r.received_at)>parse_dt(r.event_at)]
        later=[r for r in rs if parse_dt(r.event_at) and parse_dt(r.created_at) and parse_dt(r.created_at)>parse_dt(r.event_at) and any(x in r.text.lower() for x in ("because","explained","overage","everyone knew"))]
        missing=[r for r in rs if not parse_dt(r.event_at or r.created_at)]
        if after:o.append(obs(self.portal_id,f"{len(after)} record(s) were received after the event they may be used to explain.","HIGH",after,["KNOWLEDGE_TIME_GAP"],"TIME-1"))
        if later:o.append(obs(self.portal_id,f"{len(later)} explanation record(s) post-date the event.","MEDIUM",later,["POST_EVENT_EXPLANATION"],"TIME-2"))
        if missing:o.append(obs(self.portal_id,f"{len(missing)} record(s) lack a usable event/creation date.","MEDIUM",missing,["TIMELINE_GAP"],"TIME-3"))
        if after or later:b.append("event-time transmission, recipient, attachment and creation metadata")
        return PortalResult(self.portal_id,o,bridge_records=b,opened_portals=["claim_drift"] if later else [],metrics={"timeline_closure":round(100*(len(rs)-len(missing))/max(1,len(rs)),2)})


class MoneyPortal(Portal):
    portal_id="money_flow"
    def run(self,q,rs,p):
        o=[];b=[]; tx=[t for r in rs for t in r.transactions]; by={r.record_id:r for r in rs}
        owner=[t for t in tx if norm(t.transaction_type) in ("owner_advance","owner_payment")]
        draws=[t for t in tx if norm(t.transaction_type) in ("draw","bank_draw","lender_funding")]
        credit=[t for t in owner if norm(t.credit_status) in ("","unknown","unresolved")]
        cross=[t for t in tx if t.metadata.get("source_project_id") and t.project_id and norm(t.metadata["source_project_id"])!=norm(t.project_id)]
        dup=[]
        for a in owner:
            for d in draws:
                da,dd=parse_dt(a.date),parse_dt(d.date)
                gap=abs((dd-da).days) if da and dd else 99999
                same=(a.purpose and d.purpose and norm(a.purpose)==norm(d.purpose)) or (a.category and d.category and norm(a.category)==norm(d.category))
                if gap<=120 and same:dup.append((a,d))
        def rows(items):
            ids={t.source_record_id for t in items if t.source_record_id};return [by[i] for i in ids if i in by]
        if credit:o.append(obs(self.portal_id,f"{len(credit)} owner payment(s) lack closed credit/reimbursement treatment.","CRITICAL",rows(credit),["OWNER_ADVANCE","CREDIT_UNRESOLVED"],"MNY-1"))
        if cross:o.append(obs(self.portal_id,f"{len(cross)} transaction(s) have a project/lot mismatch.","CRITICAL",rows(cross),["CROSS_LOT"],"MNY-2"))
        if dup:o.append(obs(self.portal_id,f"{len(dup)} owner-payment/draw pair(s) share purpose/category within 120 days.","HIGH",rows([x for pair in dup for x in pair]),["PAYMENT_BEFORE_DRAW","SAME_DOLLAR_TEST"],"MNY-3"))
        if credit:b.append("final owner-credit ledger plus invoice, vendor payment and related draw")
        if cross:b.append("bank statement, vendor subledger, ship-to/delivery record and corrective entry")
        if dup:b.append("application tracing for each owner-payment/draw candidate")
        inflow=sum(t.amount for t in tx if norm(t.transaction_type) in ("owner_advance","owner_payment","draw","bank_draw","lender_funding","deposit"))
        outflow=sum(t.amount for t in tx if norm(t.transaction_type) in ("vendor_payment","wire_out","check","refund","transfer_out"))
        return PortalResult(self.portal_id,o,bridge_records=b,opened_portals=["authorization","contract_scope","bridge_records"] if o else [],metrics={"transactions":len(tx),"inflow":round(inflow,2),"outflow":round(outflow,2),"unresolved_modeled_balance":round(inflow-outflow,2),"duplicate_candidates":len(dup)},limitations=["Similarity opens a review lane; it is not proof of duplicate recovery."])


class ContractPortal(Portal):
    portal_id="contract_scope"
    def run(self,q,rs,p):
        o=[];b=[]; by={r.record_id:r for r in rs}; claims=[c for r in rs for c in r.claims]
        base=[c for c in claims if norm(c.predicate) in ("contract_amount","baseline_scope","included_scope","allowance")]
        revisions=[c for c in claims if norm(c.predicate)=="revised_budget" and not c.qualifiers.get("signed_by_owner")]
        missing=[c for c in claims if norm(c.predicate) in ("not_delivered","removed_scope") and bool(c.value)]
        if not base:o.append(obs(self.portal_id,"No controlling contract/baseline claim is present.","CRITICAL",rs[:1],["BASELINE_MISSING"],"SCP-1"))
        if revisions:
            rows=[by[c.source_record_id] for c in revisions if c.source_record_id in by]
            o.append(obs(self.portal_id,f"{len(revisions)} revised budget(s) lack recorded owner signature/authorization.","CRITICAL",rows,["BUDGET_LINEAGE","AUTHORIZATION_GAP"],"SCP-2"))
        if missing:
            rows=[by[c.source_record_id] for c in missing if c.source_record_id in by]
            o.append(obs(self.portal_id,f"{len(missing)} nondelivery/removal claim(s) require charge/draw/credit reconciliation.","HIGH",rows,["NONDELIVERED_SCOPE"],"SCP-3"))
        if not base:b.append("controlling signed agreement and incorporated baseline")
        if revisions:b.append("native revision, transmittal, signature, scope delta and removed-item credits")
        if missing:b.append("contract inclusion, funding, payment, cancellation/return and credit")
        return PortalResult(self.portal_id,o,bridge_records=b,opened_portals=["authorization","claim_drift"] if o else [],metrics={"baseline_claims":len(base),"unsigned_revisions":len(revisions),"nondelivered":len(missing)})


class AuthorizationPortal(Portal):
    portal_id="authorization"
    def run(self,q,rs,p):
        o=[];b=[];denied=[];unknown=[];unseen=[]
        for r in rs:
            s={norm(r.metadata.get("authorization_status")),norm(r.metadata.get("signature_status"))}
            s|={norm(c.value) for c in r.claims if norm(c.predicate) in ("authorization_status","signature_status")}
            if s&{"denied","forged","unauthorized","not_signed"}:denied.append(r)
            elif s&{"unknown","unverified","disputed"}:unknown.append(r)
            if r.metadata.get("owner_seen") is False:unseen.append(r)
        if denied:o.append(obs(self.portal_id,f"{len(denied)} record(s) carry denied/forged/unauthorized/not-signed status.","CRITICAL",denied,["UNAUTHORIZED","SIGNATURE_DISPUTE"],"AUTH-1"))
        if unknown:o.append(obs(self.portal_id,f"{len(unknown)} signature/authorization record(s) remain disputed or unverified.","HIGH",unknown,["AUTHORIZATION_OPEN"],"AUTH-2"))
        if unseen:o.append(obs(self.portal_id,f"{len(unseen)} record(s) are marked owner-unseen and cannot alone prove informed approval.","HIGH",unseen,["OWNER_UNSEEN"],"AUTH-3"))
        if denied or unknown:b.append("native artifact, audit trail, IP/device, transmission and witness foundation")
        if unseen:b.append("recipient headers, portal logs and contemporaneous owner communication")
        return PortalResult(self.portal_id,o,bridge_records=b,opened_portals=["legal_elements","bridge_records"] if o else [],metrics={"denied":len(denied),"unverified":len(unknown),"owner_unseen":len(unseen)})


class DriftPortal(Portal):
    portal_id="claim_drift"
    def run(self,q,rs,p):
        o=[];b=[]; by={r.record_id:r for r in rs};g=defaultdict(list)
        for r in rs:
            for c in r.claims:g[(norm(c.subject_id),norm(c.predicate))].append(c)
        for k,cs in g.items():
            vals={c.signature() for c in cs}
            if len(vals)>1:
                ids={c.source_record_id for c in cs if c.source_record_id};rows=[by[i] for i in ids if i in by]
                scopes={norm(c.scope) for c in cs}
                o.append(obs(self.portal_id,f"Claim drift for {k[0]} → {k[1]}: {sorted(vals)}; scopes={sorted(scopes)}.","HIGH" if len(scopes)==1 else "MEDIUM",rows,["CLAIM_DRIFT"],"DRIFT-1"))
        if o:b.append("claim/version register with wording, value, scope, effective date, author and approval")
        return PortalResult(self.portal_id,o,bridge_records=b,opened_portals=["contradiction","bridge_records"] if o else [],metrics={"drift_groups":len(o)})


class ContradictionPortal(Portal):
    portal_id="contradiction"
    def run(self,q,rs,p):
        o=[];b=[];branches=[];by={r.record_id:r for r in rs};g=defaultdict(list)
        for r in rs:
            for c in r.claims:g[c.key()].append(c)
        for k,cs in g.items():
            vals={c.signature() for c in cs}
            if len(vals)>1:
                ids={c.source_record_id for c in cs if c.source_record_id};rows=[by[i] for i in ids if i in by]
                fam={norm(by[i].source_family) for i in ids if i in by}
                o.append(obs(self.portal_id,f"Incompatible same-scope claims for {k}: {sorted(vals)}.","CRITICAL" if len(fam)>1 else "HIGH",rows,["TYPED_CONTRADICTION"],"CON-1"))
                branches.append(Branch(f"BR-{uuid.uuid4().hex[:8]}","Values reflect legitimate scope/stage differences.",["scope labels","version lineage","authorization","true-up"],"Same-scope same-time values remain incompatible after native reconciliation.",BranchStatus.UNTESTED,contrary_record_ids=sorted(ids)))
        if o:b.append("native scope, version, authorization and final reconciliation for each typed conflict")
        return PortalResult(self.portal_id,o,branches,b,["alternative_explanations"] if o else [],{"typed_conflicts":len(o)})


class AlternativePortal(Portal):
    portal_id="alternative_explanations"
    alternatives=[
      ("ordinary mistake",["prompt correction","consistent correction","no retained benefit"],"continued or selective use after notice"),
      ("timing difference",["stage labels","chronology","final true-up"],"same-scope same-time conflict"),
      ("legitimate change",["signed change","scope delta","price delta","transmission"],"no authorization or owner-unseen internal budget"),
      ("administrative reclassification",["crosswalk","no duplicate recovery","same final credit"],"changed burden or absent crosswalk"),
      ("credit or reimbursement",["credit ledger","reduced draw","refund","vendor application"],"no credit plus later same-category funding")]
    def run(self,q,rs,p):
        text=" ".join(r.text.lower() for r in rs);branches=[]
        for h,signals,falsifier in self.alternatives:
            hits=[s for s in signals if s in text]
            branches.append(Branch(f"BR-{uuid.uuid4().hex[:8]}",h,signals,falsifier,BranchStatus.SURVIVES if len(hits)>=2 else BranchStatus.UNTESTED,[r.record_id for r in rs] if hits else [],reopen_trigger="new record satisfying or defeating expected signals"))
        return PortalResult(self.portal_id,branches=branches,bridge_records=["preserve the strongest innocent/administrative explanation and its confirming/defeating record"],metrics={"branches":len(branches),"surviving":sum(b.status==BranchStatus.SURVIVES for b in branches)})


class BridgePortal(Portal):
    portal_id="bridge_records"
    expected={
      "OWNER_ADVANCE":["owner check/wire","vendor invoice","vendor payment application","related draw line","final owner-credit ledger"],
      "UNAUTHORIZED":["native signed artifact","signature audit trail","transmission","IP/device metadata","witness foundation"],
      "BUDGET_LINEAGE":["native version","author","transmittal","owner approval","scope/price delta"],
      "CROSS_LOT":["bank statement","vendor subledger","delivery/ship-to","corrective entry"],
      "NONDELIVERED_SCOPE":["contract inclusion","funding","payment","return/cancellation","credit/refund"]}
    def run(self,q,rs,p):
        tags={t for x in p.values() for ob in x.observations for t in ob.tags};expected=sorted({x for t in tags for x in self.expected.get(t,[])})
        present={norm(r.metadata.get("document_type")) for r in rs};missing=[x for x in expected if norm(x) not in present]
        o=[obs(self.portal_id,f"{len(missing)} expected bridge-record type(s) are not affirmatively present in this supplied corpus.","HIGH",rs[:1],["BRIDGE_MISSING"],"BRG-1",["corpus gap is not proof the record never existed"])] if missing else []
        return PortalResult(self.portal_id,o,bridge_records=missing,metrics={"expected":expected,"missing":missing,"bridge_closure":round(100*(len(expected)-len(missing))/max(1,len(expected)),2)})


class LegalPortal(Portal):
    portal_id="legal_elements"
    mapping={"OWNER_UNSEEN":["reliance/use","authorization","knowledge"],"TYPED_CONTRADICTION":["falsity","materiality"],"CLAIM_DRIFT":["falsity","knowledge/recklessness","intent"],"CROSS_LOT":["benefit/burden","causation","damages"],"CREDIT_UNRESOLVED":["injury","causation","damages"],"UNAUTHORIZED":["authorization","lender process","use"],"NONDELIVERED_SCOPE":["breach","causation","damages"]}
    def run(self,q,rs,p):
        by={r.record_id:r for r in rs};m=defaultdict(set)
        for x in p.values():
            for ob in x.observations:
                for t in ob.tags:
                    for e in self.mapping.get(t,[]):m[e]|=set(ob.record_ids)
        o=[obs(self.portal_id,f"Evidence-routing candidate for element '{e}' links {len(ids)} record(s).","INFO",[by[i] for i in ids if i in by],["LEGAL_ELEMENT_CANDIDATE"],"ELM-1",["mapping is not a legal conclusion"]) for e,ids in sorted(m.items())]
        return PortalResult(self.portal_id,o,metrics={"element_map":{k:sorted(v) for k,v in m.items()}},limitations=["Counsel controls legal sufficiency, defenses, admissibility and procedure."])


class EntropyPortal(Portal):
    portal_id="entropy_health"
    def run(self,q,rs,p):
        n=max(1,len(rs))
        context=mean(mean([bool(r.source_family),bool(r.event_at or r.created_at),bool(r.metadata.get("document_type")),bool(r.metadata.get("project_id") or r.metadata.get("loan_id") or r.metadata.get("lot_id")),bool(r.custodian)]) for r in rs)
        provenance=mean(.45*source_strength(r.source_status)+.2*bool(r.content_hash)+.2*any(a.locatable() for a in r.anchors)+.15*bool(r.custodian) for r in rs)
        graph=sum(bool(r.related_record_ids or r.parent_record_id) for r in rs)/n
        dated=sum(bool(parse_dt(r.event_at or r.created_at)) for r in rs)/n
        g=defaultdict(list)
        for r in rs:
            for c in r.claims:g[c.key()].append(c)
        comparable=[x for x in g.values() if len(x)>1];conf=sum(len({c.signature() for c in x})>1 for x in comparable)/max(1,len(comparable))
        br=p.get("bridge_records");closure=(br.metrics.get("bridge_closure",50)/100) if br else .5
        reconstruct=max(0,min(1,.25*context+.28*provenance+.12*graph+.15*(1-conf)+.1*dated+.1*closure));dissolve=1-reconstruct
        o=[]
        if dissolve>=.4:o.append(obs(self.portal_id,f"Information dissolution is {dissolve*100:.1f}%; this measures corpus condition, not liability.","CRITICAL" if dissolve>=.6 else "HIGH",rs[:1],["INFORMATION_DISSOLUTION"],"ENT-1"))
        return PortalResult(self.portal_id,o,metrics={"dissolution_index":round(dissolve*100,2),"reconstructability_index":round(reconstruct*100,2),"components":{"context":round(context*100,2),"provenance":round(provenance*100,2),"graph":round(graph*100,2),"conflict_pressure":round(conf*100,2),"timeline":round(dated*100,2),"bridge":round(closure*100,2)}},limitations=["Score describes the supplied information system, not misconduct or truth."])


PORTALS={x.portal_id:x for x in (SourcePortal,IdentityPortal,TimelinePortal,MoneyPortal,ContractPortal,AuthorizationPortal,DriftPortal,ContradictionPortal,AlternativePortal,BridgePortal,LegalPortal,EntropyPortal)}


class Engine:
    def __init__(self,registry=None):
        self.registry=registry or json.loads(Path(__file__).with_name("portal_registry.json").read_text())
    def route(self,q,rs,requested=()):
        corpus=(q+" "+" ".join(r.text for r in rs)).lower();chosen=set(self.registry["always_run"])|set(requested)
        for pid,s in self.registry["portals"].items():
            if any(k.lower() in corpus for k in s.get("keywords",[])):chosen.add(pid)
        changed=True
        while changed:
            changed=False
            for pid in list(chosen):
                for dep in self.registry["portals"].get(pid,{}).get("depends_on",[]):
                    if dep not in chosen:chosen.add(dep);changed=True
        return [x for x in self.registry["execution_order"] if x in chosen]
    def review(self,q,records,requested=()):
        rs=[copy.deepcopy(r).finalize() for r in records]
        if not rs:raise ValueError("at least one record required")
        if len({r.record_id for r in rs})!=len(rs):raise ValueError("record_id must be unique")
        prior={};queue=self.route(q,rs,requested);executed=[]
        while queue:
            pid=queue.pop(0)
            if pid in prior or pid not in PORTALS:continue
            result=PORTALS[pid]().run(q,rs,prior);prior[pid]=result;executed.append(pid)
            for opened in result.opened_portals:
                if opened not in prior and opened not in queue:queue.append(opened)
        for terminal in ("bridge_records","legal_elements","entropy_health"):
            prior[terminal]=PORTALS[terminal]().run(q,rs,prior)
            if terminal not in executed:executed.append(terminal)
        results=[prior[x] for x in executed];observations=[o for x in results for o in x.observations];branches=[b for x in results for b in x.branches]
        bridges=sorted({b for x in results for b in x.bridge_records})
        violations=[{"record_id":r.record_id,"candidate_id":c.candidate_id,"model":c.model_name,"errors":c.violations()} for r in rs for c in r.model_candidates if c.violations()]
        status=TruthStatus.UNRESOLVED if bridges or any(o.severity=="CRITICAL" for o in observations) or any(b.status==BranchStatus.UNTESTED for b in branches) else (TruthStatus.MIXED if any(o.severity=="HIGH" for o in observations) else TruthStatus.LIKELY_TRUE)
        lead=[o.statement for o in observations if o.severity=="CRITICAL"] or [o.statement for o in observations if o.severity=="HIGH"]
        answer=("The source-bound review identifies: "+" ".join(lead[:2])) if lead else "The supplied corpus does not yet support a closed answer."
        if bridges:answer+=f" Closure requires {len(bridges)} bridge-record/action item(s)."
        answer+=f" Current truth status: {status.value}."
        trace=[];step=1
        for x in results:
            for o in x.observations:
                trace.append({"step":step,"portal_id":x.portal_id,"observation_id":o.observation_id,"record_ids":o.record_ids,"anchor_ids":o.anchor_ids,"rule_id":o.rule_id,"statement":o.statement,"limitations":o.limitations});step+=1
        return Report(f"RUN-{uuid.uuid4().hex[:12]}",datetime.now(timezone.utc).isoformat(),q,executed,status,ReviewStatus.PROPOSED,answer,results,
          ["identity","time","money","scope/obligation","document status","actor state","process","alternative explanation","legal element"],
          bridges,trace,["new native evidence","changed identity","corrected amount","new version","new testimony","court or expert development"],violations,
          {"engine":"case-review-reasoning-portals","version":"1.0.0","records":len(rs),"claims":sum(len(r.claims) for r in rs),"transactions":sum(len(r.transactions) for r in rs),"observations":len(observations),"branches":len(branches),"control_rule":"Native/source records control; AI is assistive only."})


def record_from_dict(d):
    x=dict(d);x["source_status"]=enum_value(SourceStatus,x.get("source_status"),SourceStatus.UNKNOWN)
    x["anchors"]=[Anchor(**a) for a in x.get("anchors",[])]
    claims=[]
    for c in x.get("claims",[]):
        c=dict(c);c["source_status"]=enum_value(SourceStatus,c.get("source_status"),SourceStatus.UNKNOWN);c["review_status"]=enum_value(ReviewStatus,c.get("review_status"),ReviewStatus.PROPOSED);claims.append(Claim(**c))
    x["claims"]=claims;x["transactions"]=[Transaction(**t) for t in x.get("transactions",[])]
    candidates=[]
    for c in x.get("model_candidates",[]):
        c=dict(c);c["source_status"]=enum_value(SourceStatus,c.get("source_status"),SourceStatus.DERIVED_ONLY);c["review_status"]=enum_value(ReviewStatus,c.get("review_status"),ReviewStatus.PROPOSED);candidates.append(ModelCandidate(**c))
    x["model_candidates"]=candidates
    return Record(**x)

def load_case(path):
    d=json.loads(Path(path).read_text());return d.get("question","What does the evidence establish?"),[record_from_dict(x) for x in d.get("records",[])],d.get("options",{})

def main():
    ap=argparse.ArgumentParser();ap.add_argument("input");ap.add_argument("-o","--output",default="case_review_report.json");ap.add_argument("--portal",action="append",default=[]);a=ap.parse_args()
    q,rs,opt=load_case(a.input);report=Engine().review(q,rs,sorted(set(opt.get("requested_portals",[])+a.portal)));Path(a.output).write_text(json.dumps(report.to_dict(),indent=2));print(json.dumps(report.to_dict(),indent=2))
if __name__=="__main__":main()
