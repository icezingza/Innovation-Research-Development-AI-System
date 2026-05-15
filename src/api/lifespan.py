import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.agents.research_agent import ResearchAgent
from src.config import get_settings
from src.governance.policy_enforcer import PolicyEnforcer
from src.inference.client import InferenceClient
from src.memory.memory_manager import MemoryManager
from src.memory.neo4j_connector import Neo4jKnowledgeConnector
from src.memory.postgres_memory_store import PostgresMemoryStore
from src.memory.qdrant_connector import QdrantMemoryConnector
from src.memory.redis_runtime_store import RedisRuntimeStore
from src.orchestration.cognitive_pipeline import CognitivePipeline
from src.runtime.state_manager import RuntimeStateManager

logger = logging.getLogger(__name__)


async def _try_connect(name: str, coro, errors: dict) -> object | None:
    try:
        result = await coro
        logger.info("service_connected", extra={"service": name})
        return result
    except Exception as exc:
        errors[name] = str(exc)
        logger.warning(
            "service_unavailable", extra={"service": name, "error": str(exc)}
        )
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    errors: dict[str, str] = {}

    # --- memory layer ---
    qdrant = QdrantMemoryConnector(host=settings.qdrant_host, port=settings.qdrant_port)
    await _try_connect("qdrant", qdrant.healthcheck(), errors)

    redis_store = RedisRuntimeStore(url=settings.redis_url)
    await _try_connect("redis", redis_store.healthcheck(), errors)

    postgres_store = PostgresMemoryStore(url=settings.postgres_url)
    pg_ok = await _try_connect("postgres", postgres_store.healthcheck(), errors)
    if pg_ok:
        try:
            await postgres_store.init_schema()
        except Exception as exc:
            logger.error("schema_init_failed", extra={"error": str(exc)})

    neo4j = Neo4jKnowledgeConnector(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
    await _try_connect("neo4j", neo4j.healthcheck(), errors)

    memory = MemoryManager(
        vector_store=qdrant,
        graph_store=neo4j,
        runtime_store=redis_store,
        persistence_store=postgres_store,
    )

    # --- runtime ---
    redis_ok = not errors.get("redis")
    state_manager = RuntimeStateManager(store=redis_store if redis_ok else None)
    inference_client = InferenceClient(settings)

    # --- db session factory (None when postgres unavailable) ---
    session_factory = None
    if not errors.get("postgres"):
        engine = create_async_engine(settings.postgres_url, echo=False)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # --- agent pipeline ---
    agent = ResearchAgent(inference_client=inference_client)
    pipeline = CognitivePipeline(agents=[agent], policy_enforcer=PolicyEnforcer())

    # --- wire app state ---
    app.state.memory = memory
    app.state.state_manager = state_manager
    app.state.pipeline = pipeline
    app.state.db_session = session_factory
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
    if session_factory is not None:
        await engine.dispose()
    logger.info("runtime_stopped")
