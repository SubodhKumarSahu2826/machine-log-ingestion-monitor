from datetime import datetime
import json
import httpx
import pytest

from simulator.machine_simulator import MachineSimulator, generate_event
from simulator.scenarios import ScenarioType


def test_event_payload_generation():
    """1. Test event payload structure and client constraints."""
    event = generate_event(machine_id=2, integration_id=5, cycle_count=42)

    assert event["machine_id"] == 2
    assert event["integration_id"] == 5
    assert event["event_type"] == "cycle_completed"
    assert event["payload"]["result"] == "PASS"
    assert event["payload"]["cycle_count"] == 42
    assert "cycle_time_ms" in event["payload"]
    assert event["payload"]["defect_code"] is None

    # Crucial constraint: client must NOT generate or send received_at
    assert "received_at" not in event


def test_unique_event_ids():
    """2. Test that each generated event has a unique event_id."""
    events = [generate_event(machine_id=1, integration_id=1) for _ in range(100)]
    event_ids = [e["event_id"] for e in events]

    assert len(event_ids) == 100
    assert len(set(event_ids)) == 100


def test_timezone_aware_occurred_at():
    """3. Test that occurred_at is a valid ISO format timezone-aware timestamp."""
    event = generate_event(machine_id=1, integration_id=1)
    occurred_at_str = event["occurred_at"]

    dt = datetime.fromisoformat(occurred_at_str)
    assert dt.tzinfo is not None
    assert dt.tzinfo.utcoffset(dt) is not None


def test_normal_scenario_sends_events_to_api():
    """4. Test NORMAL scenario sends events to POST /api/v1/events."""
    recorded_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(201, json={"status": "success", "event_id": "test", "received_at": "2026-09-25T10:00:00Z", "message": "ok"})

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    simulator = MachineSimulator(
        api_url="http://mock-api:8000",
        machine_id=1,
        integration_id=2,
        interval=0.01,
        scenario=ScenarioType.NORMAL,
        client=client
    )

    simulator.run(max_events=4)

    assert len(recorded_requests) == 4
    assert simulator.events_sent == 4

    for req in recorded_requests:
        assert req.method == "POST"
        assert req.url.path == "/api/v1/events"
        body = json.loads(req.content.decode("utf-8"))
        assert body["machine_id"] == 1
        assert body["integration_id"] == 2
        assert "event_id" in body
        assert "occurred_at" in body
        assert "received_at" not in body


def test_silent_scenario_stops_sending_events():
    """5. Test SILENT scenario sends initial events and then halts transmission."""
    recorded_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(201, json={"status": "success"})

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    simulator = MachineSimulator(
        api_url="http://mock-api:8000",
        machine_id=1,
        integration_id=1,
        interval=0.01,
        scenario=ScenarioType.SILENT,
        client=client
    )

    # Run with keep_alive=False to verify it ceases transmission
    simulator.run(initial_silent_events=3, keep_alive=False)

    assert len(recorded_requests) == 3
    assert simulator.events_sent == 3


def test_transient_api_failure_handled_gracefully():
    """6. Test transient API failure retries and permanent failure does not crash."""
    # Subtest A: Transient 503 error that succeeds on attempt 2
    attempt = 0

    def retry_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(201, json={"status": "success"})

    transport = httpx.MockTransport(retry_handler)
    client = httpx.Client(transport=transport)

    simulator = MachineSimulator(
        interval=0.01,
        max_retries=2,
        retry_delay=0.01,
        client=client
    )

    event = generate_event(1, 1)
    success = simulator.send_event(event)

    assert success is True
    assert attempt == 2
    assert simulator.events_sent == 1

    # Subtest B: Permanent network connection failure handled without crash
    def fail_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport_fail = httpx.MockTransport(fail_handler)
    client_fail = httpx.Client(transport=transport_fail)

    failing_simulator = MachineSimulator(
        interval=0.01,
        max_retries=2,
        retry_delay=0.01,
        client=client_fail
    )

    # Must return False and NOT raise an unhandled exception
    result = failing_simulator.send_event(event)
    assert result is False


def test_placeholder_scenarios_raise_not_implemented():
    """Verify that placeholder failure scenarios raise NotImplementedError."""
    simulator = MachineSimulator(
        scenario=ScenarioType.NETWORK_FAILURE
    )
    with pytest.raises(NotImplementedError) as exc_info:
        simulator.run()

    assert "placeholder" in str(exc_info.value).lower()
