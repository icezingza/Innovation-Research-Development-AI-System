import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.agents.critique_agent import CritiqueAgent
from src.agents.hypothesis_agent import HypothesisAgent
from src.agents.memory_agent import MemoryAgent
from src.agents.research_agent import ResearchAgent
from src.agents.synthesis_agent import SynthesisAgent
from src.config import get_settings
from src.governance.audit_log import GovernanceAuditLog
from src.governance.policy_enforcer import PolicyEnforcer
from src.inference.client import create_embedding_provider, create_inference_router
from src.infrastructure.event_bus import RuntimeEventBus
from src.memory.context_engine import RESEARCH_COLLECTION, ContextEngine
from src.memory.knowledge_graph import KnowledgeGraph
from src.memory.memory_manager import MemoryManager
from src.memory.neo4j_connector import Neo4jKnowledgeConnector
from src.memory.postgres_memory_store import PostgresMemoryStore
from src.memory.qdrant_connector import QdrantMemoryConnector
from src.memory.redis_runtime_store import RedisRuntimeStore
from src.memory.research_memory import ResearchMemory
from src.orchestration.agent_coordinator import AgentCoordinator, CoordinatorConfig
from src.orchestration.cognitive_pipeline import CognitivePipeline
from src.orchestration.debate_runtime import DebateRuntime
from src.orchestration.research_agenda import ResearchAgenda
from src.orchestration.research_workflow import ResearchWorkflow, WorkflowConfig
from src.reasoning.adaptive_config import AdaptiveConfigManager
from src.reasoning.quality_tracker import QualityTracker
from src.reasoning.reasoning_trace import ReasoningTrace
from src.reasoning.recursive_loop import RecursiveReasoningLoop
from src.runtime.agent_spawner import AgentSpawner
from src.runtime.cognitive_session import CognitiveSessionManager
from src.runtime.scheduler import AsyncScheduler
from src.runtime.state_manager import RuntimeStateManager
from src.runtime.stream_manager import StreamManager
from src.runtime.worker_pool import AsyncWorkerPool
from src.security.api_keys import APIKeyManager
from src.security.rate_limiter import RateLimiter

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
    neo4j_ok = await _probe("neo4j", neo4j.healthcheck(), errors)

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
            logger.info("qdrant_collection_ready", extra={"collection": RESEARCH_COLLECTION})
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

    # --- security ---
    key_manager = APIKeyManager(raw_keys=settings.api_keys)
    rate_limiter = RateLimiter(
        requests_per_minute=settings.rate_limit_requests_per_minute,
        enabled=settings.rate_limit_enabled,
    )

    # --- governance ---
    audit_log = GovernanceAuditLog(redis_store=redis_store if redis_ok else None)
    policy_enforcer = PolicyEnforcer(audit_log=audit_log)

    # --- reasoning ---
    reasoning_trace = ReasoningTrace(
        store=redis_store if redis_ok else None,
        session_factory=session_factory,
    )
    quality_tracker = QualityTracker(reasoning_trace=reasoning_trace)

    # --- runtime ---
    state_manager = RuntimeStateManager(store=redis_store if redis_ok else None)
    scheduler = AsyncScheduler()
    worker_pool = AsyncWorkerPool(scheduler=scheduler, max_workers=4)
    stream_manager = StreamManager()

    # --- reasoning components ---
    recursive_loop = RecursiveReasoningLoop(trace=reasoning_trace)
    debate_runtime = DebateRuntime(
        inference_router=inference_router if inference_router.enabled else None,
    )

    # --- knowledge graph ---
    knowledge_graph = KnowledgeGraph(connector=neo4j) if neo4j_ok else None

    # --- event bus ---
    event_bus = RuntimeEventBus()

    # --- research memory ---
    research_memory = ResearchMemory(
        context_engine=context_engine,
        session_factory=session_factory,
    )
    MemoryAgent(research_memory=research_memory).register(event_bus)

    # --- specialized agents ---
    _inf = inference_router if inference_router.enabled else None
    hypothesis_agents = [HypothesisAgent(inference_router=_inf, event_bus=event_bus)]
    critique_agents = [CritiqueAgent(inference_router=_inf, event_bus=event_bus)]
    synthesis_agent = SynthesisAgent(inference_router=_inf, event_bus=event_bus)

    coordinator = AgentCoordinator(
        event_bus=event_bus,
        hypothesis_agents=hypothesis_agents,
        critique_agents=critique_agents,
        synthesis_agent=synthesis_agent,
        inference_router=_inf,
        research_memory=research_memory,
        config=CoordinatorConfig(),
    )

    # --- cognitive pipeline ---
    agent = ResearchAgent(inference_router=_inf, context_engine=context_engine)
    pipeline = CognitivePipeline(agents=[agent], policy_enforcer=policy_enforcer)
    research_workflow = ResearchWorkflow(
        pipeline=pipeline,
        debate_runtime=debate_runtime,
        recursive_loop=recursive_loop,
        inference_router=_inf,
        knowledge_graph=knowledge_graph,
        research_memory=research_memory,
        stream_manager=stream_manager,
        config=WorkflowConfig(),
    )

    # --- adaptive config + research agenda + sessions ---
    workflow_config = WorkflowConfig()
    adaptive_config = AdaptiveConfigManager(
        quality_tracker=quality_tracker,
        workflow_config=workflow_config,
    )
    research_agenda = ResearchAgenda(research_memory=research_memory)
    session_manager = CognitiveSessionManager(
        redis_client=redis_store.client if redis_ok else None
    )
    agent_spawner = AgentSpawner(event_bus=event_bus, inference_router=_inf)

    # --- start worker pool ---
    await worker_pool.start()

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
    app.state.research_workflow = research_workflow
    app.state.scheduler = scheduler
    app.state.worker_pool = worker_pool
    app.state.stream_manager = stream_manager
    app.state.audit_log = audit_log
    app.state.event_bus = event_bus
    app.state.coordinator = coordinator
    app.state.research_memory = research_memory
    app.state.quality_tracker = quality_tracker
    app.state.key_manager = key_manager
    app.state.rate_limiter = rate_limiter
    app.state.service_errors = errors
    app.state.settings = settings
    app.state.adaptive_config = adaptive_config
    app.state.research_agenda = research_agenda
    app.state.session_manager = session_manager
    app.state.agent_spawner = agent_spawner

    if errors:
        logger.warning("runtime_started_degraded", extra={"unavailable": list(errors)})
    else:
        logger.info("runtime_started")

    yield

    # --- shutdown ---
    await worker_pool.stop()
    scheduler.stop()
    await redis_store.close()
    await neo4j.close()
    await postgres_store.dispose()
    if engine is not None:
        await engine.dispose()
    logger.info("runtime_stopped")
