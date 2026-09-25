# Architecture

## Overview
The system is built as a modular monolith in Python, utilizing FastAPI and SQLAlchemy, backed by a PostgreSQL database. The frontend is a React SPA built with Vite.

## Backend Architecture
- **API Layer:** FastAPI routers for defining public endpoints. No business logic in routers.
- **Service Layer:** Contains core business logic, rules, and orchestration (e.g., stale detection, diagnostics, recovery).
- **Repository Layer:** Encapsulates database access and SQLAlchemy queries.

## Domain Model
- `Site` → `Line` → `Station` → `Machine` → `Integration` → `Events / Heartbeats / Incidents`

## Infrastructure
- **PostgreSQL:** Primary relational database.
- **Docker Compose:** Used for running the database and eventually the full stack locally.
- **Simulator:** A separate process that mimics factory equipment by sending HTTP requests to the Backend API.

## Recovery & Verification Architecture (Phase 6)
The system implements a closed-loop recovery workflow that enforces bounded attempts, concurrency safety, and telemetry-based verification:

```
DETECT (Monitoring)
  ↓
DIAGNOSE (Probable Cause)
  ↓
RECOVER (Controlled Action: RETRY_CONNECTION, RECONNECT_CONNECTOR, REPLAY_EVENTS)
  ↓
WAIT FOR TELEMETRY (Simulator / External Machine transmits new event)
  ↓
VERIFY (New event persisted AND last_seen_at > recovery_started_at)
  ↓
RESOLVED (Integration -> HEALTHY)
```

or upon repeated verification timeouts / failed attempts:
```
RECOVER
  ↓
VERIFICATION TIMEOUT / FAILURE
  ↓
FAILED
  ↓ (Bounded retries: default 3 attempts)
ESCALATED (Integration -> FAILED)
```

### Key Architectural Principles:
1. **Controlled Recovery Simulation:** In MVP, actions are simulated/controlled because physical PLC/OPC-UA/MQTT hardware is absent, while preserving a clean adapter boundary for real field connectors.
2. **Critical Verification Rule:** A recovery action is never considered successful merely because the recovery command executed. Verification strictly requires actual new machine data in PostgreSQL (`received_at > recovery_started_at`, `Integration.last_seen_at > recovery_started_at`, and fresh integration state). Duplicate events or replayed old events do not advance `last_seen_at` and will not verify recovery.
3. **Bounded Retries & Escalation:** Recovery attempts are limited (default 3). After exhausting attempts without valid telemetry, the incident escalates and the integration is marked `FAILED` to alert human operators.
4. **Concurrency Protection:** Active recovery acquires database-level state guards preventing concurrent recovery executions for the same integration.

