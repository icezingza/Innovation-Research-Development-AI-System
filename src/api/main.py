from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from src.api.health import router as health_router
from src.api.lifespan import lifespan
from src.api.routes.auth import router as auth_router
from src.api.routes.agenda import router as agenda_router
from src.api.routes.cognition import router as cognition_router
from src.api.routes.governance import router as governance_router
from src.api.routes.intelligence import router as intelligence_router
from src.api.routes.reasoning import router as reasoning_router
from src.api.routes.research import router as research_router
from src.api.routes.runtime import router as runtime_router
from src.api.routes.sessions import router as sessions_router
from src.api.routes.streams import router as streams_router
from src.api.routes.workflows import router as workflows_router
from src.api.routes.dashboard import router as dashboard_router
from src.api.routes.tenants import router as tenants_router
from src.api.routes.experiments import router as experiments_router

# swarms_router: Phase 4 swarm templates (incomplete - missing src.database module)
# Temporarily disabled until swarms.models migrates to src.memory.schema.Base
try:
    from src.swarms.routes import router as swarms_router

    _SWARMS_AVAILABLE = True
except ModuleNotFoundError:
    swarms_router = None
    _SWARMS_AVAILABLE = False


def create_app(lifespan_override=None) -> FastAPI:
    from src.api.middleware import SecurityMiddleware
    from src.security.rate_limit_middleware import RateLimitMiddleware
    from src.tenants.middleware import TenantMiddleware
    from src.tenants.quota_middleware import QuotaMiddleware
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="Cognitive Research Runtime",
        version="0.9.0",
        lifespan=lifespan_override or lifespan,
    )

    # CORS for local HTML testing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all for local testing
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware stack (last added = first executed):
    # Request flow: Security → Tenant → RateLimit → Quota → Route
    app.add_middleware(QuotaMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(SecurityMiddleware)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(research_router)
    app.include_router(workflows_router)
    app.include_router(runtime_router)
    app.include_router(reasoning_router)
    app.include_router(governance_router)
    app.include_router(cognition_router)
    app.include_router(intelligence_router)
    app.include_router(streams_router)
    app.include_router(agenda_router)
    app.include_router(sessions_router)
    app.include_router(dashboard_router)
    app.include_router(tenants_router)
    app.include_router(experiments_router)
    if _SWARMS_AVAILABLE:
        app.include_router(swarms_router)

    # Static files and client-side routing
    frontend_dist = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist"
    )

    if os.path.exists(frontend_dist):
        app.mount(
            "/assets",
            StaticFiles(directory=os.path.join(frontend_dist, "assets")),
            name="assets",
        )

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if full_path.startswith("api/"):
                return  # Let FastAPI handle API routes

            file_path = os.path.join(frontend_dist, full_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(file_path)

            return FileResponse(os.path.join(frontend_dist, "index.html"))

    return app


app = create_app()
