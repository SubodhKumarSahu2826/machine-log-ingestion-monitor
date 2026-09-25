# Live Demonstration Script (3–5 Minutes)

**Project:** Factory Data Reliability & Auto-Recovery Monitor  
**Target Audience:** Hackathon Evaluators, Field Support Engineers, Manufacturing Operations  
**Live URL:** `http://localhost:5173` (Frontend) | `http://localhost:8000/docs` (Swagger API)  

---

## Timeline & Presentation Walkthrough

### ⏱️ 0:00 – 0:30: Problem Statement & Architecture
- **Spoken:**  
  *"In manufacturing, silent data stream interruptions mean blind production—defective parts get made without anyone noticing. Our platform solves this through an autonomous closed loop: **MONITOR → DETECT → DIAGNOSE → RECOVER → VERIFY → RESOLVE**."*
- **Action / Visual:**  
  Show the architecture overview in README or the Field Support Dashboard header. Emphasize that the backend communicates strictly over HTTP with zero simulated mocks in production.

---

### ⏱️ 0:30 – 1:00: Healthy Machine Integrations
- **Spoken:**  
  *"Here is our Field Support Console connected live to PostgreSQL. We see 4 factory machine integrations across our assembly line. Notice the status badges: all streams are HEALTHY, and our freshness counter shows elapsed seconds since the latest valid machine event."*
- **Action / Visual:**  
  Point to the Metric Cards row (Total, Healthy, Open Incidents: 0) and the Integration table on the Dashboard.

---

### ⏱️ 1:00 – 1:45: Trigger Stale Integration
- **Spoken:**  
  *"Now let's simulate an equipment transmission stoppage. We launch the simulator in `SILENT` or `RECOVER_AFTER_RETRY` mode."*
- **Command / Action:**  
  In a terminal run:
  ```bash
  python -m simulator.machine_simulator --scenario RECOVER_AFTER_RETRY --integration-id 1
  ```
  *(Or trigger silent pause via the in-app Simulator console).*
- **Visual Outcome:**  
  As time exceeds the 120s stale threshold (or test threshold), the stream badge turns **STALE** (rose badge). The background worker immediately creates exactly **one active Incident** with state `OPEN`.

---

### ⏱️ 1:45 – 2:15: Incident Triage & Deterministic Diagnostics
- **Spoken:**  
  *"Let's inspect Incident #1. Our deterministic diagnostic engine evaluates 6 distinct vectors: controller heartbeat, network connectivity, connector health, authentication, payload parsing, and database ingestion."*
- **Action / Visual:**  
  Click **View Incident** to open the Incident Workspace.  
  Click **Run Diagnostics**.  
  Show the 6 diagnostic check cards and the probable cause output (e.g., `MACHINE_OFFLINE` or `CONNECTOR_FAILURE`).

---

### ⏱️ 2:15 – 3:00: Execute Controlled Recovery
- **Spoken:**  
  *"Rather than an unverified manual restart, we initiate a bounded recovery action. We select `RETRY_CONNECTION`."*
- **Action / Visual:**  
  Click **Initiate Recovery**, select `RETRY_CONNECTION`, and click Confirm.  
  Show the incident state transition to **`RECOVERING`** on the visual Timeline Stepper. Show the Recovery Attempt record added to the history table with status `STARTED`.

---

### ⏱️ 3:00 – 3:30: Telemetry Arrival, Verification & Resolution
- **Spoken:**  
  *"**The Critical Rule:** The incident does NOT resolve merely because the recovery command was dispatched. Our system strictly requires actual new telemetry to be ingested and persisted in PostgreSQL."*
- **Action / Visual:**  
  Because the simulator was in `RECOVER_AFTER_RETRY`, it detects `RECOVERING` state over HTTP and transmits a fresh cycle event.  
  Click **Verify Telemetry**.  
  The verification succeeds!  
  - Incident transitions: **`VERIFIED` → `RESOLVED`**  
  - Integration health transitions: **`HEALTHY`**  
  - Recovery attempt updates to: **`SUCCESS`** with completion timestamp.  
  - Return to the Dashboard and show the stream is once again **HEALTHY** and incident count is 0.

---

### ⏱️ 3:30 – 4:15: Permanent Hardware Failure & Escalation
- **Spoken:**  
  *"What happens if the equipment has suffered a catastrophic physical failure and cannot transmit data? Recovery must be bounded to prevent infinite retry loops."*
- **Command / Action:**  
  Run simulator in permanent failure:
  ```bash
  python -m simulator.machine_simulator --scenario PERMANENT_FAILURE --integration-id 2
  ```
- **Visual Outcome:**  
  Stream becomes STALE. Open the new incident.  
  - Attempt 1: Fails verification → status `FAILURE`, state `FAILED`.  
  - Attempt 2: Fails verification → status `FAILURE`, state `FAILED`.  
  - Attempt 3: Fails verification → Max attempts (3) exhausted!  
  Show that the incident automatically transitions to **`ESCALATED`**, and the integration health is permanently marked **`FAILED`**.  
  Show that attempting a 4th recovery is cleanly rejected with HTTP 400 Bad Request.

---

### ⏱️ 4:15 – 5:00: Architecture, Testing & Production Evolution
- **Spoken:**  
  *"To summarize: The platform is built on FastAPI, PostgreSQL, and React. All 58 backend tests pass, covering idempotency, concurrency protection, out-of-order timestamps, and recovery boundaries. The recovery service is designed with a pluggable adapter boundary so physical PLC/OPC-UA/MQTT reset commands can drop in without altering our core data-driven verification guarantees."*
- **Action / Visual:**  
  Show the terminal test output (`58 passed`) and the Docker Compose setup.
