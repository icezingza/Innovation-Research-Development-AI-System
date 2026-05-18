"""ChaosAgent — continuous adversarial red-team agent for autonomous system hardening.

Runs during idle time to exercise RegulatoryGuard against the full attack corpus,
identifies any prompts that slipped through (misses), generates new keyword rules
from those misses, and persists them so the next run is harder to fool.

Self-hardening flywheel:
    run N  → find miss → generate rule → write learned_rules.yaml
    run N+1 → fresh guard loads learned_rules.yaml → miss no longer slips through
"""

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.governance.audit_log import AuditEntry, GovernanceAuditLog
from src.security.chaos_rule_generator import ChaosRuleGenerator
from src.security.regulatory_guard import RegulatoryGuard, RegulatoryViolation

logger = logging.getLogger(__name__)

_CORPUS_PATH = Path(__file__).parent.parent / "security" / "red_team_corpus.yaml"


class PromptResult(BaseModel):
    prompt_id: str
    category: str
    text: str
    was_blocked: bool
    expected_blocked: bool
    violation_rule: str | None = None
    is_miss: bool = False
    is_false_positive: bool = False


class ChaosRunReport(BaseModel):
    run_id: str
    started_at: str
    attack_total: int
    attack_blocked: int
    attack_missed: int
    control_total: int
    control_passed: int
    control_false_positives: int
    new_rules_added: int
    block_rate: float
    miss_ids: list[str] = Field(default_factory=list)
    details: list[dict[str, Any]] = Field(default_factory=list)


def _load_corpus(path: Path) -> tuple[list[dict], list[dict]]:
    """Return (attack_prompts, safe_controls) from corpus YAML."""
    if not path.exists():
        return [], []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("attack_prompts", []), data.get("safe_controls", [])


class ChaosAgent:
    """Autonomous adversarial stress-tester that hardens the regulatory guardrail over time.

    Each ``run()`` call:
    1. Instantiates a fresh RegulatoryGuard (picks up any newly learned rules).
    2. Fires all attack prompts — records any that were NOT blocked (misses).
    3. Fires all safe controls — records any that WERE blocked (false positives).
    4. Mines missed prompts for keyword patterns and writes them to learned_rules.yaml.
    5. Logs a structured audit entry via GovernanceAuditLog.
    """

    def __init__(
        self,
        audit_log: GovernanceAuditLog | None = None,
        rule_generator: ChaosRuleGenerator | None = None,
        corpus_path: Path = _CORPUS_PATH,
        rules_path: Path | None = None,
    ) -> None:
        self._audit = audit_log or GovernanceAuditLog()
        self._generator = rule_generator or ChaosRuleGenerator()
        self._corpus_path = corpus_path
        self._rules_path = rules_path  # None → default RegulatoryGuard path

    def _make_guard(self) -> RegulatoryGuard:
        return (
            RegulatoryGuard(rules_path=str(self._rules_path))
            if self._rules_path
            else RegulatoryGuard()
        )

    async def run(self) -> ChaosRunReport:
        run_id = str(uuid.uuid4())
        started_at = datetime.now(UTC).isoformat()
        logger.info("chaos_agent.run_start run_id=%s", run_id)

        guard = self._make_guard()
        attack_prompts, safe_controls = _load_corpus(self._corpus_path)

        results: list[PromptResult] = []
        miss_ids: list[str] = []

        for entry in attack_prompts:
            pid = entry.get("id", "unknown")
            text = entry.get("text", "")
            blocked = False
            rule_hit: str | None = None
            try:
                guard.check(text)
            except RegulatoryViolation as exc:
                blocked = True
                rule_hit = exc.rule_id

            is_miss = not blocked
            if is_miss:
                miss_ids.append(pid)
                logger.warning(
                    "chaos_agent.miss prompt_id=%s category=%s",
                    pid,
                    entry.get("category", ""),
                )

            results.append(
                PromptResult(
                    prompt_id=pid,
                    category=entry.get("category", ""),
                    text=text[:120],
                    was_blocked=blocked,
                    expected_blocked=True,
                    violation_rule=rule_hit,
                    is_miss=is_miss,
                )
            )

        fp_count = 0
        for entry in safe_controls:
            pid = entry.get("id", "unknown")
            text = entry.get("text", "")
            blocked = False
            rule_hit = None
            try:
                guard.check(text)
            except RegulatoryViolation as exc:
                blocked = True
                rule_hit = exc.rule_id
                fp_count += 1
                logger.warning(
                    "chaos_agent.false_positive prompt_id=%s rule=%s", pid, exc.rule_id
                )

            results.append(
                PromptResult(
                    prompt_id=pid,
                    category=entry.get("category", ""),
                    text=text[:120],
                    was_blocked=blocked,
                    expected_blocked=False,
                    violation_rule=rule_hit,
                    is_false_positive=blocked,
                )
            )

        new_rules_added = self._generator.generate_and_persist(miss_ids)

        attack_blocked = len(attack_prompts) - len(miss_ids)
        block_rate = (
            attack_blocked / len(attack_prompts) if attack_prompts else 1.0
        )

        report = ChaosRunReport(
            run_id=run_id,
            started_at=started_at,
            attack_total=len(attack_prompts),
            attack_blocked=attack_blocked,
            attack_missed=len(miss_ids),
            control_total=len(safe_controls),
            control_passed=len(safe_controls) - fp_count,
            control_false_positives=fp_count,
            new_rules_added=new_rules_added,
            block_rate=round(block_rate, 4),
            miss_ids=miss_ids,
            details=[r.model_dump() for r in results],
        )

        await self._audit.record(
            AuditEntry(
                decision="chaos_run",
                reason=f"block_rate={block_rate:.2%} misses={len(miss_ids)} new_rules={new_rules_added}",
                message_id=run_id,
                sender_id="chaos_agent",
                message_type="chaos_simulation",
                content_size_bytes=0,
                extra={
                    "attack_total": len(attack_prompts),
                    "attack_blocked": attack_blocked,
                    "miss_ids": miss_ids,
                    "false_positives": fp_count,
                    "new_rules_added": new_rules_added,
                },
            )
        )

        logger.info(
            "chaos_agent.run_complete run_id=%s block_rate=%.2f misses=%d new_rules=%d",
            run_id,
            block_rate,
            len(miss_ids),
            new_rules_added,
        )
        return report
