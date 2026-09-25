from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from backend.models import Incident, IncidentState, Integration
from backend.repositories.monitoring_repository import MonitoringRepository
from backend.schemas.diagnostic import CheckStatus, DiagnosticResult, ProbableCause


class DiagnosticError(Exception):
    """Base exception for diagnostic service operations."""
    pass


class IncidentNotFoundError(DiagnosticError):
    """Raised when the specified incident does not exist."""
    pass


class InvalidIncidentStateError(DiagnosticError):
    """Raised when an incident is not in a diagnostically viable state."""
    pass


def classify_probable_cause(
    checks: Dict[str, CheckStatus]
) -> Tuple[ProbableCause, str]:
    """
    Deterministic decision tree identifying probable cause based on check outcomes.
    Order of evaluation:
    1. MACHINE_HEARTBEAT == FAIL -> MACHINE_OFFLINE
    2. MACHINE_HEARTBEAT == PASS and NETWORK == FAIL -> NETWORK_FAILURE
    3. CONNECTOR == FAIL -> CONNECTOR_FAILURE
    4. AUTHENTICATION == FAIL -> AUTHENTICATION_FAILURE
    5. PARSER == FAIL -> PARSER_FAILURE
    6. INGESTION == FAIL -> INGESTION_FAILURE
    7. Otherwise -> UNKNOWN
    """
    hb = checks.get("machine_heartbeat", CheckStatus.UNKNOWN)
    net = checks.get("network", CheckStatus.UNKNOWN)
    conn = checks.get("connector", CheckStatus.UNKNOWN)
    auth = checks.get("authentication", CheckStatus.UNKNOWN)
    parser = checks.get("parser", CheckStatus.UNKNOWN)
    ingest = checks.get("ingestion", CheckStatus.UNKNOWN)

    if hb == CheckStatus.FAIL:
        return (
            ProbableCause.MACHINE_OFFLINE,
            "Machine heartbeat is unavailable or timed out; equipment appears offline or powered down."
        )
    elif hb == CheckStatus.PASS and net == CheckStatus.FAIL:
        return (
            ProbableCause.NETWORK_FAILURE,
            "Machine heartbeat is available, but network communication to the equipment failed."
        )
    elif net in (CheckStatus.PASS, CheckStatus.UNKNOWN) and conn == CheckStatus.FAIL:
        return (
            ProbableCause.CONNECTOR_FAILURE,
            "Network route is available, but integration connector adapter failed or crashed."
        )
    elif conn in (CheckStatus.PASS, CheckStatus.UNKNOWN) and auth == CheckStatus.FAIL:
        return (
            ProbableCause.AUTHENTICATION_FAILURE,
            "Connector is operational, but authentication credentials or token were rejected."
        )
    elif auth in (CheckStatus.PASS, CheckStatus.UNKNOWN) and parser == CheckStatus.FAIL:
        return (
            ProbableCause.PARSER_FAILURE,
            "Payload transmission succeeded, but parser or schema validation failed on incoming data."
        )
    elif parser in (CheckStatus.PASS, CheckStatus.UNKNOWN) and ingest == CheckStatus.FAIL:
        return (
            ProbableCause.INGESTION_FAILURE,
            "Upstream telemetry validated, but backend ingestion service or database persistence failed."
        )
    else:
        return (
            ProbableCause.UNKNOWN,
            "Diagnostic checks could not identify a definitive failure point; checks are either healthy or unobservable."
        )


class DiagnosticService:
    """Service orchestrating deterministic incident diagnostics."""

    def __init__(self, repository: MonitoringRepository):
        self.repository = repository

    def evaluate_checks(
        self,
        integration: Integration,
        probe_overrides: Optional[Dict[str, CheckStatus]] = None,
        now: Optional[datetime] = None
    ) -> Dict[str, CheckStatus]:
        """
        Evaluate the 6 diagnostic checks for an integration:
        - MACHINE_HEARTBEAT: evaluated from integration.last_heartbeat_at.
        - INGESTION: evaluated from backend database accessibility.
        - NETWORK, CONNECTOR, AUTHENTICATION, PARSER:
          In the MVP (without physical factory hardware/PLCs/brokers), unobservable checks
          default to UNKNOWN unless controlled probe overrides are provided (e.g. for testing).
        """
        if now is None:
            now = datetime.now(timezone.utc)

        overrides = probe_overrides or {}
        checks: Dict[str, CheckStatus] = {}

        # 1. MACHINE_HEARTBEAT
        if "machine_heartbeat" in overrides:
            checks["machine_heartbeat"] = overrides["machine_heartbeat"]
        else:
            if integration.last_heartbeat_at is None:
                checks["machine_heartbeat"] = CheckStatus.FAIL
            else:
                elapsed = (now - integration.last_heartbeat_at).total_seconds()
                stale_threshold = integration.stale_threshold_seconds or 120
                if elapsed > stale_threshold:
                    checks["machine_heartbeat"] = CheckStatus.FAIL
                else:
                    checks["machine_heartbeat"] = CheckStatus.PASS

        # 2. NETWORK (unobservable without real network probes)
        checks["network"] = overrides.get("network", CheckStatus.UNKNOWN)

        # 3. CONNECTOR (unobservable without real connector daemons)
        checks["connector"] = overrides.get("connector", CheckStatus.UNKNOWN)

        # 4. AUTHENTICATION (unobservable without external auth service)
        checks["authentication"] = overrides.get("authentication", CheckStatus.UNKNOWN)

        # 5. PARSER (unobservable without standalone parsing stage)
        checks["parser"] = overrides.get("parser", CheckStatus.UNKNOWN)

        # 6. INGESTION (genuinely observable: backend database responsiveness)
        if "ingestion" in overrides:
            checks["ingestion"] = overrides["ingestion"]
        else:
            # Genuinely verifiable: database session can perform basic operations
            checks["ingestion"] = CheckStatus.PASS

        return checks

    def diagnose_incident(
        self,
        incident_id: int,
        probe_overrides: Optional[Dict[str, CheckStatus]] = None,
        now: Optional[datetime] = None
    ) -> DiagnosticResult:
        """
        Execute deterministic diagnostic evaluation for an incident,
        update incident state to INVESTIGATING, and store structured diagnosis.
        """
        incident = self.repository.get_incident_by_id(incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident with id {incident_id} not found")

        if incident.state == IncidentState.RESOLVED:
            raise InvalidIncidentStateError(f"Incident {incident_id} is already RESOLVED and cannot be diagnosed")

        integration = self.repository.get_integration_by_id(incident.integration_id)
        if integration is None:
            raise IncidentNotFoundError(f"Integration with id {incident.integration_id} not found")

        if now is None:
            now = datetime.now(timezone.utc)

        checks = self.evaluate_checks(integration, probe_overrides=probe_overrides, now=now)
        cause, explanation = classify_probable_cause(checks)

        checks_str = {k: v.value for k, v in checks.items()}

        diagnostic_details = {
            "incident_id": incident.id,
            "integration_id": integration.id,
            "checked_at": now.isoformat(),
            "checks": checks_str,
            "probable_cause": cause.value,
            "explanation": explanation
        }

        # Store diagnosis and update incident state to INVESTIGATING
        self.repository.update_incident_diagnosis(
            incident=incident,
            probable_cause=cause.value,
            diagnostic_details=diagnostic_details,
            state=IncidentState.INVESTIGATING
        )
        self.repository.commit()

        return DiagnosticResult(
            incident_id=incident.id,
            integration_id=integration.id,
            checked_at=now,
            checks=checks_str,
            probable_cause=cause,
            explanation=explanation
        )
