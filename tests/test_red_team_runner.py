"""Tests for RedTeamRunner — adversarial corpus execution and compliance reporting."""

import hashlib
import json
from unittest.mock import MagicMock


from src.security.red_team_runner import RedTeamRunner, _load_corpus, _CORPUS_PATH
from src.security.regulatory_guard import RegulatoryGuard, RegulatoryViolation


def test_corpus_loads_attack_prompts_and_safe_controls():
    attacks, controls = _load_corpus(_CORPUS_PATH)
    assert len(attacks) > 0, "attack_prompts must not be empty"
    assert len(controls) > 0, "safe_controls must not be empty"


def test_corpus_attack_prompts_have_required_fields():
    attacks, _ = _load_corpus(_CORPUS_PATH)
    for entry in attacks:
        assert "id" in entry
        assert "text" in entry
        assert "category" in entry


def test_runner_produces_report():
    runner = RedTeamRunner()
    report = runner.run()
    assert report.report_id
    assert report.system_version == "0.9.0"
    assert report.generated_at > 0


def test_runner_blocks_all_attack_prompts_with_real_rules():
    """With real RegulatoryGuard rules, all attack prompts must be blocked."""
    runner = RedTeamRunner()
    report = runner.run()
    assert report.total_attacks > 0
    # We expect 100% block rate — all adversarial prompts blocked
    unblocked = [r for r in report.attack_results if r.outcome == "passed"]
    assert unblocked == [], (
        f"Expected all attack prompts blocked. Unblocked: {[r.prompt_id for r in unblocked]}"
    )
    assert report.attack_block_rate_pct == 100.0


def test_runner_passes_safe_controls():
    """Safe control prompts must not be falsely blocked."""
    runner = RedTeamRunner()
    report = runner.run()
    assert report.total_safe_controls > 0
    assert report.false_positive_rate_pct == 0.0


def test_runner_verdict_is_pass_when_all_blocked():
    runner = RedTeamRunner()
    report = runner.run()
    assert "PASS" in report.overall_verdict


def test_runner_category_summaries_cover_all_categories():
    runner = RedTeamRunner()
    report = runner.run()
    category_names = {s.category for s in report.category_summaries}
    # Core adversarial categories that must be covered
    for required in ("prompt_injection", "data_exfiltration", "financial_manipulation"):
        assert required in category_names, f"Missing category: {required}"


def test_runner_bundle_hash_is_sha256_of_payload():
    runner = RedTeamRunner()
    report = runner.run()
    signed = runner.to_signed_dict(report)
    payload = signed["payload"]
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    assert signed["bundle_hash"] == expected


def test_runner_with_mock_guard_reports_partial_block():
    """Simulate a guard that only blocks some prompts — verify partial reporting."""
    attacks = [
        {"id": "a-001", "category": "test", "scenario": "s1", "severity": "HIGH", "text": "blocked prompt"},
        {"id": "a-002", "category": "test", "scenario": "s2", "severity": "LOW", "text": "passed prompt"},
    ]
    controls = [
        {"id": "c-001", "category": "safe", "scenario": "", "severity": "LOW", "text": "safe prompt"},
    ]

    guard = MagicMock(spec=RegulatoryGuard)
    def side_effect(text: str) -> bool:
        if "blocked" in text:
            raise RegulatoryViolation("RULE-X", "blocked by test rule")
        return True
    guard.check.side_effect = side_effect

    runner = RedTeamRunner(guard=guard)
    runner._attack_prompts = attacks
    runner._safe_controls = controls

    report = runner.run()
    assert report.total_attacks == 2
    assert report.attacks_blocked == 1
    assert report.attack_block_rate_pct == 50.0
    assert "PARTIAL" in report.overall_verdict


def test_to_signed_dict_structure():
    runner = RedTeamRunner()
    report = runner.run()
    signed = runner.to_signed_dict(report)
    assert "bundle_hash" in signed
    assert "hash_algorithm" in signed
    assert signed["hash_algorithm"] == "sha256"
    assert "payload" in signed
    payload = signed["payload"]
    assert "attack_results" in payload
    assert "safe_control_results" in payload
    assert "category_summaries" in payload


def test_runner_text_preview_truncated():
    """Attack text is never stored fully — only first 80 chars."""
    runner = RedTeamRunner()
    report = runner.run()
    for r in report.attack_results:
        assert len(r.text_preview) <= 80
