from fastapi import FastAPI

from src.api.health import router as health_router

app = FastAPI(
    title="Cognitive Research Runtime",
    version="0.2.0",
)

app.include_router(health_router)
