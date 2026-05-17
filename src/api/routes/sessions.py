"""Cognitive session management endpoints.

POST   /sessions              — create a new session
GET    /sessions              — list active sessions
GET    /sessions/{id}         — get session state
DELETE /sessions/{id}         — close (deactivate) a session
POST   /sessions/{id}/goals   — attach a goal to a session
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.runtime.cognitive_session import CognitiveSessionManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sessions"])


class CreateSessionRequest(BaseModel):
    metadata: dict = {}


class AddGoalRequest(BaseModel):
    goal: str


def _get_manager(request: Request) -> CognitiveSessionManager:
    mgr = getattr(request.app.state, "session_manager", None)
    if mgr is None:
        raise HTTPException(status_code=503, detail="Session manager not initialised")
    return mgr


@router.post("/sessions", status_code=201)
async def create_session(body: CreateSessionRequest, request: Request) -> dict:
    mgr = _get_manager(request)
    session = await mgr.create(metadata=body.metadata)
    return session.model_dump()


@router.get("/sessions")
async def list_sessions(request: Request, limit: int = 50) -> dict:
    mgr = _get_manager(request)
    sessions = await mgr.list_active(limit=limit)
    return {
        "sessions": [s.model_dump() for s in sessions],
        "count": len(sessions),
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request) -> dict:
    mgr = _get_manager(request)
    session = await mgr.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump()


@router.delete("/sessions/{session_id}")
async def close_session(session_id: str, request: Request) -> dict:
    mgr = _get_manager(request)
    ok = await mgr.close(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "status": "closed"}


@router.post("/sessions/{session_id}/goals")
async def add_goal(session_id: str, body: AddGoalRequest, request: Request) -> dict:
    mgr = _get_manager(request)
    ok = await mgr.add_goal(session_id, body.goal)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    session = await mgr.get(session_id)
    return {"session_id": session_id, "goals": session.goals if session else []}


@router.get("/sessions/stats/summary")
async def session_stats(request: Request) -> dict:
    mgr = _get_manager(request)
    return await mgr.stats()
