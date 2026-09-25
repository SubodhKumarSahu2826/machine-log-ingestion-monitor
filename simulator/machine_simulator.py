import argparse
import os
import random
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

# Support running directly or as a module
try:
    from simulator.scenarios import ScenarioType
except ImportError:
    from scenarios import ScenarioType


def generate_event(machine_id: int, integration_id: int, cycle_count: int = 1) -> Dict[str, Any]:
    """Generate a single valid machine event payload."""
    return {
        "event_id": f"sim-{uuid.uuid4()}",
        "machine_id": machine_id,
        "integration_id": integration_id,
        "event_type": "cycle_completed",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "result": "PASS",
            "cycle_count": cycle_count,
            "cycle_time_ms": random.randint(1500, 2200),
            "defect_code": None
        }
    }


class MachineSimulator:
    """Simulator mimicking factory equipment emitting telemetry events over HTTP."""

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        machine_id: int = 1,
        integration_id: int = 1,
        interval: float = 1.0,
        scenario: ScenarioType = ScenarioType.NORMAL,
        max_retries: int = 3,
        retry_delay: float = 0.5,
        client: Optional[httpx.Client] = None
    ):
        self.api_url = api_url.rstrip("/")
        self.machine_id = machine_id
        self.integration_id = integration_id
        self.interval = interval
        self.scenario = ScenarioType(scenario) if isinstance(scenario, str) else scenario
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client = client or httpx.Client(timeout=5.0)
        self._running = False
        self.events_sent = 0

    def stop(self) -> None:
        """Signal the simulator loop to stop."""
        self._running = False

    def send_event(self, event: Dict[str, Any]) -> bool:
        """
        Send an event to the backend API with bounded retry logic.
        Returns True if accepted (201 or 200), False otherwise.
        """
        endpoint = f"{self.api_url}/api/v1/events"
        attempts = 0

        while attempts <= self.max_retries:
            attempts += 1
            try:
                response = self._client.post(endpoint, json=event)
                if response.status_code == 201:
                    print(f"[event] sent event_id={event['event_id']} status=201")
                    self.events_sent += 1
                    return True
                elif response.status_code == 200:
                    print(f"[event] duplicate event_id={event['event_id']} status=200")
                    return True
                elif response.status_code in (400, 404, 422):
                    print(f"[event] rejected status={response.status_code} error={response.text}")
                    return False
                elif response.status_code >= 500:
                    print(f"[event] server error status={response.status_code} attempt={attempts}")
                else:
                    print(f"[event] unexpected response status={response.status_code} body={response.text}")
                    return False
            except (httpx.RequestError, httpx.HTTPError) as exc:
                print(f"[event] network failure attempt={attempts}/{self.max_retries + 1}: {exc}")

            if attempts <= self.max_retries:
                time.sleep(self.retry_delay)

        print(f"[event] failed to send event_id={event['event_id']} after {attempts} attempts")
        return False

    def run(
        self,
        max_events: Optional[int] = None,
        initial_silent_events: int = 3,
        keep_alive: bool = True
    ) -> None:
        """Run the configured simulator scenario."""
        self._running = True

        if self.scenario == ScenarioType.NORMAL:
            self._run_normal(max_events=max_events)
        elif self.scenario == ScenarioType.SILENT:
            self._run_silent(initial_events=initial_silent_events, keep_alive=keep_alive)
        elif self.scenario == ScenarioType.RECOVER_AFTER_RETRY:
            self._run_recover_after_retry(
                initial_events=initial_silent_events,
                max_events=max_events,
                keep_alive=keep_alive
            )
        elif self.scenario == ScenarioType.PERMANENT_FAILURE:
            self._run_permanent_failure(initial_events=initial_silent_events, keep_alive=keep_alive)
        elif self.scenario in (
            ScenarioType.NETWORK_FAILURE,
            ScenarioType.CONNECTOR_FAILURE,
            ScenarioType.PARSER_FAILURE,
        ):
            raise NotImplementedError(
                f"Scenario '{self.scenario.value}' is a placeholder for later phases."
            )
        else:
            raise ValueError(f"Unknown scenario: {self.scenario}")

    def _run_normal(self, max_events: Optional[int] = None) -> None:
        """Continuously generate and send valid events at configured intervals."""
        print(f"[simulator] starting NORMAL scenario (interval={self.interval}s, machine_id={self.machine_id}, integration_id={self.integration_id})")
        cycle = 0
        while self._running:
            cycle += 1
            event = generate_event(self.machine_id, self.integration_id, cycle_count=cycle)
            self.send_event(event)

            if max_events is not None and self.events_sent >= max_events:
                print(f"[simulator] reached target event count ({max_events}), exiting.")
                break

            time.sleep(self.interval)

    def _run_silent(self, initial_events: int = 3, keep_alive: bool = True) -> None:
        """Send initial events then cease transmission while keeping process alive."""
        print(f"[simulator] starting SILENT scenario (sending {initial_events} initial events then stopping)")
        for cycle in range(1, initial_events + 1):
            if not self._running:
                break
            event = generate_event(self.machine_id, self.integration_id, cycle_count=cycle)
            self.send_event(event)
            time.sleep(self.interval)

        print("[simulator] SILENT mode active: stopped sending events. Keeping process alive.")
        while self._running and keep_alive:
            time.sleep(1.0)

    def _run_recover_after_retry(
        self,
        initial_events: int = 3,
        max_events: Optional[int] = None,
        poll_interval: float = 0.5,
        max_poll_seconds: float = 30.0,
        keep_alive: bool = True
    ) -> None:
        """
        Send initial events, pause transmission until backend issues a recovery action
        (incident enters RECOVERING state), then resume sending events.
        """
        print(f"[simulator] starting RECOVER_AFTER_RETRY scenario (initial {initial_events} events, then waiting for recovery)")
        for cycle in range(1, initial_events + 1):
            if not self._running:
                break
            event = generate_event(self.machine_id, self.integration_id, cycle_count=cycle)
            self.send_event(event)
            time.sleep(self.interval)

        print(f"[simulator] silent pause active: polling for RECOVERING incident on integration {self.integration_id}...")
        start_poll = time.time()
        recovery_detected = False

        while self._running and (time.time() - start_poll) < max_poll_seconds:
            try:
                resp = self._client.get(
                    f"{self.api_url}/api/v1/incidents",
                    params={"integration_id": self.integration_id, "state": "RECOVERING"}
                )
                if resp.status_code == 200:
                    incidents = resp.json()
                    if len(incidents) > 0:
                        print(f"[simulator] recovery detected (incident {incidents[0]['id']} in RECOVERING state). Resuming transmission!")
                        recovery_detected = True
                        break
            except (httpx.RequestError, httpx.HTTPError) as exc:
                print(f"[simulator] poll error: {exc}")

            time.sleep(poll_interval)

        if not recovery_detected:
            print("[simulator] poll timed out without detecting recovery.")
            while self._running and keep_alive:
                time.sleep(1.0)
            return

        # Resume sending events
        cycle = initial_events
        while self._running:
            cycle += 1
            event = generate_event(self.machine_id, self.integration_id, cycle_count=cycle)
            self.send_event(event)

            if max_events is not None and self.events_sent >= max_events:
                print(f"[simulator] reached target event count ({max_events}), exiting.")
                break

            if not keep_alive and (max_events is None):
                break

            time.sleep(self.interval)

    def _run_permanent_failure(self, initial_events: int = 3, keep_alive: bool = True) -> None:
        """Send initial events then cease transmission permanently without recovering."""
        print(f"[simulator] starting PERMANENT_FAILURE scenario (sending {initial_events} events then permanently silent)")
        for cycle in range(1, initial_events + 1):
            if not self._running:
                break
            event = generate_event(self.machine_id, self.integration_id, cycle_count=cycle)
            self.send_event(event)
            time.sleep(self.interval)

        print("[simulator] permanent failure active: no further events will be transmitted.")
        while self._running and keep_alive:
            time.sleep(1.0)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments with environment variable fallbacks."""
    parser = argparse.ArgumentParser(description="Factory Equipment Event Simulator")
    parser.add_argument(
        "--api-url",
        default=os.getenv("API_BASE_URL", "http://localhost:8000"),
        help="Base URL for the ingestion API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--machine-id",
        type=int,
        default=int(os.getenv("MACHINE_ID", "1")),
        help="Machine ID (default: 1)"
    )
    parser.add_argument(
        "--integration-id",
        type=int,
        default=int(os.getenv("INTEGRATION_ID", "1")),
        help="Integration ID (default: 1)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("EVENT_INTERVAL", "1.0")),
        help="Event emission interval in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--scenario",
        default=os.getenv("SCENARIO", "NORMAL"),
        choices=[s.value for s in ScenarioType],
        help="Execution scenario (default: NORMAL)"
    )
    parser.add_argument(
        "--initial-events",
        type=int,
        default=int(os.getenv("INITIAL_EVENTS", "3")),
        help="Number of initial events for SILENT scenario (default: 3)"
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=int(os.getenv("MAX_EVENTS")) if os.getenv("MAX_EVENTS") else None,
        help="Maximum events to send before exiting (default: infinite)"
    )
    return parser.parse_args()


def main() -> None:
    """Entrypoint for the simulator CLI."""
    args = parse_args()
    simulator = MachineSimulator(
        api_url=args.api_url,
        machine_id=args.machine_id,
        integration_id=args.integration_id,
        interval=args.interval,
        scenario=ScenarioType(args.scenario)
    )

    def handle_signal(sig, frame):
        print("\n[simulator] stop signal received, shutting down gracefully...")
        simulator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        simulator.run(
            max_events=args.max_events,
            initial_silent_events=args.initial_events,
            keep_alive=True
        )
    except KeyboardInterrupt:
        simulator.stop()


if __name__ == "__main__":
    main()
