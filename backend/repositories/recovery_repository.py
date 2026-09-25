from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models import (
    AuditEvent,
    Incident,
    IncidentState,
    Integration,
    MachineEvent,
    RecoveryAttempt,
)


class RecoveryRepository:
    """Repository encapsulating database operations for recovery attempts and incident transitions."""

    def __init__(self, db: Session):
        self.db = db

    def get_incident(self, incident_id: int) -> Optional[Incident]:
        """Fetch an incident by primary key."""
        return self.db.query(Incident).filter(Incident.id == incident_id).first()

    def get_integration(self, integration_id: int) -> Optional[Integration]:
        """Fetch an integration by primary key."""
        return self.db.query(Integration).filter(Integration.id == integration_id).first()

    def get_recovering_incident_for_integration(self, integration_id: int) -> Optional[Incident]:
        """Check if an active incident for this integration is currently in RECOVERING state."""
        return (
            self.db.query(Incident)
            .filter(
                Incident.integration_id == integration_id,
                Incident.state == IncidentState.RECOVERING,
            )
            .first()
        )

    def create_recovery_attempt(
        self,
        incident_id: int,
        action: str,
        status: str = "STARTED",
        attempted_at: Optional[datetime] = None
    ) -> RecoveryAttempt:
        """Create and add a new RecoveryAttempt record."""
        if attempted_at is None:
            attempted_at = datetime.now(timezone.utc)

        attempt = RecoveryAttempt(
            incident_id=incident_id,
            action=action,
            status=status,
            attempted_at=attempted_at,
        )
        self.db.add(attempt)
        return attempt

    def get_latest_recovery_attempt(self, incident_id: int) -> Optional[RecoveryAttempt]:
        """Retrieve the latest recovery attempt for an incident."""
        return (
            self.db.query(RecoveryAttempt)
            .filter(RecoveryAttempt.incident_id == incident_id)
            .order_by(RecoveryAttempt.id.desc())
            .first()
        )

    def get_recovery_attempts(self, incident_id: int) -> List[RecoveryAttempt]:
        """Retrieve all recovery attempts for an incident."""
        return (
            self.db.query(RecoveryAttempt)
            .filter(RecoveryAttempt.incident_id == incident_id)
            .order_by(RecoveryAttempt.attempted_at.asc())
            .all()
        )

    def count_failed_attempts(self, incident_id: int) -> int:
        """Count the number of failed recovery attempts for an incident."""
        return (
            self.db.query(RecoveryAttempt)
            .filter(
                RecoveryAttempt.incident_id == incident_id,
                RecoveryAttempt.status == "FAILURE"
            )
            .count()
        )

    def count_total_attempts(self, incident_id: int) -> int:
        """Count the total number of recovery attempts for an incident."""
        return (
            self.db.query(RecoveryAttempt)
            .filter(RecoveryAttempt.incident_id == incident_id)
            .count()
        )

    def has_event_after(self, integration_id: int, timestamp: datetime) -> bool:
        """Check if any valid machine event was ingested after the specified timestamp."""
        return (
            self.db.query(MachineEvent)
            .filter(
                MachineEvent.integration_id == integration_id,
                MachineEvent.received_at > timestamp
            )
            .first()
            is not None
        )

    def record_audit_event(
        self,
        entity_type: str,
        entity_id: int,
        action: str,
        details: Optional[dict] = None
    ) -> AuditEvent:
        """Record an immutable audit event."""
        audit = AuditEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            details=details,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(audit)
        return audit

    def commit(self) -> None:
        """Commit active transaction."""
        self.db.commit()

    def rollback(self) -> None:
        """Roll back active transaction."""
        self.db.rollback()
