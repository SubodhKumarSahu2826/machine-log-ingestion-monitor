import pytest
from fastapi.testclient import TestClient

from backend.database import SessionLocal, engine
from backend.main import app
from backend.models import (
    Integration,
    IntegrationHealthState,
    Machine,
    MachineEvent,
    Station,
)


@pytest.fixture(scope="session")
def check_db():
    """Ensure database connection is active."""
    with engine.connect() as conn:
        pass


@pytest.fixture
def db_session():
    """Yield a database session and ensure clean close."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """Provide a FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def test_setup(db_session):
    """
    Ensure a dedicated machine and integration exist for testing,
    and clean up test machine events afterwards.
    """
    station = db_session.query(Station).first()
    assert station is not None, "Database must have seed data"

    machine = db_session.query(Machine).filter(Machine.name == "Test_Machine_Ingest").first()
    if not machine:
        machine = Machine(name="Test_Machine_Ingest", station_id=station.id)
        db_session.add(machine)
        db_session.commit()
        db_session.refresh(machine)

    integration = db_session.query(Integration).filter(Integration.name == "Test_Integration_Ingest").first()
    if not integration:
        integration = Integration(
            name="Test_Integration_Ingest",
            type="API",
            machine_id=machine.id,
            expected_interval_seconds=30,
            health_state=IntegrationHealthState.HEALTHY,
            last_seen_at=None
        )
        db_session.add(integration)
        db_session.commit()
        db_session.refresh(integration)
    else:
        integration.last_seen_at = None
        db_session.commit()
        db_session.refresh(integration)

    yield {
        "machine_id": machine.id,
        "integration_id": integration.id,
        "machine": machine,
        "integration": integration
    }

    # Teardown: delete test events created during test
    db_session.query(MachineEvent).filter(
        (MachineEvent.integration_id == integration.id) | (MachineEvent.event_id.like("test-%"))
    ).delete(synchronize_session=False)
    db_session.commit()
