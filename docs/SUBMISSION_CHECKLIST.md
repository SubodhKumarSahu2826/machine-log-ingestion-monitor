# Submission Requirements & Verification Checklist

This document maps the completed implementation to the hackathon evaluation criteria.

---

### 1. Functional Correctness (30%)

| Required Capability | Implemented Component & Verification Evidence |
| :--- | :--- |
| **Event Ingestion** | `POST /api/v1/events` handles Pydantic validation, ensures server-side `received_at` timestamps, and persists to PostgreSQL `machine_events`. |
| **Idempotency** | Duplicate `event_id` submissions return HTTP 200 without creating duplicate records or advancing `last_seen_at`. |
| **Out-of-Order Safety** | Old timestamp events (`occurred_at < last_seen_at`) are accepted for historical record but do not corrupt `last_seen_at`. |
| **Monitoring & Freshness** | Background `MonitoringWorker` computes elapsed seconds against configurable `warning_threshold` and `stale_threshold`. |
| **State Transitions** | Clean transitions across `HEALTHY` → `WARNING` → `STALE` and incident creation without duplicate active incidents. |
| **Deterministic Diagnostics** | Diagnostic engine evaluates 6 distinct vectors (`machine_heartbeat`, `network`, `connector`, `authentication`, `parser`, `ingestion`) with priority resolution rule. |
| **Controlled Recovery** | Supports explicit `RETRY_CONNECTION`, `RECONNECT_CONNECTOR`, `REPLAY_EVENTS`. Rejects invalid or arbitrary commands. |
| **Telemetry Verification** | Recovery cannot be verified without real machine data (`received_at > recovery_started_at` AND `last_seen_at` advanced). |
| **Bounded Retries** | Limits attempts (default 3); escalates to `ESCALATED` and integration `FAILED` when attempts are exhausted. |
| **Concurrency Protection** | Rejects overlapping recovery requests on the same incident or integration with HTTP 409 Conflict. |

---

### 2. Problem Solving (20%)

| Criterion | Problem-Solving Approach |
| :--- | :--- |
| **Closed-Loop Reliability** | Solved the silent stream failure problem by implementing an automated closed loop (**DETECT → DIAGNOSE → RECOVER → VERIFY → RESOLVE**). |
| **Elimination of False Positives** | Solved the "fake recovery" flaw by disallowing resolution based on command dispatch alone; resolution strictly requires verified telemetry arrival. |
| **Observable Hardware Boundaries** | Separated genuinely observable software metrics (heartbeat freshness, database responsiveness) from physical connector probes, offering controlled test probe overrides for reproducible evaluation. |
| **External Simulator Isolation** | Prevented database coupling by forcing the Factory Simulator to communicate strictly over public HTTP ingestion endpoints. |

---

### 3. Code Quality and Architecture (20%)

| Architectural Principle | Implementation Details |
| :--- | :--- |
| **Separation of Concerns** | Strict layered design: `API (FastAPI Routers) → Service Layer (Business Logic) → Repository Layer (SQLAlchemy ORM) → Database (PostgreSQL 15)`. No business logic leaks into routers. |
| **Domain Modeling** | Normalized schema reflecting physical factory hierarchy: `Site → Line → Station → Machine → Integration → Events / Incidents / RecoveryAttempts`. |
| **Database Migrations** | Repeatable Alembic migrations with explicit constraints, foreign keys, and indexes (`ix_machine_events_event_id`, `ix_machine_events_integration_id`). |
| **Frontend Architecture** | Modern React 19 + TypeScript + Vite architecture structured into `api/`, `components/`, `pages/`, `types/`, and `utils/`. Zero mock data in production builds. |

---

### 4. Testing & Error Handling (15%)

| Test Suite / Area | Coverage & Verification |
| :--- | :--- |
| **Backend Test Suite** | **58/58 automated tests passing** across `tests/test_events.py`, `tests/test_monitoring.py`, `tests/test_diagnostics.py`, `tests/test_recovery.py`, `tests/test_simulator.py`. |
| **Edge Cases Covered** | Missing fields (422), malformed timestamps (422), unknown integration (404), machine/integration mismatch (400), database rollback on failure (500), concurrent recovery (409), duplicate event idempotency (200), and max attempt exhaustion (400). |
| **Frontend Build Quality** | `npm run build` executes TypeScript type-checking (`tsc -b`) and Vite production bundle with **zero errors**. |
| **Browser E2E Verification** | Verified live via browser automation across Dashboard, Detail, Incident Workspace, and Simulator console. |

---

### 5. Documentation & Demo (10%)

| Item | Location & Content |
| :--- | :--- |
| **README.md** | Complete architecture, quickstart, Docker instructions, testing guide, failure scenarios, and transparency declarations. |
| **Demo Script** | `docs/demo-script.md`: Timed 3–5 minute step-by-step evaluator script covering both success and permanent failure paths. |
| **Implementation Status** | `docs/IMPLEMENTATION_STATUS.md`: Chronological log of all completed phases. |
| **Decisions & Architecture** | `docs/ARCHITECTURE.md` and `docs/DECISIONS.md`: Documented architectural decisions and trade-offs. |

---

### 6. Usability (5%)

| Feature | Implementation |
| :--- | :--- |
| **Industrial Dark Theme** | Purpose-built Field Support console with curated status colors (`HEALTHY`, `WARNING`, `STALE`, `RECOVERING`, `FAILED`). |
| **Lifecycle Timeline** | Stepper visualization tracking incident states and step timestamps. |
| **Auto-Sync Polling** | Non-aggressive 3-second live sync with manual Pause / Resume toggle. |
| **Simulator Judge Console** | In-browser telemetry injector and terminal command generator for fast evaluator testing. |
