# Factory Data Reliability & Auto-Recovery Monitor

An industrial-grade telemetry monitoring, root-cause diagnosis, and closed-loop auto-recovery platform for manufacturing line equipment integrations.

> **IMPORTANT TRANSPARENCY STATEMENT:**
> The hackathon environment does not provide live factory equipment/data. The repository therefore includes a Factory Event Simulator that communicates through the same HTTP ingestion API used by the application. The simulator does not write directly to the database.

---

## 1. Problem Statement
Modern manufacturing plants rely on continuous real-time data streaming from PLCs, test stands, and SCADA gateways across automated lines. When an integration silently ceases transmitting data—due to network jitter, connector adapter crashes, or parser faults—production continues blind to defect spikes, cycle time drift, and regulatory compliance breaches. Manual discovery takes hours, during which hundreds of unmonitored units may roll off the line.

## 2. Problem Interpretation
To ensure data stream reliability, the system must treat integration telemetry not as a passive metric, but as an active closed loop. Rather than just alerting an operator to a stale stream, the platform must:
1. **Monitor & Detect:** Continuously compute freshness against line-specific thresholds (`expected_interval`, `warning_threshold`, `stale_threshold`).
2. **Diagnose Deterministically:** Probe the failure domain across 6 distinct vectors (`machine_heartbeat`, `network`, `connector`, `authentication`, `parser`, `ingestion`) and identify the exact probable cause.
3. **Execute Controlled Recovery:** Perform bounded, non-destructive recovery actions (`RETRY_CONNECTION`, `RECONNECT_CONNECTOR`, `REPLAY_EVENTS`).
4. **Enforce Telemetry Verification:** Never declare an incident resolved just because a recovery command executed. Verify that **actual new, valid machine data** was ingested, persisted, and advanced `last_seen_at`.
5. **Resolve or Escalate:** Transition to `RESOLVED` only after telemetry verification, or escalate to `ESCALATED` upon exceeding bounded retry attempts.

---

## 3. Solution Overview & Key Workflow

```
[ Factory Equipment / Simulator ]
               │
               ▼  (HTTP POST /api/v1/events)
   [ Event Ingestion Engine ] ──► [ PostgreSQL 15 ]
               │                          │
               ▼                          ▼
   [ Background Monitoring Worker ] ◄─────┘
         (Freshness Evaluation)
               │
               ▼
           DETECTED (HEALTHY → WARNING → STALE)
               │
               ▼
           DIAGNOSE (Probable Cause Decision Tree)
               │
               ▼
     RECOVER (Controlled Action: RETRY_CONNECTION, RECONNECT_CONNECTOR, REPLAY_EVENTS)
               │
               ▼
     WAIT FOR TELEMETRY (Simulator / External Adapter emits new event)
               │
               ▼
     VERIFY (received_at > recovery_started_at AND last_seen_at advanced)
          ┌────┴────┐
          ▼         ▼
       VERIFIED   TIMEOUT / NO DATA
          │         │
          ▼         ▼
       RESOLVED   FAILED (Retry bounded: max 3 attempts)
                    │
                    ▼
                  ESCALATED
```

---

## 4. Tech Stack

- **Backend:** Python 3.11+, FastAPI (REST API), Pydantic v2 (Validation & Schemas).
- **Database & ORM:** PostgreSQL 15, SQLAlchemy 2.0, Psycopg3 (binary driver).
- **Database Migrations:** Alembic (schema tracking and repeatable migrations).
- **Frontend Dashboard:** React 19, TypeScript, Vite, Vanilla CSS design tokens (Dark Industrial theme).
- **Simulator:** Standalone Python client using `httpx` (strictly HTTP API-based, zero direct DB access).
- **Testing:** Pytest (58 unit and end-to-end integration tests).
- **Containerization:** Docker & Docker Compose (PostgreSQL, FastAPI Backend, React Frontend).

---

## 5. Repository Structure

```
factory-data-reliability-monitor/
├── backend/
│   ├── alembic/                # Alembic migration scripts
│   ├── alembic.ini             # Migration configuration
│   ├── api/                    # FastAPI routers (events, integrations, incidents)
│   ├── database.py             # Database engine & session maker
│   ├── main.py                 # FastAPI application, lifespan, & CORS
│   ├── models.py               # SQLAlchemy ORM domain entities
│   ├── repositories/           # Repository layer (DB access)
│   ├── schemas/                # Pydantic request/response schemas
│   ├── seed.py                 # Factory domain seed script
│   ├── services/               # Core business services (monitoring, diagnostics, recovery)
│   ├── workers/                # Background monitoring worker loop
│   ├── Dockerfile              # Backend production container
│   └── requirements.txt        # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── api/client.ts       # Type-safe API client
│   │   ├── components/         # Industrial UI components (StatusIndicator, FactoryFlow, IntegrationTable, etc.)
│   │   ├── pages/              # Views (OperationsPage, IntegrationsPage, IncidentPage, DemoPage)
│   │   ├── types/index.ts      # TypeScript interfaces
│   │   ├── utils/formatters.ts # Formatting and design tokens
│   │   ├── App.tsx             # Root layout & auto-refresh polling
│   │   ├── main.tsx            # Bootstrap entry point
│   │   └── index.css           # Industrial dark theme styling
│   ├── Dockerfile              # Multi-stage production Nginx container
│   └── package.json            # Frontend dependencies
├── simulator/
│   ├── machine_simulator.py    # Factory equipment event simulator
│   ├── scenarios/              # Scenario definitions (NORMAL, SILENT, RECOVER_AFTER_RETRY, PERMANENT_FAILURE)
│   └── requirements.txt        # Simulator dependencies
├── tests/
│   ├── conftest.py             # Pytest fixtures and DB setup
│   ├── test_events.py          # Ingestion & idempotency tests
│   ├── test_monitoring.py      # Freshness & stale detection tests
│   ├── test_diagnostics.py     # Deterministic diagnostic tests
│   ├── test_recovery.py        # Controlled recovery & verification tests
│   └── test_simulator.py       # Simulator behavior tests
├── docs/                       # Architecture, decisions, and demo guides
├── docker-compose.yml          # Multi-container orchestration
└── README.md
```

---

## 6. Database Overview

Domain Entity Relationships:
```
Site ──► Line ──► Station ──► Machine ──► Integration
                                               │
                                 ┌─────────────┼─────────────┐
                                 ▼             ▼             ▼
                            MachineEvent   Heartbeat      Incident
                                                             │
                                                             ▼
                                                      RecoveryAttempt
```

Key Tables & Constraints:
- `integrations`: Tracks stream status, `health_state` (`HEALTHY`, `WARNING`, `STALE`, `RECOVERING`, `FAILED`), and `last_seen_at`.
- `machine_events`: Persists telemetry with unique `event_id` constraint, client `occurred_at`, and server `received_at`.
- `incidents`: Tracks lifecycle `state` (`DETECTED`, `OPEN`, `INVESTIGATING`, `RECOVERING`, `VERIFIED`, `RESOLVED`, `FAILED`, `ESCALATED`) and structured `diagnostic_details` (JSON).
- `recovery_attempts`: Records recovery history (`action`, `status`, `attempted_at`, `completed_at`, `result_message`).
- `audit_events`: Immutable audit trail for all system state transitions.

---

## 7. Setup & Execution Instructions

### Option A: Complete Docker Compose (Recommended for Evaluators)

Run the full stack (PostgreSQL, Backend API, and Frontend) in one command:
```bash
docker compose up --build
```
- **Frontend Dashboard:** `http://localhost:5173`
- **Backend API & Swagger Docs:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

### Option B: Local Development

#### 1. Start Database
```bash
docker compose up -d db
```

#### 2. Setup Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

#### 3. Run Migrations & Seed Data
```bash
alembic -c backend/alembic.ini upgrade head
python -m backend.seed
```

#### 4. Run Backend Server
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 5. Run Frontend Development Server
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 8. Testing Instructions

Run the complete backend test suite:
```bash
pytest -v
```
*Current test count: 58 tests passed.*

Build the frontend production bundle:
```bash
cd frontend
npm run build
```

---

## 9. Simulator Instructions & Failure Scenarios

The simulator mimics factory floor equipment sending events over HTTP:

```bash
# NORMAL Scenario: Continuously emits events every 1.0s (maintains HEALTHY state)
python -m simulator.machine_simulator --scenario NORMAL --interval 1.0 --integration-id 1

# SILENT Scenario: Emits 3 events then halts (triggers STALE detection)
python -m simulator.machine_simulator --scenario SILENT --initial-events 3 --integration-id 1

# RECOVER_AFTER_RETRY Scenario (Scenario A):
# Emits initial events, pauses silently, waits for recovery (incident in RECOVERING), then resumes
python -m simulator.machine_simulator --scenario RECOVER_AFTER_RETRY --integration-id 1

# PERMANENT_FAILURE Scenario (Scenario B):
# Hardware failure; remains completely silent through all recovery attempts (leads to ESCALATION)
python -m simulator.machine_simulator --scenario PERMANENT_FAILURE --integration-id 1
```

---

## 10. Live Demonstration Guide

See [`docs/demo-script.md`](docs/demo-script.md) for the exact 3–5 minute step-by-step evaluator walkthrough:
1. **Show Healthy Dashboard:** Integrations are `HEALTHY`, freshness counters updating.
2. **Trigger Stale Incident:** Run `SILENT` or pause transmission → Integration becomes `STALE` → Single active `Incident` appears.
3. **Deterministic Diagnostics:** Open incident workspace → Click **Run Diagnostics** → Evaluates 6 vectors, pinpoints probable cause (e.g., `MACHINE_OFFLINE`).
4. **Controlled Recovery & Telemetry Verification:** Click **Initiate Recovery** (`RETRY_CONNECTION`) → Simulator resumes → Ingests fresh event → Click **Verify Telemetry** → Incident transitions `VERIFIED` → `RESOLVED`, Integration returns to `HEALTHY`.
5. **Bounded Retries & Escalation:** In `PERMANENT_FAILURE`, 3 failed verification attempts result in `ESCALATED` incident state and `FAILED` integration state.

---

## 11. Limitations & Future Production Evolution

- **Current MVP Scope:** Recovery actions (`RETRY_CONNECTION`, `RECONNECT_CONNECTOR`, `REPLAY_EVENTS`) interact with a simulated environment over HTTP because physical factory PLC/OPC-UA/MQTT hardware is absent.
- **Production Adapter Boundary:** The service layer provides an explicit connector adapter interface where real PLC reset hooks (Modbus TCP, OPC-UA node reset, MQTT broker reconnect) plug in directly without changing the core state machine or verification rules.
- **Future Scale:** Can incorporate distributed worker brokers (Celery/Temporal) and real-time WebSocket telemetry pushes when scaling to 10,000+ machine streams.

---

## 12. AI-Assisted Development Declaration

This application was developed with the assistance of an agentic AI coding assistant (Antigravity by Google DeepMind). The entire architectural design, state machines, database schemas, API boundaries, deterministic diagnostic algorithms, recovery verification rules, tests, and frontend components were verified, reviewed, manually validated, and tested end-to-end for correctness, performance, and adherence to production software engineering standards.
