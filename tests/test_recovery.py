from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.models import (
    AuditEvent,
    Incident,
    IncidentState,
    Integration,
    IntegrationHealthState,
    Machine,
    MachineEvent,
    RecoveryAttempt,
    Station,
)
from backend.repositories.recovery_repository import RecoveryRepository
from backend.schemas.recovery import RecoveryAction
from backend.services.recovery_service import (
    ConcurrentRecoveryError,
    IncidentNotFoundError,
    InvalidIncidentStateError,
    MaxAttemptsExceededError,
    RecoveryDatabaseError,
    RecoveryService,
)


@pytest.fixture
def recovery_fixture(db_session):
    """Fixture providing a dedicated test machine, integration, and incident."""
    station = db_session.query(Station).first()
    assert station is not None

    machine = db_session.query(Machine).filter(Machine.name == "Test_Recovery_Machine").first()
    if not machine:
        machine = Machine(name="Test_Recovery_Machine", station_id=station.id)
        db_session.add(machine)
        db_session.commit()
        db_session.refresh(machine)

    integration = db_session.query(Integration).filter(Integration.name == "Test_Recovery_Integration").first()
    if not integration:
        integration = Integration(
            name="Test_Recovery_Integration",
            type="API",
            machine_id=machine.id,
            expected_interval_seconds=30,
            warning_threshold_seconds=60,
            stale_threshold_seconds=120,
            health_state=IntegrationHealthState.STALE,
            last_seen_at=datetime.now(timezone.utc) - timedelta(seconds=200),
        )
        db_session.add(integration)
        db_session.commit()
        db_session.refresh(integration)
    else:
        integration.health_state = IntegrationHealthState.STALE
        integration.last_seen_at = datetime.now(timezone.utc) - timedelta(seconds=200)
        db_session.commit()
        db_session.refresh(integration)

    incident = Incident(
        integration_id=integration.id,
        probable_cause="Integration STALE: no events received for 200s",
        state=IncidentState.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(seconds=190),
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    yield {
        "machine": machine,
        "integration": integration,
        "incident": incident
    }

    # Teardown
    db_session.query(RecoveryAttempt).filter(RecoveryAttempt.incident_id == incident.id).delete(synchronize_session=False)
    db_session.query(AuditEvent).filter(
        AuditEvent.entity_type == "Incident",
        AuditEvent.entity_id == incident.id
    ).delete(synchronize_session=False)
    db_session.query(Incident).filter(Incident.id == incident.id).delete(synchronize_session=False)
    db_session.query(MachineEvent).filter(MachineEvent.integration_id == integration.id).delete(synchronize_session=False)
    db_session.commit()


def test_successful_recovery_action(db_session, recovery_fixture):
    """1. Test that calling recovery initiates the action cleanly."""
    repo = RecoveryRepository(db_session)
    service = RecoveryService(repo, max_attempts=3)
    incident = recovery_fixture["incident"]

    inc, attempt = service.initiate_recovery(incident.id, RecoveryAction.RETRY_CONNECTION)

    assert inc.id == incident.id
    assert attempt.action == RecoveryAction.RETRY_CONNECTION.value
    assert attempt.status == "STARTED"
    assert attempt.attempted_at is not None


def test_recovery_moves_incident_to_recovering(db_session, recovery_fixture):
    """2. Test recovery moves incident and integration to RECOVERING."""
    repo = RecoveryRepository(db_session)
    service = RecoveryService(repo, max_attempts=3)
    incident = recovery_fixture["incident"]
    integration = recovery_fixture["integration"]

    inc, _ = service.initiate_recovery(incident.id, RecoveryAction.RECONNECT_CONNECTOR)

    assert inc.state == IncidentState.RECOVERING
    db_session.refresh(integration)
    assert integration.health_state == IntegrationHealthState.RECOVERING


def test_recovery_attempt_is_persisted(db_session, recovery_fixture):
    """3. Test recovery attempt is persisted in database with timestamps."""
    repo = RecoveryRepository(db_session)
    service = RecoveryService(repo, max_attempts=3)
    incident = recovery_fixture["incident"]

    _, attempt = service.initiate_recovery(incident.id, RecoveryAction.REPLAY_EVENTS)

    persisted = repo.get_latest_recovery_attempt(incident.id)
    assert persisted is not None
    assert persisted.id == attempt.id
    assert persisted.action == "REPLAY_EVENTS"
    assert persisted.status == "STARTED"
    assert persisted.attempted_at is not None


def test_successful_new_event_verifies_recovery(db_session, recovery_fixture):
    """4. Test that a new valid event received after recovery verifies recovery."""
    repo = RecoveryRepository(db_session)
    service = RecoveryService(repo, max_attempts=3)
    incident = recovery_fixture["incident"]
    integration = recovery_fixture["integration"]
    machine = recovery_fixture["machine"]

    start_time = datetime.now(timezone.utc)
    service.initiate_recovery(incident.id, RecoveryAction.RETRY_CONNECTION, now=start_time)

    # Ingest a new machine event after start_time
    event_time = start_time + timedelta(seconds=2)
    event = MachineEvent(
        event_id="recov-event-1",
        machine_id=machine.id,
        integration_id=integration.id,
        event_type="cycle_completed",
        occurred_at=event_time,
        received_at=event_time,
        payload={"result": "PASS"}
    )
    db_session.add(event)
    integration.last_seen_at = event_time
    db_session.commit()

    verified, updated_inc, attempt, msg = service.verify_recovery(incident.id, now=event_time + timedelta(seconds=1))

    assert verified is True
    assert "Recovery successfully verified" in msg
    assert attempt.status == "SUCCESS"
    assert attempt.completed_at is not None


def test_verified_recovery_resolves_incident(db_session, recovery_fixture):
    """5. Test that verified recovery moves incident to RESOLVED and integration to HEALTHY."""
    repo = RecoveryRepository(db_session)
    service = RecoveryService(repo, max_attempts=3)
    incident = recovery_fixture["incident"]
    integration = recovery_fixture["integration"]
    machine = recovery_fixture["machine"]

    start_time = datetime.now(timezone.utc)
    service.initiate_recovery(incident.id, RecoveryAction.RETRY_CONNECTION, now=start_time)

    # Ingest event
    event_time = start_time + timedelta(seconds=1)
    event = MachineEvent(
        event_id="recov-event-2",
        machine_id=machine.id,
        integration_id=integration.id,
        event_type="cycle_completed",
        occurred_at=event_time,
        received_at=event_time,
        payload={"status": "OK"}
    )
    db_session.add(event)
    integration.last_seen_at = event_time
    db_session.commit()

    service.verify_recovery(incident.id)

    db_session.refresh(incident)
    db_session.refresh(integration)
    assert incident.state == IncidentState.RESOLVED
    assert incident.resolved_at is not None
    assert integration.health_state == IntegrationHealthState.HEALTHY


def test_recovery_without_new_event_fails(db_session, recovery_fixture):
    """6. Test that recovery verification without a new event fails and marks attempt FAILURE."""
    repo = RecoveryRepository(db_session)
    service = RecoveryService(repo, max_attempts=3)
    incident = recovery_fixture["incident"]

    service.initiate_recovery(incident.id, RecoveryAction.RETRY_CONNECTION)

    # Verify without any new event
    verified, updated_inc, attempt, msg = service.verify_recovery(incident.id)

    assert verified is False
    assert attempt.status == "FAILURE"
    assert "Verification failed: no fresh machine event" in attempt.result_message
    assert updated_inc.state == IncidentState.FAILED


def test_maximum_recovery_attempts_enforced(db_session, recovery_fixture):
    """7. Test maximum recovery attempts (default 3) are strictly enforced."""
    repo = RecoveryRepository(db_session)
    service = RecoveryService(repo, max_attempts=3)
    incident = recovery_fixture["incident"]

    # Pre-populate 3 failed recovery attempts
    for i in range(3):
        att = repo.create_recovery_attempt(incident.id, "RETRY_CONNECTION", status="FAILURE")
        att.completed_at = datetime.now(timezone.utc)
    db_session.commit()

    # Attempting a 4th recovery must be rejected and escalate incident
    with pytest.raises(MaxAttemptsExceededError) as exc_info:
        service.initiate_recovery(incident.id, RecoveryAction.RETRY_CONNECTION)

    assert "Maximum recovery attempts (3) exceeded" in str(exc_info.value)
    db_session.refresh(incident)
    assert incident.state == IncidentState.ESCALATED


def test_permanent_failure_escalates(db_session, recovery_fixture):
    """8. Test permanent failure escalates incident to ESCALATED and integration to FAILED."""
    repo = RecoveryRepository(db_session)
    service = RecoveryService(repo, max_attempts=3)
    incident = recovery_fixture["incident"]
    integration = recovery_fixture["integration"]

    # Attempt 1: Fails
    service.initiate_recovery(incident.id, RecoveryAction.RETRY_CONNECTION)
    service.verify_recovery(incident.id)
    db_session.refresh(incident)
    assert incident.state == IncidentState.FAILED

    # Attempt 2: Fails
    service.initiate_recovery(incident.id, RecoveryAction.RECONNECT_CONNECTOR)
    service.verify_recovery(incident.id)
    db_session.refresh(incident)
    assert incident.state == IncidentState.FAILED

    # Attempt 3: Fails -> Reaches max attempts (3) -> ESCALATED
    service.initiate_recovery(incident.id, RecoveryAction.REPLAY_EVENTS)
    verified, inc, attempt, msg = service.verify_recovery(incident.id)

    assert verified is False
    assert "Incident ESCALATED" in msg
    db_session.refresh(incident)
    db_session.refresh(integration)
    assert incident.state == IncidentState.ESCALATED
    assert integration.health_state == IntegrationHealthState.FAILED


def test_concurrent_recovery_is_rejected(db_session, recovery_fixture):
    """9. Test concurrent recovery on the same incident or integration is rejected."""
    repo = RecoveryRepository(db_session)
    service = RecoveryService(repo, max_attempts=3)
    incident = recovery_fixture["incident"]

    # First recovery initiates successfully
    service.initiate_recovery(incident.id, RecoveryAction.RETRY_CONNECTION)

    # Second recovery request on the same incident must be rejected
    with pytest.raises(ConcurrentRecoveryError) as exc_info:
        service.initiate_recovery(incident.id, RecoveryAction.RETRY_CONNECTION)
    assert "already in RECOVERING state" in str(exc_info.value)


def test_duplicate_event_during_verification_does_not_falsely_verify(db_session, recovery_fixture, client):
    """10. Test duplicate event does not advance last_seen_at and does not falsely verify recovery."""
    repo = RecoveryRepository(db_session)
    service = RecoveryService(repo, max_attempts=3)
    incident = recovery_fixture["incident"]
    integration = recovery_fixture["integration"]
    machine = recovery_fixture["machine"]

    # Ingest an original event prior to recovery
    orig_payload = {
        "event_id": "test-dup-10",
        "machine_id": machine.id,
        "integration_id": integration.id,
        "event_type": "cycle_completed",
        "occurred_at": (datetime.now(timezone.utc) - timedelta(seconds=50)).isoformat(),
        "payload": {"result": "PASS"}
    }
    r = client.post("/api/v1/events", json=orig_payload)
    assert r.status_code == 201

    db_session.refresh(integration)
    last_seen_before = integration.last_seen_at

    # Initiate recovery
    service.initiate_recovery(incident.id, RecoveryAction.RETRY_CONNECTION)

    # Resend DUPLICATE event (same event_id)
    dup_resp = client.post("/api/v1/events", json=orig_payload)
    assert dup_resp.status_code == 200 # Idempotency returns 200

    db_session.refresh(integration)
    # last_seen_at must NOT have advanced
    assert integration.last_seen_at == last_seen_before

    # Verification must fail because no new event was received after recovery started
    verified, _, attempt, _ = service.verify_recovery(incident.id)
    assert verified is False
    assert attempt.status == "FAILURE"


def test_last_seen_at_must_actually_advance(db_session, recovery_fixture):
    """11. Test that last_seen_at must actually advance beyond recovery_started_at."""
    repo = RecoveryRepository(db_session)
    service = RecoveryService(repo, max_attempts=3)
    incident = recovery_fixture["incident"]
    integration = recovery_fixture["integration"]

    now = datetime.now(timezone.utc)
    integration.last_seen_at = now - timedelta(seconds=100)
    db_session.commit()

    # Recovery started at `now`
    service.initiate_recovery(incident.id, RecoveryAction.RETRY_CONNECTION, now=now)

    # Verification run without updating integration.last_seen_at
    verified, _, attempt, _ = service.verify_recovery(incident.id, now=now + timedelta(seconds=5))
    assert verified is False
    assert attempt.status == "FAILURE"


def test_invalid_incident_state_rejects_recovery(db_session, recovery_fixture):
    """12. Test that an invalid incident state (e.g. RESOLVED) rejects recovery."""
    repo = RecoveryRepository(db_session)
    service = RecoveryService(repo, max_attempts=3)
    incident = recovery_fixture["incident"]

    incident.state = IncidentState.RESOLVED
    db_session.commit()

    with pytest.raises(InvalidIncidentStateError) as exc_info:
        service.initiate_recovery(incident.id, RecoveryAction.RETRY_CONNECTION)
    assert "already RESOLVED" in str(exc_info.value)


def test_recovery_database_failure_rolls_back(db_session, recovery_fixture):
    """13. Test that database failure during recovery rolls back transaction."""
    mock_db = MagicMock()
    mock_db.commit.side_effect = SQLAlchemyError("DB Connection Lost")
    repo = RecoveryRepository(mock_db)
    service = RecoveryService(repo)

    mock_incident = MagicMock()
    mock_incident.id = 999
    mock_incident.integration_id = 1
    mock_incident.state = IncidentState.OPEN
    repo.get_incident = MagicMock(return_value=mock_incident)
    repo.get_recovering_incident_for_integration = MagicMock(return_value=None)
    repo.count_failed_attempts = MagicMock(return_value=0)

    with pytest.raises(RecoveryDatabaseError):
        service.initiate_recovery(999, RecoveryAction.RETRY_CONNECTION)

    mock_db.rollback.assert_called_once()


def test_e2e_successful_recovery_path(client, db_session, recovery_fixture):
    """Integration test: STALE -> DIAGNOSE -> RECOVER -> POST NEW EVENT -> VERIFY -> RESOLVED."""
    incident = recovery_fixture["incident"]
    integration = recovery_fixture["integration"]
    machine = recovery_fixture["machine"]

    # 1. DIAGNOSE
    diag_resp = client.post(f"/api/v1/incidents/{incident.id}/diagnose")
    assert diag_resp.status_code == 200

    # 2. RECOVER
    recov_resp = client.post(
        f"/api/v1/incidents/{incident.id}/recover",
        json={"action": "RETRY_CONNECTION"}
    )
    assert recov_resp.status_code == 200
    data = recov_resp.json()
    assert data["incident_state"] == "RECOVERING"
    assert data["attempt"]["status"] == "STARTED"

    # 3. POST NEW EVENT
    new_event = {
        "event_id": f"e2e-success-{datetime.now().timestamp()}",
        "machine_id": machine.id,
        "integration_id": integration.id,
        "event_type": "cycle_completed",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "payload": {"cycle": 100, "result": "PASS"}
    }
    event_resp = client.post("/api/v1/events", json=new_event)
    assert event_resp.status_code == 201

    # 4. VERIFY
    verify_resp = client.post(f"/api/v1/incidents/{incident.id}/verify")
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["verified"] is True
    assert v_data["incident_state"] == "RESOLVED"

    # Check database state
    db_session.refresh(incident)
    db_session.refresh(integration)
    assert incident.state == IncidentState.RESOLVED
    assert integration.health_state == IntegrationHealthState.HEALTHY


def test_e2e_failure_path_to_escalation(client, db_session, recovery_fixture):
    """Integration test: STALE -> RECOVER -> NO EVENT -> RETRY (x3) -> ESCALATED."""
    incident = recovery_fixture["incident"]
    integration = recovery_fixture["integration"]

    # Attempt 1
    r1 = client.post(f"/api/v1/incidents/{incident.id}/recover", json={"action": "RETRY_CONNECTION"})
    assert r1.status_code == 200
    v1 = client.post(f"/api/v1/incidents/{incident.id}/verify")
    assert v1.status_code == 200
    assert v1.json()["verified"] is False
    assert v1.json()["incident_state"] == "FAILED"

    # Attempt 2
    r2 = client.post(f"/api/v1/incidents/{incident.id}/recover", json={"action": "RECONNECT_CONNECTOR"})
    assert r2.status_code == 200
    v2 = client.post(f"/api/v1/incidents/{incident.id}/verify")
    assert v2.status_code == 200
    assert v2.json()["verified"] is False
    assert v2.json()["incident_state"] == "FAILED"

    # Attempt 3 (Final attempt)
    r3 = client.post(f"/api/v1/incidents/{incident.id}/recover", json={"action": "REPLAY_EVENTS"})
    assert r3.status_code == 200
    v3 = client.post(f"/api/v1/incidents/{incident.id}/verify")
    assert v3.status_code == 200
    assert v3.json()["verified"] is False
    assert v3.json()["incident_state"] == "ESCALATED"

    # Check integration is marked FAILED
    db_session.refresh(integration)
    assert integration.health_state == IntegrationHealthState.FAILED

    # Attempt 4 should be rejected with 400 Bad Request
    r4 = client.post(f"/api/v1/incidents/{incident.id}/recover", json={"action": "RETRY_CONNECTION"})
    assert r4.status_code == 400
    assert "ESCALATED" in r4.json()["detail"]


def test_api_get_recovery_attempts(client, db_session, recovery_fixture):
    """Test GET /api/v1/incidents/{incident_id}/recovery-attempts returns all attempts."""
    incident = recovery_fixture["incident"]

    client.post(f"/api/v1/incidents/{incident.id}/recover", json={"action": "RETRY_CONNECTION"})
    client.post(f"/api/v1/incidents/{incident.id}/verify")

    resp = client.get(f"/api/v1/incidents/{incident.id}/recovery-attempts")
    assert resp.status_code == 200
    attempts = resp.json()
    assert len(attempts) >= 1
    assert attempts[0]["action"] == "RETRY_CONNECTION"
    assert attempts[0]["status"] == "FAILURE"
