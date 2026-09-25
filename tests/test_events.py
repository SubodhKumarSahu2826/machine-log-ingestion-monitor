from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError

from backend.models import Integration, MachineEvent
from backend.repositories.event_repository import EventRepository
from backend.schemas.event import EventCreate
from backend.services.event_service import DatabaseError, EventService


def test_health_check(client):
    """Verify health check endpoint returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_valid_event_ingestion(client, test_setup, db_session):
    """1. Test valid event ingestion creates event and returns 201."""
    event_id = "test-valid-001"
    now = datetime.now(timezone.utc)
    payload = {
        "event_id": event_id,
        "machine_id": test_setup["machine_id"],
        "integration_id": test_setup["integration_id"],
        "event_type": "temperature_reading",
        "occurred_at": now.isoformat(),
        "payload": {"temperature": 75.4, "unit": "celsius"}
    }

    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "success"
    assert data["event_id"] == event_id
    assert "received_at" in data

    # Verify database persistence
    event = db_session.query(MachineEvent).filter(MachineEvent.event_id == event_id).first()
    assert event is not None
    assert event.machine_id == test_setup["machine_id"]
    assert event.integration_id == test_setup["integration_id"]
    assert event.event_type == "temperature_reading"
    assert event.payload == {"temperature": 75.4, "unit": "celsius"}


def test_missing_required_field(client, test_setup):
    """2. Test missing required fields return 422 validation error."""
    now = datetime.now(timezone.utc)
    # Missing event_type and payload
    payload = {
        "event_id": "test-missing-001",
        "machine_id": test_setup["machine_id"],
        "integration_id": test_setup["integration_id"],
        "occurred_at": now.isoformat()
    }

    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 422


def test_invalid_timestamp(client, test_setup):
    """3. Test timezone-naive or malformed timestamps return 422."""
    # Naive timestamp without timezone
    payload_naive = {
        "event_id": "test-tz-001",
        "machine_id": test_setup["machine_id"],
        "integration_id": test_setup["integration_id"],
        "event_type": "status_check",
        "occurred_at": "2026-09-25T10:00:00",
        "payload": {"status": "ok"}
    }

    response_naive = client.post("/api/v1/events", json=payload_naive)
    assert response_naive.status_code == 422
    assert "timezone-aware" in response_naive.text

    # Malformed timestamp string
    payload_malformed = {
        "event_id": "test-tz-002",
        "machine_id": test_setup["machine_id"],
        "integration_id": test_setup["integration_id"],
        "event_type": "status_check",
        "occurred_at": "not-a-timestamp",
        "payload": {"status": "ok"}
    }
    response_malformed = client.post("/api/v1/events", json=payload_malformed)
    assert response_malformed.status_code == 422


def test_unknown_integration(client, test_setup):
    """4. Test event with unknown integration_id returns 404."""
    now = datetime.now(timezone.utc)
    payload = {
        "event_id": "test-unknown-int-001",
        "machine_id": test_setup["machine_id"],
        "integration_id": 999999,
        "event_type": "cycle_start",
        "occurred_at": now.isoformat(),
        "payload": {"cycle": 1}
    }

    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 404
    assert "999999 not found" in response.json()["detail"]


def test_invalid_machine_integration_relationship(client, test_setup):
    """5. Test mismatched machine_id and integration_id returns 400."""
    now = datetime.now(timezone.utc)
    # Use invalid machine_id for this integration
    mismatched_machine_id = test_setup["machine_id"] + 9999
    payload = {
        "event_id": "test-mismatch-001",
        "machine_id": mismatched_machine_id,
        "integration_id": test_setup["integration_id"],
        "event_type": "cycle_start",
        "occurred_at": now.isoformat(),
        "payload": {"cycle": 1}
    }

    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 400
    assert "not machine" in response.json()["detail"]


def test_duplicate_event_id(client, test_setup, db_session):
    """6. Test duplicate event_id is idempotent: returns 200 and does not duplicate in DB."""
    event_id = "test-dup-001"
    now = datetime.now(timezone.utc)
    payload = {
        "event_id": event_id,
        "machine_id": test_setup["machine_id"],
        "integration_id": test_setup["integration_id"],
        "event_type": "cycle_complete",
        "occurred_at": now.isoformat(),
        "payload": {"cycle": 42}
    }

    # First request: new event -> 201 Created
    res1 = client.post("/api/v1/events", json=payload)
    assert res1.status_code == 201
    assert res1.json()["status"] == "success"

    # Second request with exact same event_id: duplicate -> 200 OK
    res2 = client.post("/api/v1/events", json=payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "duplicate"
    assert res2.json()["event_id"] == event_id

    # Verify PostgreSQL contains exactly 1 record
    count = db_session.query(MachineEvent).filter(MachineEvent.event_id == event_id).count()
    assert count == 1


def test_last_seen_at_updated_after_successful_ingestion(client, test_setup, db_session):
    """7. Test Integration.last_seen_at is updated after successful ingestion."""
    event_id = "test-lastseen-001"
    now = datetime.now(timezone.utc)
    payload = {
        "event_id": event_id,
        "machine_id": test_setup["machine_id"],
        "integration_id": test_setup["integration_id"],
        "event_type": "ping",
        "occurred_at": now.isoformat(),
        "payload": {}
    }

    res = client.post("/api/v1/events", json=payload)
    assert res.status_code == 201
    received_at_str = res.json()["received_at"]
    received_at = datetime.fromisoformat(received_at_str)

    # Refresh integration from DB
    db_session.expire_all()
    integration = db_session.query(Integration).filter(Integration.id == test_setup["integration_id"]).first()
    assert integration.last_seen_at is not None
    # Compare with small tolerance for db timestamp resolution
    diff = abs((integration.last_seen_at - received_at).total_seconds())
    assert diff < 0.01


def test_last_seen_at_not_updated_by_duplicate_ingestion(client, test_setup, db_session):
    """8. Test duplicate ingestion does NOT update or advance last_seen_at."""
    event_id = "test-dup-lastseen-001"
    now = datetime.now(timezone.utc)
    payload = {
        "event_id": event_id,
        "machine_id": test_setup["machine_id"],
        "integration_id": test_setup["integration_id"],
        "event_type": "ping",
        "occurred_at": now.isoformat(),
        "payload": {}
    }

    # Initial ingestion
    res1 = client.post("/api/v1/events", json=payload)
    assert res1.status_code == 201

    db_session.expire_all()
    integration_initial = db_session.query(Integration).filter(Integration.id == test_setup["integration_id"]).first()
    first_last_seen_at = integration_initial.last_seen_at
    assert first_last_seen_at is not None

    # Duplicate ingestion
    res2 = client.post("/api/v1/events", json=payload)
    assert res2.status_code == 200

    db_session.expire_all()
    integration_after = db_session.query(Integration).filter(Integration.id == test_setup["integration_id"]).first()
    assert integration_after.last_seen_at == first_last_seen_at


def test_occurred_at_and_received_at_remain_distinct(client, test_setup, db_session):
    """9. Test occurred_at and received_at are distinct when machine event occurred in the past."""
    event_id = "test-distinct-times-001"
    past_time = datetime.now(timezone.utc) - timedelta(hours=3)
    payload = {
        "event_id": event_id,
        "machine_id": test_setup["machine_id"],
        "integration_id": test_setup["integration_id"],
        "event_type": "historical_log",
        "occurred_at": past_time.isoformat(),
        "payload": {"historical": True}
    }

    res = client.post("/api/v1/events", json=payload)
    assert res.status_code == 201

    event = db_session.query(MachineEvent).filter(MachineEvent.event_id == event_id).first()
    assert event is not None

    # occurred_at must match past_time (~3 hours ago)
    # received_at must match current server time
    time_difference = (event.received_at - event.occurred_at).total_seconds()
    assert time_difference > 10000  # at least ~2.7 hours difference


def test_out_of_order_event_accepted_without_corrupting_last_seen_at(client, test_setup, db_session):
    """10. Test an older/out-of-order event is accepted and last_seen_at reflects server reception time."""
    now = datetime.now(timezone.utc)

    # Event 1: Recent event (occurred 10 min ago)
    res1 = client.post("/api/v1/events", json={
        "event_id": "test-order-001",
        "machine_id": test_setup["machine_id"],
        "integration_id": test_setup["integration_id"],
        "event_type": "recent_event",
        "occurred_at": (now - timedelta(minutes=10)).isoformat(),
        "payload": {}
    })
    assert res1.status_code == 201
    db_session.expire_all()
    int1 = db_session.query(Integration).filter(Integration.id == test_setup["integration_id"]).first()
    last_seen_1 = int1.last_seen_at

    # Event 2: Delayed/out-of-order event (occurred 2 days ago, but received now)
    delayed_time = now - timedelta(days=2)
    res2 = client.post("/api/v1/events", json={
        "event_id": "test-order-002",
        "machine_id": test_setup["machine_id"],
        "integration_id": test_setup["integration_id"],
        "event_type": "delayed_event",
        "occurred_at": delayed_time.isoformat(),
        "payload": {}
    })
    assert res2.status_code == 201

    db_session.expire_all()
    int2 = db_session.query(Integration).filter(Integration.id == test_setup["integration_id"]).first()
    last_seen_2 = int2.last_seen_at

    # last_seen_at must reflect server reception time (>= last_seen_1), NOT rewound to 2 days ago
    assert last_seen_2 >= last_seen_1
    assert last_seen_2 > delayed_time


def test_database_failure_rolls_back_ingestion(db_session, test_setup):
    """11. Test database failure rolls back both event insertion and last_seen_at update."""
    repository = EventRepository(db_session)
    service = EventService(repository)

    # Record initial last_seen_at
    integration = repository.get_integration(test_setup["integration_id"])
    initial_last_seen = integration.last_seen_at

    event_id = "test-fail-rollback-001"
    event_data = EventCreate(
        event_id=event_id,
        machine_id=test_setup["machine_id"],
        integration_id=test_setup["integration_id"],
        event_type="fail_test",
        occurred_at=datetime.now(timezone.utc),
        payload={"test": "rollback"}
    )

    # Mock save_event_and_update_last_seen to simulate a database failure during commit
    with patch.object(repository, "save_event_and_update_last_seen", side_effect=SQLAlchemyError("Simulated DB Crash")):
        try:
            service.ingest_event(event_data)
            assert False, "Should have raised DatabaseError"
        except DatabaseError:
            pass

    # Verify event was NOT persisted
    event_in_db = repository.get_event_by_event_id(event_id)
    assert event_in_db is None

    # Verify last_seen_at was NOT modified
    db_session.expire_all()
    integration_after = repository.get_integration(test_setup["integration_id"])
    assert integration_after.last_seen_at == initial_last_seen


def test_extra_received_at_rejected(client, test_setup):
    """Verify that client attempting to send received_at is rejected with 422."""
    payload = {
        "event_id": "test-extra-001",
        "machine_id": test_setup["machine_id"],
        "integration_id": test_setup["integration_id"],
        "event_type": "status",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "payload": {}
    }
    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 422
    assert "Extra inputs are not permitted" in response.text
