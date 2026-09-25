from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from backend.models import Integration, MachineEvent


class EventRepository:
    """Repository encapsulating database operations for machine events and integrations."""

    def __init__(self, db: Session):
        self.db = db

    def get_integration(self, integration_id: int) -> Optional[Integration]:
        """Fetch integration by ID."""
        return self.db.query(Integration).filter(Integration.id == integration_id).first()

    def get_event_by_event_id(self, event_id: str) -> Optional[MachineEvent]:
        """Fetch machine event by unique event_id."""
        return self.db.query(MachineEvent).filter(MachineEvent.event_id == event_id).first()

    def save_event_and_update_last_seen(
        self,
        event: MachineEvent,
        integration: Integration,
        last_seen_at: datetime
    ) -> None:
        """Persist machine event and update integration last_seen_at in a single transaction."""
        self.db.add(event)
        integration.last_seen_at = last_seen_at
        self.db.commit()

    def rollback(self) -> None:
        """Roll back current transaction."""
        self.db.rollback()
