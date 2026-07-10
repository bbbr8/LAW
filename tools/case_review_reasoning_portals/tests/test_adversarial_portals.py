from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from case_review_portals import (
    Anchor,
    Claim,
    Engine,
    ModelCandidate,
    Record,
    ReviewStatus,
    SourceStatus,
    Transaction,
)


def portal(report, portal_id):
    return next(result for result in report.portal_results if result.portal_id == portal_id)


def anchored(record_id, *, created_at="2024-01-01", related=None):
    return Record(
        record_id=record_id,
        text=f"Source record {record_id}",
        source_family="independent source",
        source_status=SourceStatus.NATIVE_VERIFIED,
        document_id=f"DOC-{record_id}",
        created_at=created_at,
        event_at=created_at,
        custodian="custodian",
        related_record_ids=related or [],
        metadata={"document_type": "native record", "project_id": "P1"},
        anchors=[Anchor(
            anchor_id=f"ANC-{record_id}",
            record_id=record_id,
            exact_text=f"Source record {record_id}",
            document_id=f"DOC-{record_id}",
            page=1,
        )],
    )


def test_draw_before_owner_payment_is_not_payment_before_draw():
    owner = anchored("OWNER")
    owner.transactions = [Transaction(
        transaction_id="TX-OWNER",
        amount=1000,
        date="2024-02-01",
        project_id="P1",
        lot_id="L1",
        purpose="framing",
        category="framing",
        source_record_id="OWNER",
        transaction_type="OWNER_ADVANCE",
        credit_status="RESOLVED",
    )]
    draw = anchored("DRAW")
    draw.transactions = [Transaction(
        transaction_id="TX-DRAW",
        amount=1000,
        date="2024-01-01",
        project_id="P1",
        lot_id="L1",
        purpose="framing",
        category="framing",
        source_record_id="DRAW",
        transaction_type="DRAW",
    )]
    report = Engine().review(
        "Did an owner payment precede a same-category draw?",
        [owner, draw],
        requested=["money_flow"],
    )
    assert portal(report, "money_flow").metrics["duplicate_candidates"] == 0


def test_different_scopes_do_not_create_typed_conflict():
    requested = anchored("REQUEST")
    requested.claims = [Claim(
        claim_id="C1",
        subject_id="DRAW-3",
        predicate="amount",
        value=100,
        value_type="money",
        scope="requested",
        source_record_id="REQUEST",
        source_status=SourceStatus.NATIVE_VERIFIED,
    )]
    funded = anchored("FUNDED")
    funded.claims = [Claim(
        claim_id="C2",
        subject_id="DRAW-3",
        predicate="amount",
        value=90,
        value_type="money",
        scope="funded",
        source_record_id="FUNDED",
        source_status=SourceStatus.NATIVE_VERIFIED,
    )]
    report = Engine().review(
        "Are requested and funded amounts contradictory?",
        [requested, funded],
        requested=["contradiction"],
    )
    assert portal(report, "contradiction").metrics["typed_conflicts"] == 0


def test_self_accepted_model_candidate_is_audited():
    record = anchored("MODEL")
    record.model_candidates = [ModelCandidate(
        candidate_id="MC-1",
        model_name="test/model",
        model_revision="1",
        task="classification",
        output={"label": "accepted"},
        confidence=0.99,
        source_record_ids=["MODEL"],
        anchor_ids=["ANC-MODEL"],
        source_status=SourceStatus.DERIVED_ONLY,
        review_status=ReviewStatus.ACCEPTED,
    )]
    report = Engine().review("Review model policy.", [record])
    assert report.model_policy_violations
    assert "cannot accept" in " ".join(report.model_policy_violations[0]["errors"])


def test_one_directional_link_connects_both_nodes():
    a = anchored("A", related=["B"])
    b = anchored("B")
    report = Engine().review(
        "Measure reconstructability.",
        [a, b],
        requested=["entropy_health"],
    )
    assert portal(report, "entropy_health").metrics["components"]["graph"] == 100.0


def test_old_native_record_is_not_penalized_for_age_alone():
    old = anchored("OLD", created_at="2010-01-01")
    recent = anchored("RECENT", created_at="2026-01-01")
    old_score = portal(Engine().review("Measure source quality.", [old]), "entropy_health").metrics["components"]["provenance"]
    recent_score = portal(Engine().review("Measure source quality.", [recent]), "entropy_health").metrics["components"]["provenance"]
    assert old_score == recent_score


def test_cross_project_transaction_is_flagged():
    record = anchored("CROSS")
    record.transactions = [Transaction(
        transaction_id="TX-CROSS",
        amount=5000,
        date="2024-01-15",
        project_id="P2",
        lot_id="L2",
        source_record_id="CROSS",
        transaction_type="VENDOR_PAYMENT",
        metadata={"source_project_id": "P1"},
    )]
    report = Engine().review(
        "Is this payment allocated to another project?",
        [record],
        requested=["money_flow"],
    )
    tags = {
        tag
        for observation in portal(report, "money_flow").observations
        for tag in observation.tags
    }
    assert "CROSS_LOT" in tags
