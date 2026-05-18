"""
NamoNexus Standalone Worker Node
This entrypoint allows scaling Agent Workers independently from the API server.
Connects to the central Redis/Postgres/Qdrant/Neo4j cluster and processes tasks.
"""

import asyncio
import logging
import signal
import sys

from src.config import get_settings
from src.inference.client import create_embedding_provider, create_inference_router
from src.memory.qdrant_connector import QdrantMemoryConnector
from src.memory.redis_runtime_store import RedisRuntimeStore
from src.memory.postgres_memory_store import PostgresMemoryStore
from src.memory.neo4j_connector import Neo4jKnowledgeConnector
from src.memory.context_engine import ContextEngine
from src.memory.research_memory import ResearchMemory
from src.infrastructure.event_bus import RuntimeEventBus
from src.agents.memory_agent import MemoryAgent
from src.runtime.scheduler import AsyncScheduler
from src.runtime.worker_pool import AsyncWorkerPool
from src.telemetry.tracing import configure_tracing

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("namonexus.worker")

configure_tracing()

class StandaloneWorker:
    def __init__(self):
        self.settings = get_settings()
        self.worker_pool = None
        self.redis_store = None
        self.stop_event = asyncio.Event()

    async def start(self):
        logger.info("⚙️  Starting Standalone Worker Node (NRE v5.0.0)...")
        
        # 1. Connect to Infrastructure
        self.redis_store = RedisRuntimeStore(url=self.settings.redis_url)
        qdrant = QdrantMemoryConnector(host=self.settings.qdrant_host, port=self.settings.qdrant_port)
        postgres = PostgresMemoryStore(url=self.settings.postgres_url)
        neo4j = Neo4jKnowledgeConnector(
            uri=self.settings.neo4j_uri,
            user=self.settings.neo4j_user,
            password=self.settings.neo4j_password
        )

        # 2. Setup Inference & Context
        inference = create_inference_router(self.settings)
        embedding = create_embedding_provider(self.settings)
        context_engine = ContextEngine(vector_store=qdrant, embedding_provider=embedding)

        # 3. Setup Research Memory & Event Bus
        event_bus = RuntimeEventBus() # For local communication if needed
        research_memory = ResearchMemory(
            context_engine=context_engine,
            event_bus=event_bus
        )
        MemoryAgent(research_memory=research_memory).register(event_bus)

        # 4. Initialize Scheduler & Worker Pool
        scheduler = AsyncScheduler()
        self.worker_pool = AsyncWorkerPool(scheduler=scheduler, max_workers=self.settings.rate_limit_requests_per_minute // 2)

        # 5. Connect and Run
        logger.info(f"🔗 Connected to Redis at {self.settings.redis_url}")
        await self.worker_pool.start()
        
        logger.info("✅ Worker Node is ACTIVE and listening for tasks.")
        
        # Wait for stop signal
        await self.stop_event.wait()
        
        # 6. Graceful Shutdown
        logger.info("🛑 Shutting down worker...")
        await self.worker_pool.stop()
        await self.redis_store.close()
        await neo4j.close()
        logger.info("🔒 Worker shutdown complete.")

    def signal_handler(self):
        self.stop_event.set()

async def main():
    worker = StandaloneWorker()
    
    # Handle signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.signal_handler)
    
    try:
        await worker.start()
    except Exception as e:
        logger.error(f"❌ Critical worker failure: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
