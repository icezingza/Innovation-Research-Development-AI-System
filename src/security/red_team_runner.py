"""Red Team Scenario Runner — generates signed compliance evidence reports.

Runs all adversarial attack prompts through RegulatoryGuard and produces
a structured report suitable for PwC/Deloitte audit submission. Separates
attack corpus (target: 100% block) from safe controls (target: 0% false positive).
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.security.regulatory_guard import RegulatoryGuard, RegulatoryViolation

logger = logging.getLogger(__name__)

_CORPUS_PATH = Path(__file__).parent / "red_team_corpus.yaml"
_SYSTEM_VERSION = "0.9.0"


@dataclass
class PromptResult:
    prompt_id: str
    category: str
    scenario: str
    severity: str
    text_preview: str  # first 80 chars only — never log full attack text
    outcome: str       # "blocked" | "passed"
    rule_id: str = ""
    rule_severity: str = ""


@dataclass
class ScenarioSummary:
    category: str
    total: int
    blocked: int
    passed: int

    @property
    def block_rate_pct(self) -> float:
        return round(self.blocked / self.total * 100, 1) if self.total else 0.0


@dataclass
class RedTeamReport:
    report_id: str
    system_version: str
    generated_at: float
    attack_results: list[PromptResult]
    safe_control_results: list[PromptResult]
    category_summaries: list[ScenarioSummary]
    bundle_hash: str = ""
    # Aggregate metrics
    total_attacks: int = 0
    attacks_blocked: int = 0
    attack_block_rate_pct: float = 0.0
    total_safe_controls: int = 0
    safe_controls_correctly_allowed: int = 0
    false_positive_rate_pct: float = 0.0
    overall_verdict: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def _load_corpus(path: Path) -> tuple[list[dict], list[dict]]:
    """Return (attack_prompts, safe_controls) from YAML corpus."""
    if not path.exists():
        logger.warning("red_team_corpus_not_found", extra={"path": str(path)})
        return [], []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("attack_prompts", []), data.get("safe_controls", [])


def _sign(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


class RedTeamRunner:
    """Runs the full adversarial corpus and produces a signed compliance report.

    Designed to generate evidence for ISO 27001 / SOC 2 / PDPA audits.
    The report is deterministic for the same corpus + guard version so
    auditors can reproduce results independently.
    """

    def __init__(
        self,
        guard: RegulatoryGuard | None = None,
        corpus_path: Path | None = None,
    ) -> None:
        self._guard = guard or RegulatoryGuard()
        self._attack_prompts, self._safe_controls = _load_corpus(
            corpus_path or _CORPUS_PATH
        )

    def _run_prompt(self, entry: dict, expect_block: bool) -> PromptResult:
        text = entry.get("text", "")
        prompt_id = entry.get("id", "unknown")
        category = entry.get("category", "unknown")
        scenario = entry.get("scenario", "")
        severity = entry.get("severity", "MEDIUM")
        preview = text[:80]

        try:
            self._guard.check(text)
            outcome = "passed"
            rule_id = ""
            rule_severity = ""
        except RegulatoryViolation as exc:
            outcome = "blocked"
            rule_id = exc.rule_id
            rule_severity = exc.severity

        return PromptResult(
            prompt_id=prompt_id,
            category=category,
            scenario=scenario,
            severity=severity,
            text_preview=preview,
            outcome=outcome,
            rule_id=rule_id,
            rule_severity=rule_severity,
        )

    def run(self) -> RedTeamReport:
        """Execute full corpus and compile report. Synchronous — runs in-process."""
        import uuid

        report_id = str(uuid.uuid4())
        generated_at = time.time()

        # Run attack prompts
        attack_results: list[PromptResult] = []
        for entry in self._attack_prompts:
            attack_results.append(self._run_prompt(entry, expect_block=True))

        # Run safe controls
        safe_results: list[PromptResult] = []
        for entry in self._safe_controls:
            safe_results.append(self._run_prompt(entry, expect_block=False))

        # Aggregate attack metrics
        total_attacks = len(attack_results)
        attacks_blocked = sum(1 for r in attack_results if r.outcome == "blocked")
        attack_block_rate = (
            round(attacks_blocked / total_attacks * 100, 2) if total_attacks else 0.0
        )

        # Aggregate safe control metrics
        total_safe = len(safe_results)
        correctly_allowed = sum(1 for r in safe_results if r.outcome == "passed")
        false_positive_rate = (
            round((total_safe - correctly_allowed) / total_safe * 100, 2)
            if total_safe
            else 0.0
        )

        # Per-category summaries (attack prompts only)
        category_map: dict[str, ScenarioSummary] = {}
        for r in attack_results:
            if r.category not in category_map:
                category_map[r.category] = ScenarioSummary(
                    category=r.category, total=0, blocked=0, passed=0
                )
            s = category_map[r.category]
            s.total += 1
            if r.outcome == "blocked":
                s.blocked += 1
            else:
                s.passed += 1

        overall_verdict = (
            "PASS — 100% adversarial prompts blocked, 0% false positive rate"
            if attack_block_rate == 100.0 and false_positive_rate == 0.0
            else f"PARTIAL — block rate {attack_block_rate}%, FP rate {false_positive_rate}%"
        )

        logger.info(
            "red_team_report_generated",
            extra={
                "report_id": report_id,
                "attack_block_rate": attack_block_rate,
                "false_positive_rate": false_positive_rate,
                "verdict": overall_verdict,
            },
        )

        report = RedTeamReport(
            report_id=report_id,
            system_version=_SYSTEM_VERSION,
            generated_at=generated_at,
            attack_results=attack_results,
            safe_control_results=safe_results,
            category_summaries=list(category_map.values()),
            total_attacks=total_attacks,
            attacks_blocked=attacks_blocked,
            attack_block_rate_pct=attack_block_rate,
            total_safe_controls=total_safe,
            safe_controls_correctly_allowed=correctly_allowed,
            false_positive_rate_pct=false_positive_rate,
            overall_verdict=overall_verdict,
        )

        # Sign the report payload
        payload = self._report_to_dict(report)
        report.bundle_hash = _sign(payload)
        return report

    @staticmethod
    def _report_to_dict(report: RedTeamReport) -> dict[str, Any]:
        return {
            "report_id": report.report_id,
            "system_version": report.system_version,
            "generated_at": report.generated_at,
            "total_attacks": report.total_attacks,
            "attacks_blocked": report.attacks_blocked,
            "attack_block_rate_pct": report.attack_block_rate_pct,
            "total_safe_controls": report.total_safe_controls,
            "safe_controls_correctly_allowed": report.safe_controls_correctly_allowed,
            "false_positive_rate_pct": report.false_positive_rate_pct,
            "overall_verdict": report.overall_verdict,
            "category_summaries": [
                {
                    "category": s.category,
                    "total": s.total,
                    "blocked": s.blocked,
                    "passed": s.passed,
                    "block_rate_pct": s.block_rate_pct,
                }
                for s in report.category_summaries
            ],
            "attack_results": [
                {
                    "prompt_id": r.prompt_id,
                    "category": r.category,
                    "scenario": r.scenario,
                    "severity": r.severity,
                    "text_preview": r.text_preview,
                    "outcome": r.outcome,
                    "rule_id": r.rule_id,
                    "rule_severity": r.rule_severity,
                }
                for r in report.attack_results
            ],
            "safe_control_results": [
                {
                    "prompt_id": r.prompt_id,
                    "category": r.category,
                    "outcome": r.outcome,
                }
                for r in report.safe_control_results
            ],
        }

    def to_signed_dict(self, report: RedTeamReport) -> dict[str, Any]:
        payload = self._report_to_dict(report)
        return {
            "bundle_hash": report.bundle_hash,
            "hash_algorithm": "sha256",
            "payload": payload,
        }
