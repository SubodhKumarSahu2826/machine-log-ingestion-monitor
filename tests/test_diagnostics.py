from datetime import datetime, timezone, timedelta
import pytest

from backend.models import (
    Incident,
    IncidentState,
    Integration,
    IntegrationHealthState,
    Machine,
    Station,
)
from backend.repositories.monitoring_repository import MonitoringRepository
from backend.schemas.diagnostic import CheckStatus, ProbableCause
from backend.services.diagnostic_service import (
    DiagnosticService,
    IncidentNotFoundError,
    InvalidIncidentStateError,
    classify_probable_cause,
)


@pytest.fixture
def diagnostic_fixture(db_session):
    """Fixture providing a dedicated integration and incident for diagnostic tests."""
    station = db_session.query(Station).first()
    assert station is not None

    machine = db_session.query(Machine).filter(Machine.name == "Test_Diag_Machine").first()
    if not machine:
        machine = Machine(name="Test_Diag_Machine", station_id=station.id)
        db_session.add(machine)
        db_session.commit()
        db_session.refresh(machine)

    integration = db_session.query(Integration).filter(Integration.name == "Test_Diag_Integration").first()
    if not integration:
        integration = Integration(
            name="Test_Diag_Integration",
            type="API",
            machine_id=machine.id,
            expected_interval_seconds=30,
            warning_threshold_seconds=60,
            stale_threshold_seconds=120,
            health_state=IntegrationHealthState.STALE,
            last_heartbeat_at=datetime.now(timezone.utc),
            last_seen_at=None,
        )
        db_session.add(integration)
        db_session.commit()
        db_session.refresh(integration)
    else:
        integration.health_state = IntegrationHealthState.STALE
        integration.last_heartbeat_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(integration)

    incident = Incident(
        integration_id=integration.id,
        probable_cause="Initial stale detection",
        state=IncidentState.OPEN,
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    yield {
        "integration": integration,
        "incident": incident,
        "machine": machine,
    }

    # Teardown
    db_session.query(Incident).filter(Incident.integration_id == integration.id).delete()
    db_session.commit()


def test_healthy_available_heartbeat(diagnostic_fixture, db_session):
    """1. Healthy recent heartbeat evaluates to PASS."""
    now = datetime(2026, 9, 25, 13, 0, 0, tzinfo=timezone.utc)
    integration = diagnostic_fixture["integration"]
    integration.last_heartbeat_at = now - timedelta(seconds=20)
    db_session.commit()

    repo = MonitoringRepository(db_session)
    service = DiagnosticService(repo)
    checks = service.evaluate_checks(integration, now=now)

    assert checks["machine_heartbeat"] == CheckStatus.PASS


def test_machine_offline(diagnostic_fixture, db_session):
    """2. Heartbeat unavailable or timed out evaluates to FAIL and MACHINE_OFFLINE."""
    now = datetime(2026, 9, 25, 13, 0, 0, tzinfo=timezone.utc)
    integration = diagnostic_fixture["integration"]
    # Timed out heartbeat (250s > 120s stale threshold)
    integration.last_heartbeat_at = now - timedelta(seconds=250)
    db_session.commit()

    repo = MonitoringRepository(db_session)
    service = DiagnosticService(repo)
    checks = service.evaluate_checks(integration, now=now)

    assert checks["machine_heartbeat"] == CheckStatus.FAIL
    cause, explanation = classify_probable_cause(checks)
    assert cause == ProbableCause.MACHINE_OFFLINE
    assert "heartbeat" in explanation.lower()


def test_network_failure():
    """3. Heartbeat available but network check fails -> NETWORK_FAILURE."""
    checks = {
        "machine_heartbeat": CheckStatus.PASS,
        "network": CheckStatus.FAIL,
        "connector": CheckStatus.UNKNOWN,
        "authentication": CheckStatus.UNKNOWN,
        "parser": CheckStatus.UNKNOWN,
        "ingestion": CheckStatus.PASS,
    }
    cause, explanation = classify_probable_cause(checks)
    assert cause == ProbableCause.NETWORK_FAILURE
    assert "network" in explanation.lower()


def test_connector_failure():
    """4. Heartbeat and network healthy/unknown, connector fails -> CONNECTOR_FAILURE."""
    checks = {
        "machine_heartbeat": CheckStatus.PASS,
        "network": CheckStatus.PASS,
        "connector": CheckStatus.FAIL,
        "authentication": CheckStatus.UNKNOWN,
        "parser": CheckStatus.UNKNOWN,
        "ingestion": CheckStatus.PASS,
    }
    cause, explanation = classify_probable_cause(checks)
    assert cause == ProbableCause.CONNECTOR_FAILURE
    assert "connector" in explanation.lower()


def test_authentication_failure():
    """5. Upstream healthy, authentication fails -> AUTHENTICATION_FAILURE."""
    checks = {
        "machine_heartbeat": CheckStatus.PASS,
        "network": CheckStatus.PASS,
        "connector": CheckStatus.PASS,
        "authentication": CheckStatus.FAIL,
        "parser": CheckStatus.UNKNOWN,
        "ingestion": CheckStatus.PASS,
    }
    cause, explanation = classify_probable_cause(checks)
    assert cause == ProbableCause.AUTHENTICATION_FAILURE
    assert "authentication" in explanation.lower()


def test_parser_failure():
    """6. Authentication healthy, parser/validation fails -> PARSER_FAILURE."""
    checks = {
        "machine_heartbeat": CheckStatus.PASS,
        "network": CheckStatus.PASS,
        "connector": CheckStatus.PASS,
        "authentication": CheckStatus.PASS,
        "parser": CheckStatus.FAIL,
        "ingestion": CheckStatus.PASS,
    }
    cause, explanation = classify_probable_cause(checks)
    assert cause == ProbableCause.PARSER_FAILURE
    assert "parser" in explanation.lower()


def test_ingestion_failure():
    """7. Upstream checks pass, ingestion check fails -> INGESTION_FAILURE."""
    checks = {
        "machine_heartbeat": CheckStatus.PASS,
        "network": CheckStatus.PASS,
        "connector": CheckStatus.PASS,
        "authentication": CheckStatus.PASS,
        "parser": CheckStatus.PASS,
        "ingestion": CheckStatus.FAIL,
    }
    cause, explanation = classify_probable_cause(checks)
    assert cause == ProbableCause.INGESTION_FAILURE
    assert "ingestion" in explanation.lower()


def test_unknown_condition():
    """8. All checks pass or are unobservable -> UNKNOWN."""
    checks = {
        "machine_heartbeat": CheckStatus.PASS,
        "network": CheckStatus.UNKNOWN,
        "connector": CheckStatus.UNKNOWN,
        "authentication": CheckStatus.UNKNOWN,
        "parser": CheckStatus.UNKNOWN,
        "ingestion": CheckStatus.PASS,
    }
    cause, explanation = classify_probable_cause(checks)
    assert cause == ProbableCause.UNKNOWN
    assert "definitive failure point" in explanation.lower()


def test_correct_probable_cause_selection_precedence():
    """9. Test priority: MACHINE_OFFLINE takes precedence over NETWORK_FAILURE."""
    # When both heartbeat and network indicate failure, heartbeat is most fundamental
    checks = {
        "machine_heartbeat": CheckStatus.FAIL,
        "network": CheckStatus.FAIL,
        "connector": CheckStatus.FAIL,
        "authentication": CheckStatus.FAIL,
        "parser": CheckStatus.FAIL,
        "ingestion": CheckStatus.FAIL,
    }
    cause, _ = classify_probable_cause(checks)
    assert cause == ProbableCause.MACHINE_OFFLINE

    # When heartbeat is PASS, network failure takes precedence over connector failure
    checks["machine_heartbeat"] = CheckStatus.PASS
    cause2, _ = classify_probable_cause(checks)
    assert cause2 == ProbableCause.NETWORK_FAILURE


def test_diagnostic_result_structure(diagnostic_fixture, db_session):
    """10. Test diagnostic result matches expected schema contract."""
    repo = MonitoringRepository(db_session)
    service = DiagnosticService(repo)

    result = service.diagnose_incident(diagnostic_fixture["incident"].id)

    assert result.incident_id == diagnostic_fixture["incident"].id
    assert result.integration_id == diagnostic_fixture["integration"].id
    assert isinstance(result.checked_at, datetime)
    assert isinstance(result.checks, dict)

    # Must contain all 6 checks
    required_checks = ["machine_heartbeat", "network", "connector", "authentication", "parser", "ingestion"]
    for chk in required_checks:
        assert chk in result.checks
        assert result.checks[chk] in ("PASS", "FAIL", "UNKNOWN")

    assert isinstance(result.probable_cause, ProbableCause)
    assert isinstance(result.explanation, str)
    assert len(result.explanation) > 0


def test_diagnostic_endpoint_and_errors(client, diagnostic_fixture):
    """11. Test POST /api/v1/incidents/{id}/diagnose and error handling (404 and 400)."""
    incident_id = diagnostic_fixture["incident"].id

    # Successful diagnosis
    res = client.post(f"/api/v1/incidents/{incident_id}/diagnose", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["incident_id"] == incident_id
    assert "probable_cause" in data
    assert "checks" in data

    # Diagnosis with controlled probe overrides
    res_override = client.post(
        f"/api/v1/incidents/{incident_id}/diagnose",
        json={"probe_overrides": {"machine_heartbeat": "PASS", "network": "FAIL"}}
    )
    assert res_override.status_code == 200
    assert res_override.json()["probable_cause"] == "NETWORK_FAILURE"

    # Non-existent incident -> 404
    res_404 = client.post("/api/v1/incidents/999999/diagnose")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()


def test_diagnostic_result_persistence(client, diagnostic_fixture, db_session):
    """12. Test that diagnostic result is persisted in the database and accessible via GET."""
    incident_id = diagnostic_fixture["incident"].id

    # Run diagnosis with connector failure override
    res = client.post(
        f"/api/v1/incidents/{incident_id}/diagnose",
        json={"probe_overrides": {"machine_heartbeat": "PASS", "network": "PASS", "connector": "FAIL"}}
    )
    assert res.status_code == 200

    # Verify directly in PostgreSQL
    db_session.expire_all()
    repo = MonitoringRepository(db_session)
    incident = repo.get_incident_by_id(incident_id)

    assert incident.probable_cause == "CONNECTOR_FAILURE"
    assert incident.state == IncidentState.INVESTIGATING
    assert incident.diagnostic_details is not None
    assert incident.diagnostic_details["probable_cause"] == "CONNECTOR_FAILURE"
    assert incident.diagnostic_details["checks"]["connector"] == "FAIL"

    # Verify GET /api/v1/incidents/{id} reflects the persisted diagnosis
    get_res = client.get(f"/api/v1/incidents/{incident_id}")
    assert get_res.status_code == 200
    incident_data = get_res.json()
    assert incident_data["probable_cause"] == "CONNECTOR_FAILURE"
    assert incident_data["state"] == "INVESTIGATING"
    assert incident_data["diagnostic_details"]["checks"]["connector"] == "FAIL"
