# Project Context

## Objective
Build a production-quality implementation of the "Machine Log Ingestion Monitor" challenge. The system monitors whether machine/test data is being reliably received from factory integrations, detects stale or failed integrations, diagnoses probable failure points, attempts controlled recovery, verifies recovery, and resolves or escalates incidents.

## Core Workflow
MONITOR → DETECT → DIAGNOSE → RECOVER → VERIFY → RESOLVE / ESCALATE

## Technical Constraints
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, pytest, HTTPX. Modular monolith.
- **Frontend:** React, TypeScript, Vite. Recharts only when needed.
- **Infrastructure:** Docker, Docker Compose.
- **Simulator:** Python script communicating only through the public API.

## Core Principles
- A working system is more important than feature quantity.
- Do not introduce unrelated features.
- MVP must remain simple and reliable.
- AI is assistive only, not for critical system state.
- Efficiency rule: existing dependency > new dependency, simple > complex.
