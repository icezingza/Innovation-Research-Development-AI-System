"""Tests for CognitiveSessionManager."""
import pytest

from src.runtime.cognitive_session import CognitiveSessionManager, SessionState


class TestCognitiveSessionManager:
    @pytest.mark.asyncio
    async def test_create_returns_session(self) -> None:
        mgr = CognitiveSessionManager()
        session = await mgr.create()
        assert isinstance(session, SessionState)
        assert session.session_id
        assert session.active

    @pytest.mark.asyncio
    async def test_create_with_metadata(self) -> None:
        mgr = CognitiveSessionManager()
        session = await mgr.create(metadata={"user": "researcher"})
        assert session.metadata["user"] == "researcher"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_unknown(self) -> None:
        mgr = CognitiveSessionManager()
        result = await mgr.get("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_created_session(self) -> None:
        mgr = CognitiveSessionManager()
        session = await mgr.create()
        retrieved = await mgr.get(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_close_deactivates_session(self) -> None:
        mgr = CognitiveSessionManager()
        session = await mgr.create()
        ok = await mgr.close(session.session_id)
        assert ok
        updated = await mgr.get(session.session_id)
        assert updated is not None
        assert not updated.active

    @pytest.mark.asyncio
    async def test_close_unknown_returns_false(self) -> None:
        mgr = CognitiveSessionManager()
        assert not await mgr.close("not-exists")

    @pytest.mark.asyncio
    async def test_delete_removes_session(self) -> None:
        mgr = CognitiveSessionManager()
        session = await mgr.create()
        ok = await mgr.delete(session.session_id)
        assert ok
        assert await mgr.get(session.session_id) is None

    @pytest.mark.asyncio
    async def test_add_goal(self) -> None:
        mgr = CognitiveSessionManager()
        session = await mgr.create()
        ok = await mgr.add_goal(session.session_id, "Understand dark matter")
        assert ok
        updated = await mgr.get(session.session_id)
        assert "Understand dark matter" in updated.goals  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_add_goal_deduplicates(self) -> None:
        mgr = CognitiveSessionManager()
        session = await mgr.create()
        await mgr.add_goal(session.session_id, "Goal A")
        await mgr.add_goal(session.session_id, "Goal A")
        updated = await mgr.get(session.session_id)
        assert updated.goals.count("Goal A") == 1  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_record_workflow(self) -> None:
        mgr = CognitiveSessionManager()
        session = await mgr.create()
        ok = await mgr.record_workflow(session.session_id, "wf-123")
        assert ok
        updated = await mgr.get(session.session_id)
        assert "wf-123" in updated.workflow_ids  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_increment_findings(self) -> None:
        mgr = CognitiveSessionManager()
        session = await mgr.create()
        await mgr.increment_findings(session.session_id, 3)
        updated = await mgr.get(session.session_id)
        assert updated.findings_count == 3  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_list_active_returns_active_sessions(self) -> None:
        mgr = CognitiveSessionManager()
        s1 = await mgr.create()
        s2 = await mgr.create()
        await mgr.close(s1.session_id)
        active = await mgr.list_active()
        ids = [s.session_id for s in active]
        assert s2.session_id in ids
        assert s1.session_id not in ids

    @pytest.mark.asyncio
    async def test_stats(self) -> None:
        mgr = CognitiveSessionManager()
        await mgr.create()
        stats = await mgr.stats()
        assert stats["total_in_memory"] >= 1
        assert stats["active"] >= 1
        assert not stats["redis_backed"]
