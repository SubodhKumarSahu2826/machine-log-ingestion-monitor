import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError

from backend.models import (
    Incident,
    IncidentState,
    Integration,
    IntegrationHealthState,
    RecoveryAttempt,
)
from backend.repositories.recovery_repository import RecoveryRepository
from backend.schemas.recovery import RecoveryAction


class RecoveryError(Exception):
    """Base exception for recovery service operations."""
    pass


class IncidentNotFoundError(RecoveryError):
    """Raised when an incident is not found."""
    pass


class InvalidIncidentStateError(RecoveryError):
    """Raised when recovery is attempted in an invalid incident state."""
    pass


class ConcurrentRecoveryError(RecoveryError):
    """Raised when concurrent recovery is attempted on the same integration or incident."""
    pass


class MaxAttemptsExceededError(RecoveryError):
    """Raised when recovery exceeds maximum allowed attempts."""
    pass


class RecoveryDatabaseError(RecoveryError):
    """Raised when a database error occurs during recovery operations."""
    pass


class RecoveryService:
    """Service orchestrating controlled recovery, bounded retries, and data-driven verification."""

    def __init__(self, repository: RecoveryRepository, max_attempts: int = 3):
        self.repository = repository
        self.max_attempts = max_attempts

    def initiate_recovery(
        self,
        incident_id: int,
        action: RecoveryAction,
        now: Optional[datetime] = None
    ) -> Tuple[Incident, RecoveryAttempt]:
        """
        Initiate a recovery attempt:
        1. Validate incident exists and is not already resolved/escalated.
        2. Prevent concurrent recoveries for the incident and integration.
        3. Enforce bounded attempts.
        4. Move incident to RECOVERING.
        5. Persist a RecoveryAttempt record with status STARTED.
        """
        incident = self.repository.get_incident(incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident with id {incident_id} not found")

        if incident.state == IncidentState.RESOLVED:
            raise InvalidIncidentStateError(f"Incident {incident_id} is already RESOLVED and cannot be recovered")

        if incident.state == IncidentState.ESCALATED:
            raise MaxAttemptsExceededError(f"Incident {incident_id} is ESCALATED and cannot be recovered")

        if incident.state == IncidentState.RECOVERING:
            raise ConcurrentRecoveryError(f"Incident {incident_id} is already in RECOVERING state")

        if incident.state not in (IncidentState.OPEN, IncidentState.INVESTIGATING, IncidentState.FAILED, IncidentState.DETECTED):
            raise InvalidIncidentStateError(f"Incident {incident_id} in state {incident.state.value} cannot enter recovery")

        # Concurrency protection across the integration
        recovering_incident = self.repository.get_recovering_incident_for_integration(incident.integration_id)
        if recovering_incident and recovering_incident.id != incident.id:
            raise ConcurrentRecoveryError(
                f"Another incident ({recovering_incident.id}) for integration {incident.integration_id} is currently RECOVERING"
            )

        # Check existing failed attempts
        failed_count = self.repository.count_failed_attempts(incident.id)
        if failed_count >= self.max_attempts:
            incident.state = IncidentState.ESCALATED
            integration = self.repository.get_integration(incident.integration_id)
            if integration:
                integration.health_state = IntegrationHealthState.FAILED
            self.repository.commit()
            raise MaxAttemptsExceededError(
                f"Maximum recovery attempts ({self.max_attempts}) exceeded for incident {incident_id}; incident escalated"
            )

        if now is None:
            now = datetime.now(timezone.utc)

        try:
            # Transition incident and integration to RECOVERING
            incident.state = IncidentState.RECOVERING
            integration = self.repository.get_integration(incident.integration_id)
            if integration:
                integration.health_state = IntegrationHealthState.RECOVERING

            # Create recovery attempt record
            attempt = self.repository.create_recovery_attempt(
                incident_id=incident.id,
                action=action.value,
                status="STARTED",
                attempted_at=now
            )

            # Record audit event
            self.repository.record_audit_event(
                entity_type="Incident",
                entity_id=incident.id,
                action="RECOVERY_INITIATED",
                details={"action": action.value, "attempt_id": attempt.id}
            )

            self.repository.commit()
            return incident, attempt
        except SQLAlchemyError as exc:
            self.repository.rollback()
            raise RecoveryDatabaseError(f"Database error initiating recovery: {exc}") from exc

    def verify_recovery(
        self,
        incident_id: int,
        now: Optional[datetime] = None
    ) -> Tuple[bool, Incident, RecoveryAttempt, str]:
        """
        Verify recovery strictly against database telemetry:
        1. Confirms a new valid MachineEvent was ingested after recovery started.
        2. Confirms Integration.last_seen_at advanced beyond recovery_started_at.
        3. If satisfied: moves incident RECOVERING -> VERIFIED -> RESOLVED and integration to HEALTHY.
        4. If not satisfied: moves incident to FAILED (and ESCALATED if failed attempts >= max_attempts).
        """
        incident = self.repository.get_incident(incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident with id {incident_id} not found")

        integration = self.repository.get_integration(incident.integration_id)
        if integration is None:
            raise IncidentNotFoundError(f"Integration {incident.integration_id} not found")

        attempt = self.repository.get_latest_recovery_attempt(incident_id)
        if attempt is None:
            raise InvalidIncidentStateError(f"No recovery attempt found for incident {incident_id}")

        if incident.state != IncidentState.RECOVERING:
            if incident.state == IncidentState.RESOLVED:
                return True, incident, attempt, "Incident is already resolved."
            if incident.state == IncidentState.ESCALATED:
                return False, incident, attempt, "Incident is escalated."
            raise InvalidIncidentStateError(f"Incident is in {incident.state.value} state, not RECOVERING")

        if now is None:
            now = datetime.now(timezone.utc)

        recovery_started_at = attempt.attempted_at

        # Critical verification check: new event arrived after recovery started
        has_new_event = self.repository.has_event_after(integration.id, recovery_started_at)
        last_seen_advanced = (
            integration.last_seen_at is not None and
            integration.last_seen_at > recovery_started_at
        )

        try:
            if has_new_event and last_seen_advanced:
                # Successful verification path: RECOVERING -> VERIFIED -> RESOLVED
                attempt.status = "SUCCESS"
                attempt.completed_at = now
                attempt.result_message = "Recovery verified: fresh machine event ingested and persisted."

                # Explicit transition through VERIFIED to RESOLVED
                incident.state = IncidentState.VERIFIED
                self.repository.record_audit_event(
                    entity_type="Incident",
                    entity_id=incident.id,
                    action="RECOVERY_VERIFIED",
                    details={"attempt_id": attempt.id, "last_seen_at": integration.last_seen_at.isoformat()}
                )

                incident.state = IncidentState.RESOLVED
                incident.resolved_at = now
                integration.health_state = IntegrationHealthState.HEALTHY

                self.repository.record_audit_event(
                    entity_type="Incident",
                    entity_id=incident.id,
                    action="INCIDENT_RESOLVED",
                    details={"attempt_id": attempt.id, "resolved_at": now.isoformat()}
                )

                self.repository.commit()
                return True, incident, attempt, "Recovery successfully verified: new event received and incident resolved."
            else:
                # Failed verification path
                attempt.status = "FAILURE"
                attempt.completed_at = now
                attempt.result_message = "Verification failed: no fresh machine event received after recovery started."

                self.repository.db.flush()
                failed_count = self.repository.count_failed_attempts(incident.id)

                # Move incident to FAILED
                incident.state = IncidentState.FAILED
                self.repository.record_audit_event(
                    entity_type="Incident",
                    entity_id=incident.id,
                    action="RECOVERY_FAILED",
                    details={"attempt_id": attempt.id, "failed_count": failed_count}
                )

                if failed_count >= self.max_attempts:
                    # Bounded retries exceeded: FAILED -> ESCALATED
                    incident.state = IncidentState.ESCALATED
                    integration.health_state = IntegrationHealthState.FAILED
                    msg = f"Recovery verification failed ({failed_count}/{self.max_attempts} attempts). Incident ESCALATED."
                    self.repository.record_audit_event(
                        entity_type="Incident",
                        entity_id=incident.id,
                        action="RECOVERY_ESCALATED",
                        details={"attempt_id": attempt.id, "failed_count": failed_count}
                    )
                else:
                    integration.health_state = IntegrationHealthState.STALE
                    msg = f"Recovery verification failed: no new event. Attempt {failed_count}/{self.max_attempts} marked failed."

                self.repository.commit()
                return False, incident, attempt, msg

        except SQLAlchemyError as exc:
            self.repository.rollback()
            raise RecoveryDatabaseError(f"Database error during recovery verification: {exc}") from exc

    def execute_recovery(
        self,
        incident_id: int,
        action: RecoveryAction,
        timeout_seconds: Optional[float] = None
    ) -> Tuple[Incident, RecoveryAttempt, Optional[bool], str]:
        """
        Execute recovery action with optional synchronous verification wait.
        If timeout_seconds is provided, waits up to timeout for a new event to arrive.
        Otherwise initiates recovery asynchronously and returns RECOVERING state.
        """
        incident, attempt = self.initiate_recovery(incident_id, action)

        if timeout_seconds and timeout_seconds > 0:
            start_wait = time.time()
            integration = self.repository.get_integration(incident.integration_id)
            verified = False

            while (time.time() - start_wait) < timeout_seconds:
                # Check if new event arrived
                if self.repository.has_event_after(integration.id, attempt.attempted_at):
                    verified = True
                    break
                time.sleep(0.1)

            success, incident, attempt, message = self.verify_recovery(incident_id)
            return incident, attempt, success, message
        else:
            return incident, attempt, None, f"Recovery action {action.value} initiated. Incident moved to RECOVERING."
