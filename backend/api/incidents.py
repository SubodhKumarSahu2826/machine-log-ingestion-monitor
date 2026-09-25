from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Incident, IncidentState
from backend.repositories.monitoring_repository import MonitoringRepository
from backend.repositories.recovery_repository import RecoveryRepository
from backend.schemas.diagnostic import DiagnosticRequest, DiagnosticResult
from backend.schemas.incident import IncidentResponse
from backend.schemas.recovery import (
    RecoveryAttemptResponse,
    RecoveryRequest,
    RecoveryResponse,
    VerificationResponse,
)
from backend.services.diagnostic_service import (
    DiagnosticService,
    IncidentNotFoundError as DiagIncidentNotFoundError,
    InvalidIncidentStateError as DiagInvalidStateError,
)
from backend.services.recovery_service import (
    ConcurrentRecoveryError,
    IncidentNotFoundError,
    InvalidIncidentStateError,
    MaxAttemptsExceededError,
    RecoveryDatabaseError,
    RecoveryService,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])


def get_diagnostic_service(db: Session = Depends(get_db)) -> DiagnosticService:
    """Dependency provider for DiagnosticService."""
    repo = MonitoringRepository(db)
    return DiagnosticService(repo)


def get_recovery_service(db: Session = Depends(get_db)) -> RecoveryService:
    """Dependency provider for RecoveryService."""
    repo = RecoveryRepository(db)
    return RecoveryService(repo)


def get_recovery_repository(db: Session = Depends(get_db)) -> RecoveryRepository:
    """Dependency provider for RecoveryRepository."""
    return RecoveryRepository(db)


def get_monitoring_repository(db: Session = Depends(get_db)) -> MonitoringRepository:
    """Dependency provider for MonitoringRepository."""
    return MonitoringRepository(db)


@router.get(
    "",
    response_model=List[IncidentResponse],
    summary="List incidents"
)
def list_incidents(
    integration_id: Optional[int] = Query(None, description="Filter by integration ID"),
    state: Optional[str] = Query(None, description="Filter by incident state"),
    db: Session = Depends(get_db)
) -> List[IncidentResponse]:
    """Retrieve incidents with optional filtering by integration and state."""
    query = db.query(Incident)
    if integration_id is not None:
        query = query.filter(Incident.integration_id == integration_id)
    if state is not None:
        query = query.filter(Incident.state == state)
    return query.order_by(Incident.created_at.desc()).all()


@router.post(
    "/{incident_id}/diagnose",
    response_model=DiagnosticResult,
    summary="Run deterministic diagnostics on an incident"
)
def diagnose_incident(
    incident_id: int,
    request: Optional[DiagnosticRequest] = None,
    service: DiagnosticService = Depends(get_diagnostic_service)
) -> DiagnosticResult:
    """
    Execute deterministic diagnostic checks for an incident.
    Returns structured check results, probable cause classification, and explanation.
    """
    try:
        overrides = request.probe_overrides if request else None
        return service.diagnose_incident(incident_id, probe_overrides=overrides)
    except DiagIncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DiagInvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{incident_id}/recover",
    response_model=RecoveryResponse,
    summary="Initiate controlled incident recovery"
)
def recover_incident(
    incident_id: int,
    request: RecoveryRequest,
    service: RecoveryService = Depends(get_recovery_service)
) -> RecoveryResponse:
    """
    Initiate controlled recovery (RETRY_CONNECTION, RECONNECT_CONNECTOR, REPLAY_EVENTS).
    Moves incident to RECOVERING and records a RecoveryAttempt.
    If timeout_seconds is provided, waits synchronously for verification.
    """
    try:
        incident, attempt, verified, message = service.execute_recovery(
            incident_id=incident_id,
            action=request.action,
            timeout_seconds=request.timeout_seconds
        )
        return RecoveryResponse(
            incident_id=incident.id,
            integration_id=incident.integration_id,
            incident_state=incident.state.value,
            attempt=RecoveryAttemptResponse.model_validate(attempt),
            message=message
        )
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConcurrentRecoveryError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (InvalidIncidentStateError, MaxAttemptsExceededError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecoveryDatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post(
    "/{incident_id}/verify",
    response_model=VerificationResponse,
    summary="Verify recovery outcome against telemetry"
)
def verify_recovery(
    incident_id: int,
    service: RecoveryService = Depends(get_recovery_service)
) -> VerificationResponse:
    """
    Verify recovery strictly against database telemetry:
    Confirms a new valid MachineEvent arrived after recovery started, and last_seen_at advanced.
    Resolves incident on success; records attempt failure and escalates on max attempts.
    """
    try:
        verified, incident, attempt, message = service.verify_recovery(incident_id)
        return VerificationResponse(
            incident_id=incident.id,
            integration_id=incident.integration_id,
            incident_state=incident.state.value,
            verified=verified,
            message=message,
            attempt=RecoveryAttemptResponse.model_validate(attempt) if attempt else None
        )
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidIncidentStateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecoveryDatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get(
    "/{incident_id}/recovery-attempts",
    response_model=List[RecoveryAttemptResponse],
    summary="Get recovery attempts for an incident"
)
def get_recovery_attempts(
    incident_id: int,
    repo: RecoveryRepository = Depends(get_recovery_repository)
) -> List[RecoveryAttemptResponse]:
    """Retrieve the complete history of recovery attempts for an incident."""
    incident = repo.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident with id {incident_id} not found")
    attempts = repo.get_recovery_attempts(incident_id)
    return [RecoveryAttemptResponse.model_validate(a) for a in attempts]


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get incident details and diagnostic result"
)
def get_incident(
    incident_id: int,
    repo: MonitoringRepository = Depends(get_monitoring_repository)
) -> IncidentResponse:
    """Retrieve an incident with its probable cause and stored diagnostic details."""
    incident = repo.get_incident_by_id(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with id {incident_id} not found"
        )
    return incident
