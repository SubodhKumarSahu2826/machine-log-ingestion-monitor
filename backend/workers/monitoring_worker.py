import asyncio
import logging
from typing import Optional

from backend.database import SessionLocal
from backend.repositories.monitoring_repository import MonitoringRepository
from backend.services.monitoring_service import MonitoringService

logger = logging.getLogger(__name__)


class MonitoringWorker:
    """Background worker periodically assessing integration freshness and generating incidents."""

    def __init__(self, interval_seconds: float = 5.0):
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the periodic monitoring loop."""
        self._running = True
        logger.info(f"Starting monitoring worker loop (interval={self.interval_seconds}s)")
        while self._running:
            try:
                self.run_cycle()
            except Exception as exc:
                logger.error(f"Error during monitoring cycle: {exc}")

            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    def run_cycle(self) -> None:
        """Execute a single monitoring cycle synchronously."""
        db = SessionLocal()
        try:
            repo = MonitoringRepository(db)
            service = MonitoringService(repo)
            results = service.run_monitoring_cycle()
            for integration, state, incident in results:
                if incident is not None:
                    logger.warning(
                        f"[incident-created] integration_id={integration.id} "
                        f"name='{integration.name}' state={state.value} "
                        f"incident_id={incident.id}"
                    )
        finally:
            db.close()

    async def stop(self) -> None:
        """Signal the worker to halt gracefully."""
        self._running = False
