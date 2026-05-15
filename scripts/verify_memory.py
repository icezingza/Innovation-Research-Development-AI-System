"""Memory infrastructure health check script.

Verifies connectivity to Neo4j (Knowledge Graph) and Qdrant (Vector Search)
before starting the cognitive runtime. Retries up to 10 times with 3s backoff.

Usage:
    python scripts/verify_memory.py

Environment variables (see .env.example):
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
    QDRANT_HOST, QDRANT_PORT
"""
import asyncio
import os
import sys
import time


def check_neo4j() -> bool:
    try:
        from neo4j import GraphDatabase  # type: ignore[import]

        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        print("Neo4j (Knowledge Graph) is ONLINE.")
        return True
    except ImportError:
        print("neo4j package not installed — run: pip install neo4j")
        return False
    except Exception as exc:
        print(f"Waiting for Neo4j... ({exc})")
        return False


def check_qdrant() -> bool:
    try:
        from qdrant_client import QdrantClient  # type: ignore[import]

        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", "6333"))
        client = QdrantClient(host=host, port=port, timeout=5)
        client.get_collections()
        print("Qdrant (Vector Search) is ONLINE.")
        return True
    except ImportError:
        print("qdrant-client package not installed — run: pip install qdrant-client")
        return False
    except Exception as exc:
        print(f"Waiting for Qdrant... ({exc})")
        return False


async def check_postgres() -> bool:
    try:
        import asyncpg  # type: ignore[import]

        url = os.getenv(
            "POSTGRES_URL",
            "postgresql://cognitive:cognitive@localhost/cognition",
        ).replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(url, timeout=5)
        await conn.close()
        print("PostgreSQL (Structured Persistence) is ONLINE.")
        return True
    except ImportError:
        print("asyncpg package not installed — run: pip install asyncpg")
        return False
    except Exception as exc:
        print(f"Waiting for PostgreSQL... ({exc})")
        return False


async def check_redis() -> bool:
    try:
        import redis.asyncio as aioredis  # type: ignore[import]

        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        client = aioredis.from_url(url, socket_connect_timeout=5)
        await client.ping()
        await client.aclose()
        print("Redis (Runtime Cache) is ONLINE.")
        return True
    except ImportError:
        print("redis package not installed — run: pip install redis")
        return False
    except Exception as exc:
        print(f"Waiting for Redis... ({exc})")
        return False


async def main(retries: int = 10, interval: float = 3.0) -> int:
    print("Initiating Memory Infrastructure Health Check...")
    print(f"Checking: Neo4j, Qdrant, PostgreSQL, Redis (up to {retries} attempts)\n")

    neo4j_ready = False
    qdrant_ready = False
    pg_ready = False
    redis_ready = False

    for attempt in range(1, retries + 1):
        print(f"--- Attempt {attempt}/{retries} ---")

        if not neo4j_ready:
            neo4j_ready = check_neo4j()
        if not qdrant_ready:
            qdrant_ready = check_qdrant()
        if not pg_ready:
            pg_ready = await check_postgres()
        if not redis_ready:
            redis_ready = await check_redis()

        all_ready = neo4j_ready and qdrant_ready and pg_ready and redis_ready
        if all_ready:
            print("\nAll Memory Systems are Fully Operational!")
            return 0

        ready = sum([neo4j_ready, qdrant_ready, pg_ready, redis_ready])
        print(f"{ready}/4 systems ready\n")

        if attempt < retries:
            time.sleep(interval)

    print("\nError: Memory Systems failed to initialize in time.")
    print("Tip: Run `docker compose up -d` from the project root to start all services.")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
