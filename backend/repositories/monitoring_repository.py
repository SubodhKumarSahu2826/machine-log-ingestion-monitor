from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models import (
    Incident,
    IncidentState,
    Integration,
    IntegrationHealthState,
)


class MonitoringRepository:
    """Repository encapsulating queries and mutations for monitoring and incident creation."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_integrations(self) -> List[Integration]:
        """Fetch all integrations for monitoring evaluation."""
        return self.db.query(Integration).all()

    def get_integration_by_id(self, integration_id: int) -> Optional[Integration]:
        """Fetch an integration by primary key."""
        return self.db.query(Integration).filter(Integration.id == integration_id).first()

    def get_active_incident(self, integration_id: int) -> Optional[Incident]:
        """Fetch the current unresolved incident for an integration, if any."""
        return (
            self.db.query(Incident)
            .filter(
                Incident.integration_id == integration_id,
                Incident.state != IncidentState.RESOLVED,
            )
            .first()
        )

    def create_incident(
        self,
        integration_id: int,
        probable_cause: str,
        state: IncidentState = IncidentState.OPEN
    ) -> Incident:
        """Create and persist an incident."""
        incident = Incident(
            integration_id=integration_id,
            probable_cause=probable_cause,
            state=state,
        )
        self.db.add(incident)
        return incident

    def get_incident_by_id(self, incident_id: int) -> Optional[Incident]:
        """Fetch an incident by primary key."""
        return self.db.query(Incident).filter(Incident.id == incident_id).first()

    def update_incident_diagnosis(
        self,
        incident: Incident,
        probable_cause: str,
        diagnostic_details: dict,
        state: Optional[IncidentState] = None
    ) -> None:
        """Update incident with deterministic diagnostic assessment."""
        incident.probable_cause = probable_cause
        incident.diagnostic_details = diagnostic_details
        if state is not None:
            incident.state = state

    def update_health_state(
        self,
        integration: Integration,
        health_state: IntegrationHealthState
    ) -> None:
        """Update integration health state."""
        integration.health_state = health_state

    def commit(self) -> None:
        """Commit pending transaction changes."""
        self.db.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        self.db.rollback()
