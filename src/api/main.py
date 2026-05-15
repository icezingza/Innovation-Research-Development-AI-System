from fastapi import FastAPI

from src.api.health import router as health_router
from src.api.lifespan import lifespan
from src.api.routes.cognition import router as cognition_router
from src.api.routes.governance import router as governance_router
from src.api.routes.intelligence import router as intelligence_router
from src.api.routes.reasoning import router as reasoning_router
from src.api.routes.research import router as research_router
from src.api.routes.runtime import router as runtime_router
from src.api.routes.workflows import router as workflows_router


def create_app(lifespan_override=None) -> FastAPI:
    return FastAPI(
        title="Cognitive Research Runtime",
        version="0.7.0",
        lifespan=lifespan_override or lifespan,
    )


app = create_app()
app.include_router(health_router)
app.include_router(research_router)
app.include_router(workflows_router)
app.include_router(runtime_router)
app.include_router(reasoning_router)
app.include_router(governance_router)
app.include_router(cognition_router)
app.include_router(intelligence_router)
