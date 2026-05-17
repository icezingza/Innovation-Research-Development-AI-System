import pytest
from src.security.regulatory_guard import RegulatoryGuard, RegulatoryViolation


def test_pdpa_id_card_blocked():
    guard = RegulatoryGuard()
    with pytest.raises(RegulatoryViolation) as exc:
        guard.check("เลขบัตรประชาชนของลูกค้าคือ 1234567890123")
    assert exc.value.rule_id == "PDPA-001"


def test_finance_investment_advice_blocked():
    guard = RegulatoryGuard()
    with pytest.raises(RegulatoryViolation) as exc:
        guard.check("ผมแนะนำให้ซื้อหุ้นตัวนี้ครับ รับประกันผลตอบแทนสูง")
    assert exc.value.rule_id == "FIN-001"


def test_normal_text_passes():
    guard = RegulatoryGuard()
    result = guard.check("โมเดล Machine Learning ใช้ TensorFlow อย่างไร")
    assert result is True
