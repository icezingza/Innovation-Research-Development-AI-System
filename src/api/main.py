from fastapi import FastAPI

from src.api.health import router as health_router
from src.api.lifespan import lifespan
from src.api.routes.research import router as research_router
from src.api.routes.runtime import router as runtime_router


def create_app(lifespan_override=None) -> FastAPI:
    return FastAPI(
        title="Cognitive Research Runtime",
        version="0.3.0",
        lifespan=lifespan_override or lifespan,
    )


app = create_app()
app.include_router(health_router)
app.include_router(research_router)
app.include_router(runtime_router)
