from datetime import datetime, timezone
from typing import List, Optional, Tuple

from backend.models import (
    Incident,
    IncidentState,
    Integration,
    IntegrationHealthState,
)
from backend.repositories.monitoring_repository import MonitoringRepository


def calculate_freshness(
    last_seen_at: Optional[datetime],
    now: datetime
) -> Optional[float]:
    """
    Calculate the elapsed seconds since the latest received event.
    Returns None if the integration has never received an event (last_seen_at is None).
    """
    if last_seen_at is None:
        return None
    return max(0.0, (now - last_seen_at).total_seconds())


def determine_health_state(
    last_seen_at: Optional[datetime],
    now: datetime,
    warning_threshold_seconds: int = 60,
    stale_threshold_seconds: int = 120
) -> IntegrationHealthState:
    """
    Determine integration health state based on freshness and thresholds:
    - If last_seen_at is None: defined initial state is HEALTHY (pending first data stream).
    - elapsed < warning_threshold_seconds: HEALTHY
    - warning_threshold_seconds <= elapsed < stale_threshold_seconds: WARNING
    - elapsed >= stale_threshold_seconds: STALE
    """
    freshness = calculate_freshness(last_seen_at, now)
    if freshness is None:
        # Defined initial state: an integration that has not received events yet
        # is considered HEALTHY awaiting its initial stream.
        return IntegrationHealthState.HEALTHY

    if freshness >= stale_threshold_seconds:
        return IntegrationHealthState.STALE
    elif freshness >= warning_threshold_seconds:
        return IntegrationHealthState.WARNING
    else:
        return IntegrationHealthState.HEALTHY


class MonitoringService:
    """Service orchestrating freshness evaluation, health transitions, and incident creation."""

    def __init__(self, repository: MonitoringRepository):
        self.repository = repository

    def evaluate_integration(
        self,
        integration: Integration,
        now: Optional[datetime] = None
    ) -> Tuple[IntegrationHealthState, Optional[Incident]]:
        """
        Evaluate health state for a single integration.
        If STALE and no active incident exists, create exactly one incident.
        If health recovers (e.g. from STALE to HEALTHY), update state.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        warning_threshold = integration.warning_threshold_seconds or 60
        stale_threshold = integration.stale_threshold_seconds or 120

        new_state = determine_health_state(
            last_seen_at=integration.last_seen_at,
            now=now,
            warning_threshold_seconds=warning_threshold,
            stale_threshold_seconds=stale_threshold
        )

        # Update integration health state if changed
        if new_state != integration.health_state:
            self.repository.update_health_state(integration, new_state)

        created_incident = None

        # Incident management for STALE integrations
        if new_state == IntegrationHealthState.STALE:
            # Check for existing active incident to avoid duplicates
            active_incident = self.repository.get_active_incident(integration.id)
            if active_incident is None:
                freshness = calculate_freshness(integration.last_seen_at, now)
                freshness_str = f"{freshness:.1f}s" if freshness is not None else "N/A"
                cause = (
                    f"Integration '{integration.name}' is STALE: "
                    f"no events received for {freshness_str} "
                    f"(stale threshold: {stale_threshold}s)"
                )
                created_incident = self.repository.create_incident(
                    integration_id=integration.id,
                    probable_cause=cause,
                    state=IncidentState.OPEN
                )

        return new_state, created_incident

    def run_monitoring_cycle(
        self,
        now: Optional[datetime] = None
    ) -> List[Tuple[Integration, IntegrationHealthState, Optional[Incident]]]:
        """
        Execute a full monitoring pass over all registered integrations.
        Updates state and creates incidents in a single transaction.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        integrations = self.repository.get_all_integrations()
        results = []

        for integration in integrations:
            new_state, incident = self.evaluate_integration(integration, now=now)
            results.append((integration, new_state, incident))

        self.repository.commit()
        return results
