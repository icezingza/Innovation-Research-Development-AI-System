import asyncio
import logging
from pathlib import Path

import yaml

from src.governance.audit_log import AuditEntry, GovernanceAuditLog
from src.security.regulatory_guard import RegulatoryGuard, RegulatoryViolation

logger = logging.getLogger(__name__)

_CORPUS_PATH = Path(__file__).parent / "red_team_corpus.yaml"


def _load_corpus(path: Path) -> list[dict]:
    if not path.exists():
        logger.warning("red_team_corpus_not_found", extra={"path": str(path)})
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("prompts", []) if data else []


class RedTeamMiddleware:
    """Background adversarial stress-tester for RegulatoryGuard.

    Runs the static corpus against RegulatoryGuard on startup and then
    periodically. Never blocks the request path.
    """

    def __init__(
        self,
        guard: RegulatoryGuard | None = None,
        audit_log: "GovernanceAuditLog | None" = None,
        interval_seconds: float = 300.0,
        corpus_path: Path | None = None,
    ) -> None:
        self._guard = guard or RegulatoryGuard()
        self._audit_log: GovernanceAuditLog | None = audit_log
        self._interval = interval_seconds
        self._corpus = _load_corpus(corpus_path or _CORPUS_PATH)
        self._task: asyncio.Task | None = None

    async def _run_once(self) -> dict[str, int]:
        """Run all corpus prompts through RegulatoryGuard once. Returns summary."""
        blocked = 0
        passed = 0
        for entry in self._corpus:
            prompt_id = entry.get("id", "unknown")
            text = entry.get("text", "")
            try:
                self._guard.check(text)
                passed += 1
                logger.debug("red_team_passed", extra={"prompt_id": prompt_id})
                if self._audit_log is not None:
                    await self._audit_log.record(
                        AuditEntry(
                            decision="allow",
                            reason="red_team_pass",
                            message_id=prompt_id,
                            sender_id="red_team_middleware",
                            message_type="adversarial_prompt",
                            content_size_bytes=len(text.encode()),
                        )
                    )
            except RegulatoryViolation as exc:
                blocked += 1
                logger.info(
                    "red_team_blocked",
                    extra={
                        "prompt_id": prompt_id,
                        "rule_id": exc.rule_id,
                        "severity": exc.severity,
                    },
                )
                if self._audit_log is not None:
                    await self._audit_log.record(
                        AuditEntry(
                            decision="block",
                            reason=exc.rule_id,
                            message_id=prompt_id,
                            sender_id="red_team_middleware",
                            message_type="adversarial_prompt",
                            content_size_bytes=len(text.encode()),
                            extra={"severity": exc.severity},
                        )
                    )
        logger.info(
            "red_team_run_complete",
            extra={"blocked": blocked, "passed": passed, "total": len(self._corpus)},
        )
        return {"blocked": blocked, "passed": passed}

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                await self._run_once()
            except Exception as exc:
                logger.warning("red_team_loop_error", extra={"error": str(exc)})

    async def start(self) -> None:
        """Run corpus once immediately, then schedule periodic runs."""
        await self._run_once()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
