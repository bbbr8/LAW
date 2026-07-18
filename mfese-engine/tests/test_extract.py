from mfese.extract import classify_role, extract_items


def test_role_classification():
    roles = classify_role("CABINET PROPOSAL AND AGREEMENT Total $58,000.00", "proposal.pdf", None)
    assert roles[0]["role"] == "proposal"


def test_extract_amount_and_envelope():
    text = "Total $58,473.34\nDocuSign Envelope ID: 95A11674-A840-4CB0-A0AD-2B2947AF9ADC"
    items = extract_items(text, [text])
    assert any(item.kind == "amount" and item.value == 58473.34 for item in items)
    assert any(item.kind == "envelope_id" for item in items)
