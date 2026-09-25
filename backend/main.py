import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.events import router as events_router
from backend.api.incidents import router as incidents_router
from backend.api.integrations import router as integrations_router
from backend.workers.monitoring_worker import MonitoringWorker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and clean background worker shutdown."""
    worker = None
    worker_task = None

    if os.getenv("ENABLE_BACKGROUND_MONITOR", "true").lower() in ("true", "1"):
        interval = float(os.getenv("MONITORING_INTERVAL_SECONDS", "5.0"))
        worker = MonitoringWorker(interval_seconds=interval)
        worker_task = asyncio.create_task(worker.start())

    yield

    if worker and worker_task:
        await worker.stop()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Factory Data Reliability Monitor",
    description="Monitors factory machine integrations, event ingestion reliability, and incident recovery.",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Health check endpoint returning system status."""
    return {"status": "healthy"}


app.include_router(events_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(incidents_router, prefix="/api/v1")
