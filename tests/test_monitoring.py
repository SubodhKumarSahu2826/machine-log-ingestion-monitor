from datetime import datetime, timezone, timedelta
import pytest

from backend.models import (
    Incident,
    IncidentState,
    Integration,
    IntegrationHealthState,
    Machine,
    RecoveryAttempt,
    Station,
)
from backend.repositories.monitoring_repository import MonitoringRepository
from backend.services.monitoring_service import (
    MonitoringService,
    calculate_freshness,
    determine_health_state,
)


@pytest.fixture
def monitor_integration(db_session):
    """Fixture providing a fresh isolated integration for monitoring tests."""
    station = db_session.query(Station).first()
    assert station is not None

    machine = db_session.query(Machine).filter(Machine.name == "Test_Monitor_Machine").first()
    if not machine:
        machine = Machine(name="Test_Monitor_Machine", station_id=station.id)
        db_session.add(machine)
        db_session.commit()
        db_session.refresh(machine)

    integration = db_session.query(Integration).filter(Integration.name == "Test_Monitor_Integration").first()
    if not integration:
        integration = Integration(
            name="Test_Monitor_Integration",
            type="API",
            machine_id=machine.id,
            expected_interval_seconds=30,
            warning_threshold_seconds=60,
            stale_threshold_seconds=120,
            health_state=IntegrationHealthState.HEALTHY,
            last_seen_at=None,
        )
        db_session.add(integration)
        db_session.commit()
        db_session.refresh(integration)
    else:
        integration.health_state = IntegrationHealthState.HEALTHY
        integration.last_seen_at = None
        db_session.commit()
        db_session.refresh(integration)

    # Clean existing incidents and recovery attempts for this integration
    incident_ids = [inc.id for inc in db_session.query(Incident.id).filter(Incident.integration_id == integration.id).all()]
    if incident_ids:
        db_session.query(RecoveryAttempt).filter(RecoveryAttempt.incident_id.in_(incident_ids)).delete(synchronize_session=False)
        db_session.query(Incident).filter(Incident.id.in_(incident_ids)).delete(synchronize_session=False)
        db_session.commit()

    yield integration

    # Cleanup incidents and recovery attempts
    incident_ids = [inc.id for inc in db_session.query(Incident.id).filter(Incident.integration_id == integration.id).all()]
    if incident_ids:
        db_session.query(RecoveryAttempt).filter(RecoveryAttempt.incident_id.in_(incident_ids)).delete(synchronize_session=False)
        db_session.query(Incident).filter(Incident.id.in_(incident_ids)).delete(synchronize_session=False)
        db_session.commit()


def test_fresh_integration_is_healthy():
    """1. Fresh integration with recent last_seen_at evaluates to HEALTHY."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    last_seen_at = now - timedelta(seconds=15)

    state = determine_health_state(
        last_seen_at=last_seen_at,
        now=now,
        warning_threshold_seconds=60,
        stale_threshold_seconds=120,
    )
    assert state == IntegrationHealthState.HEALTHY


def test_integration_approaching_threshold_is_warning():
    """2. Integration with freshness between warning and stale threshold evaluates to WARNING."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    last_seen_at = now - timedelta(seconds=75)

    state = determine_health_state(
        last_seen_at=last_seen_at,
        now=now,
        warning_threshold_seconds=60,
        stale_threshold_seconds=120,
    )
    assert state == IntegrationHealthState.WARNING


def test_integration_beyond_stale_threshold_is_stale():
    """3. Integration with freshness exceeding stale threshold evaluates to STALE."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    last_seen_at = now - timedelta(seconds=130)

    state = determine_health_state(
        last_seen_at=last_seen_at,
        now=now,
        warning_threshold_seconds=60,
        stale_threshold_seconds=120,
    )
    assert state == IntegrationHealthState.STALE


def test_integration_with_no_last_seen_at(monitor_integration, db_session):
    """4. Integration with last_seen_at=None evaluates to HEALTHY initial state without incidents."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    assert monitor_integration.last_seen_at is None

    # Pure function checks
    freshness = calculate_freshness(monitor_integration.last_seen_at, now)
    assert freshness is None

    state = determine_health_state(monitor_integration.last_seen_at, now)
    assert state == IntegrationHealthState.HEALTHY

    # Service evaluation check
    repo = MonitoringRepository(db_session)
    service = MonitoringService(repo)
    new_state, incident = service.evaluate_integration(monitor_integration, now=now)

    assert new_state == IntegrationHealthState.HEALTHY
    assert incident is None

    active_incidents = repo.get_active_incident(monitor_integration.id)
    assert active_incidents is None


def test_stale_creates_exactly_one_active_incident(monitor_integration, db_session):
    """5. An integration becoming STALE creates exactly one active incident."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    # Set last_seen_at to 200s ago (beyond stale threshold 120s)
    monitor_integration.last_seen_at = now - timedelta(seconds=200)
    db_session.commit()

    repo = MonitoringRepository(db_session)
    service = MonitoringService(repo)

    new_state, created_incident = service.evaluate_integration(monitor_integration, now=now)
    repo.commit()

    assert new_state == IntegrationHealthState.STALE
    assert created_incident is not None
    assert created_incident.integration_id == monitor_integration.id
    assert created_incident.state == IncidentState.OPEN
    assert "STALE" in created_incident.probable_cause

    # Verify directly in DB
    db_session.expire_all()
    incidents = db_session.query(Incident).filter(Incident.integration_id == monitor_integration.id).all()
    assert len(incidents) == 1


def test_repeated_monitoring_does_not_create_duplicate_incidents(monitor_integration, db_session):
    """6. Repeated monitoring cycles on an already STALE integration do not create duplicate incidents."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    monitor_integration.last_seen_at = now - timedelta(seconds=200)
    db_session.commit()

    repo = MonitoringRepository(db_session)
    service = MonitoringService(repo)

    # Cycle 1
    state1, inc1 = service.evaluate_integration(monitor_integration, now=now)
    repo.commit()
    assert state1 == IntegrationHealthState.STALE
    assert inc1 is not None

    # Cycle 2: 30 seconds later, still stale
    now2 = now + timedelta(seconds=30)
    state2, inc2 = service.evaluate_integration(monitor_integration, now=now2)
    repo.commit()
    assert state2 == IntegrationHealthState.STALE
    assert inc2 is None  # No new incident created!

    # Cycle 3: 60 seconds later, still stale
    now3 = now + timedelta(seconds=60)
    state3, inc3 = service.evaluate_integration(monitor_integration, now=now3)
    repo.commit()
    assert state3 == IntegrationHealthState.STALE
    assert inc3 is None

    # Verify total incidents count in database remains exactly 1
    db_session.expire_all()
    incidents = db_session.query(Incident).filter(Incident.integration_id == monitor_integration.id).all()
    assert len(incidents) == 1


def test_new_event_after_stale_changes_health_back_to_healthy(client, monitor_integration, db_session):
    """7. New event ingested after integration was STALE restores health to HEALTHY."""
    now = datetime.now(timezone.utc)

    # 1. Trigger STALE state
    repo = MonitoringRepository(db_session)
    service = MonitoringService(repo)
    monitor_integration.last_seen_at = now - timedelta(seconds=200)
    monitor_integration.health_state = IntegrationHealthState.STALE
    db_session.commit()

    # 2. Client sends a new event
    payload = {
        "event_id": "test-recover-event-001",
        "machine_id": monitor_integration.machine_id,
        "integration_id": monitor_integration.id,
        "event_type": "cycle_completed",
        "occurred_at": now.isoformat(),
        "payload": {"status": "ok"}
    }
    res = client.post("/api/v1/events", json=payload)
    assert res.status_code == 201

    # 3. Next monitoring cycle runs immediately after the new event
    db_session.expire_all()
    evaluation_time = datetime.now(timezone.utc)
    new_state, incident = service.evaluate_integration(monitor_integration, now=evaluation_time)
    repo.commit()

    assert new_state == IntegrationHealthState.HEALTHY
    assert incident is None

    # Verify DB health_state is HEALTHY
    db_session.expire_all()
    reloaded = repo.get_integration_by_id(monitor_integration.id)
    assert reloaded.health_state == IntegrationHealthState.HEALTHY


def test_freshness_uses_last_seen_at_rather_than_occurred_at(client, monitor_integration, db_session):
    """8. Freshness calculation uses server last_seen_at, ignoring historical occurred_at."""
    # Machine event was generated 10 hours ago (e.g. offline store-and-forward)
    ancient_occurred_at = datetime.now(timezone.utc) - timedelta(hours=10)

    payload = {
        "event_id": "test-store-forward-001",
        "machine_id": monitor_integration.machine_id,
        "integration_id": monitor_integration.id,
        "event_type": "store_and_forward",
        "occurred_at": ancient_occurred_at.isoformat(),
        "payload": {"historical": True}
    }

    # Ingest event now
    res = client.post("/api/v1/events", json=payload)
    assert res.status_code == 201

    # Evaluate freshness at current time
    db_session.expire_all()
    repo = MonitoringRepository(db_session)
    service = MonitoringService(repo)

    now = datetime.now(timezone.utc)
    state, incident = service.evaluate_integration(monitor_integration, now=now)

    # Must be HEALTHY because last_seen_at is ~0s old, NOT STALE from occurred_at (10h ago)
    assert state == IntegrationHealthState.HEALTHY
    assert incident is None


def test_threshold_boundary_behavior_is_deterministic():
    """9. Boundary checks at 59.9s, 60.0s, 119.9s, 120.0s are fully deterministic."""
    now = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)
    warning_threshold = 60
    stale_threshold = 120

    # 59.9s -> HEALTHY
    s1 = determine_health_state(now - timedelta(seconds=59.9), now, warning_threshold, stale_threshold)
    assert s1 == IntegrationHealthState.HEALTHY

    # 60.0s exact -> WARNING
    s2 = determine_health_state(now - timedelta(seconds=60.0), now, warning_threshold, stale_threshold)
    assert s2 == IntegrationHealthState.WARNING

    # 119.9s -> WARNING
    s3 = determine_health_state(now - timedelta(seconds=119.9), now, warning_threshold, stale_threshold)
    assert s3 == IntegrationHealthState.WARNING

    # 120.0s exact -> STALE
    s4 = determine_health_state(now - timedelta(seconds=120.0), now, warning_threshold, stale_threshold)
    assert s4 == IntegrationHealthState.STALE


def test_api_list_integrations(client, monitor_integration):
    """Test GET /api/v1/integrations returns valid integration list with health states."""
    res = client.get("/api/v1/integrations")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    matching = [i for i in data if i["id"] == monitor_integration.id]
    assert len(matching) == 1
    assert matching[0]["name"] == monitor_integration.name
    assert "health_state" in matching[0]
    assert "last_seen_at" in matching[0]
