from dataclasses import dataclass
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.models import MachineEvent
from backend.repositories.event_repository import EventRepository
from backend.schemas.event import EventCreate


class IngestionError(Exception):
    """Base class for event ingestion exceptions."""
    pass


class IntegrationNotFoundError(IngestionError):
    """Raised when the referenced integration does not exist."""
    def __init__(self, integration_id: int):
        super().__init__(f"Integration with id {integration_id} not found")
        self.integration_id = integration_id


class MachineMismatchError(IngestionError):
    """Raised when machine_id does not match the integration's associated machine."""
    def __init__(self, integration_id: int, expected_machine_id: int, actual_machine_id: int):
        super().__init__(
            f"Integration {integration_id} belongs to machine {expected_machine_id}, "
            f"not machine {actual_machine_id}"
        )
        self.integration_id = integration_id
        self.expected_machine_id = expected_machine_id
        self.actual_machine_id = actual_machine_id


class DatabaseError(IngestionError):
    """Raised when a database error occurs during event ingestion."""
    pass


@dataclass
class IngestionResult:
    """Result returned by the ingestion service."""
    status: str
    event_id: str
    received_at: datetime
    is_duplicate: bool
    message: str


class EventService:
    """Service implementing the business rules and workflow for event ingestion."""

    def __init__(self, repository: EventRepository):
        self.repository = repository

    def ingest_event(self, data: EventCreate) -> IngestionResult:
        """
        Ingest a machine event following the strict workflow:
        1. Validate integration exists.
        2. Validate machine/integration relationship.
        3. Detect duplicate event_id (idempotency).
        4. Generate server-side received_at.
        5. Persist event and update integration last_seen_at atomically.
        6. Return ingestion result.
        """
        # 1. Validate that the referenced integration exists
        integration = self.repository.get_integration(data.integration_id)
        if integration is None:
            raise IntegrationNotFoundError(data.integration_id)

        # 2. Validate that the machine/integration relationship is valid
        if integration.machine_id != data.machine_id:
            raise MachineMismatchError(
                integration_id=data.integration_id,
                expected_machine_id=integration.machine_id,
                actual_machine_id=data.machine_id
            )

        # 3. Detect duplicate event_id
        existing_event = self.repository.get_event_by_event_id(data.event_id)
        if existing_event is not None:
            return IngestionResult(
                status="duplicate",
                event_id=existing_event.event_id,
                received_at=existing_event.received_at,
                is_duplicate=True,
                message="Event with this event_id has already been processed."
            )

        # 4. Generate server-side received_at
        received_at = datetime.now(timezone.utc)

        # 5. Build entity
        event = MachineEvent(
            event_id=data.event_id,
            machine_id=data.machine_id,
            integration_id=data.integration_id,
            event_type=data.event_type,
            occurred_at=data.occurred_at,
            received_at=received_at,
            payload=data.payload
        )

        # 6. Persist event and update last_seen_at atomically
        try:
            self.repository.save_event_and_update_last_seen(event, integration, received_at)
        except IntegrityError as exc:
            self.repository.rollback()
            # Handle potential concurrency race for identical event_id
            existing_event = self.repository.get_event_by_event_id(data.event_id)
            if existing_event is not None:
                return IngestionResult(
                    status="duplicate",
                    event_id=existing_event.event_id,
                    received_at=existing_event.received_at,
                    is_duplicate=True,
                    message="Event with this event_id has already been processed."
                )
            raise DatabaseError("Database integrity violation during event ingestion") from exc
        except SQLAlchemyError as exc:
            self.repository.rollback()
            raise DatabaseError("Database failure during event ingestion") from exc

        return IngestionResult(
            status="success",
            event_id=event.event_id,
            received_at=received_at,
            is_duplicate=False,
            message="Event ingested successfully."
        )
