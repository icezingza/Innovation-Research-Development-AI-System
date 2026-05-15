from fastapi import APIRouter, Depends

from src.api.dependencies import get_research_memory
from src.memory.research_memory import ResearchMemory

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/report")
async def intelligence_report(
    memory: ResearchMemory = Depends(get_research_memory),
) -> dict:
    """Runtime intelligence summary — accumulated knowledge and quality metrics."""
    stats = await memory.stats()
    recent = await memory.get_all(limit=5)
    return {
        "knowledge_base": stats,
        "recent_findings": [
            {
                "entry_id": e.entry_id,
                "topic": e.topic,
                "statement": e.statement[:200],
                "confidence": e.confidence,
                "source": e.source,
            }
            for e in recent
        ],
    }


@router.get("/recall")
async def recall_knowledge(
    topic: str,
    limit: int = 5,
    memory: ResearchMemory = Depends(get_research_memory),
) -> dict:
    """Retrieve semantically relevant prior research for a topic."""
    entries = await memory.recall(topic=topic, limit=limit)
    return {
        "topic": topic,
        "entries": [
            {
                "entry_id": e.entry_id,
                "statement": e.statement,
                "confidence": e.confidence,
                "source": e.source,
                "session_id": e.session_id,
            }
            for e in entries
        ],
        "count": len(entries),
    }


@router.get("/hypotheses")
async def list_hypotheses(
    limit: int = 50,
    memory: ResearchMemory = Depends(get_research_memory),
) -> dict:
    """List all stored hypotheses and synthesis findings."""
    entries = await memory.get_all(limit=limit)
    return {
        "entries": [e.model_dump() for e in entries],
        "count": len(entries),
    }
