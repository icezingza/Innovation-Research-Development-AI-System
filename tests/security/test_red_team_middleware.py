from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.security.red_team_middleware import RedTeamMiddleware, _load_corpus


def _corpus_path() -> Path:
    return Path(__file__).parents[2] / "src" / "security" / "red_team_corpus.yaml"


def test_load_corpus_returns_prompts():
    prompts = _load_corpus(_corpus_path())
    assert len(prompts) >= 1
    assert all("id" in p and "text" in p for p in prompts)


def test_load_corpus_missing_file_returns_empty(tmp_path):
    prompts = _load_corpus(tmp_path / "nonexistent.yaml")
    assert prompts == []


@pytest.mark.asyncio
async def test_run_once_returns_blocked_and_passed_counts():
    middleware = RedTeamMiddleware(corpus_path=_corpus_path())
    summary = await middleware._run_once()
    assert "blocked" in summary
    assert "passed" in summary
    assert summary["blocked"] + summary["passed"] == len(middleware._corpus)


@pytest.mark.asyncio
async def test_run_once_logs_to_audit_log():
    audit_log = MagicMock()
    audit_log.record = AsyncMock()
    middleware = RedTeamMiddleware(
        corpus_path=_corpus_path(), audit_log=audit_log
    )
    await middleware._run_once()
    assert audit_log.record.call_count == len(middleware._corpus)


@pytest.mark.asyncio
async def test_start_and_stop_lifecycle():
    middleware = RedTeamMiddleware(
        corpus_path=_corpus_path(), interval_seconds=9999.0
    )
    await middleware.start()
    assert middleware._task is not None
    await middleware.stop()
    assert middleware._task is None


@pytest.mark.asyncio
async def test_safe_prompt_passes_guard():
    middleware = RedTeamMiddleware(corpus_path=_corpus_path())
    summary = await middleware._run_once()
    # At least the safe control prompt (rt-010) should pass
    assert summary["passed"] >= 1
