import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.agents.research_agent import ResearchAgent
from src.config import get_settings
from src.governance.policy_enforcer import PolicyEnforcer
from src.inference.client import create_embedding_provider, create_inference_router
from src.memory.context_engine import RESEARCH_COLLECTION, ContextEngine
from src.memory.memory_manager import MemoryManager
from src.memory.neo4j_connector import Neo4jKnowledgeConnector
from src.memory.postgres_memory_store import PostgresMemoryStore
from src.memory.qdrant_connector import QdrantMemoryConnector
from src.memory.redis_runtime_store import RedisRuntimeStore
from src.orchestration.cognitive_pipeline import CognitivePipeline
from src.orchestration.debate_runtime import DebateRuntime
from src.reasoning.reasoning_trace import ReasoningTrace
from src.reasoning.recursive_loop import RecursiveReasoningLoop
from src.runtime.state_manager import RuntimeStateManager

logger = logging.getLogger(__name__)


async def _probe(name: str, coro, errors: dict) -> bool:
    try:
        await coro
        logger.info("service_connected", extra={"service": name})
        return True
    except Exception as exc:
        errors[name] = str(exc)
        logger.warning(
            "service_unavailable", extra={"service": name, "error": str(exc)}
        )
        return False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    errors: dict[str, str] = {}

    # --- memory connectors ---
    qdrant = QdrantMemoryConnector(host=settings.qdrant_host, port=settings.qdrant_port)
    qdrant_ok = await _probe("qdrant", qdrant.healthcheck(), errors)

    redis_store = RedisRuntimeStore(url=settings.redis_url)
    redis_ok = await _probe("redis", redis_store.healthcheck(), errors)

    postgres_store = PostgresMemoryStore(url=settings.postgres_url)
    pg_ok = await _probe("postgres", postgres_store.healthcheck(), errors)
    if pg_ok:
        try:
            await postgres_store.init_schema()
        except Exception as exc:
            logger.error("schema_init_failed", extra={"error": str(exc)})
            pg_ok = False

    neo4j = Neo4jKnowledgeConnector(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
    await _probe("neo4j", neo4j.healthcheck(), errors)

    memory = MemoryManager(
        vector_store=qdrant,
        graph_store=neo4j,
        runtime_store=redis_store,
        persistence_store=postgres_store,
    )

    # --- inference layer ---
    inference_router = create_inference_router(settings)
    embedding_provider = create_embedding_provider(settings)
    if inference_router.enabled:
        logger.info(
            "inference_ready", extra={"provider": inference_router.active_provider}
        )
    else:
        logger.warning("inference_disabled_heuristic_mode")

    # --- Qdrant collection bootstrap ---
    if qdrant_ok and embedding_provider.enabled:
        try:
            await qdrant.ensure_collection(
                name=RESEARCH_COLLECTION,
                vector_size=embedding_provider.dimensions,
            )
            logger.info(
                "qdrant_collection_ready",
                extra={"collection": RESEARCH_COLLECTION},
            )
        except Exception as exc:
            logger.warning("qdrant_collection_init_failed", extra={"error": str(exc)})

    # --- context engine ---
    context_engine = (
        ContextEngine(vector_store=qdrant, embedding_provider=embedding_provider)
        if qdrant_ok and embedding_provider.enabled
        else None
    )

    # --- DB session factory ---
    session_factory = None
    engine = None
    if pg_ok:
        engine = create_async_engine(settings.postgres_url, echo=False)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # --- reasoning trace (three-tier: memory + Redis + PostgreSQL) ---
    reasoning_trace = ReasoningTrace(
        store=redis_store if redis_ok else None,
        session_factory=session_factory,
    )

    # --- runtime ---
    state_manager = RuntimeStateManager(store=redis_store if redis_ok else None)

    # --- reasoning components ---
    recursive_loop = RecursiveReasoningLoop(trace=reasoning_trace)
    debate_runtime = DebateRuntime(
        inference_router=inference_router if inference_router.enabled else None,
    )

    # --- agent pipeline ---
    agent = ResearchAgent(
        inference_router=inference_router if inference_router.enabled else None,
        context_engine=context_engine,
    )
    pipeline = CognitivePipeline(agents=[agent], policy_enforcer=PolicyEnforcer())

    # --- wire app state ---
    app.state.memory = memory
    app.state.state_manager = state_manager
    app.state.pipeline = pipeline
    app.state.db_session = session_factory
    app.state.inference = inference_router
    app.state.embedding = embedding_provider
    app.state.reasoning_trace = reasoning_trace
    app.state.recursive_loop = recursive_loop
    app.state.debate_runtime = debate_runtime
    app.state.service_errors = errors
    app.state.settings = settings

    if errors:
        logger.warning("runtime_started_degraded", extra={"unavailable": list(errors)})
    else:
        logger.info("runtime_started")

    yield

    # --- shutdown ---
    await redis_store.close()
    await neo4j.close()
    await postgres_store.dispose()
    if engine is not None:
        await engine.dispose()
    logger.info("runtime_stopped")
