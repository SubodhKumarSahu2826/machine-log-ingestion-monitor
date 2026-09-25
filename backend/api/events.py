from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.repositories.event_repository import EventRepository
from backend.schemas.event import EventCreate, EventIngestResponse
from backend.services.event_service import (
    DatabaseError,
    EventService,
    IntegrationNotFoundError,
    MachineMismatchError,
)

router = APIRouter(prefix="/events", tags=["events"])


def get_event_service(db: Session = Depends(get_db)) -> EventService:
    """Dependency provider for EventService."""
    repository = EventRepository(db)
    return EventService(repository)


@router.post(
    "",
    response_model=EventIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest machine event"
)
def ingest_event(
    event_data: EventCreate,
    response: Response,
    service: EventService = Depends(get_event_service)
) -> EventIngestResponse:
    """
    Ingest a machine telemetry event idempotently.
    - Returns 201 Created on new event ingestion.
    - Returns 200 OK on duplicate event_id (idempotent).
    - Returns 400 Bad Request on machine/integration mismatch.
    - Returns 404 Not Found on unknown integration.
    - Returns 422 Unprocessable Entity on validation errors.
    - Returns 500 Internal Server Error on database failures.
    """
    try:
        result = service.ingest_event(event_data)
        if result.is_duplicate:
            response.status_code = status.HTTP_200_OK
        else:
            response.status_code = status.HTTP_201_CREATED

        return EventIngestResponse(
            status=result.status,
            event_id=result.event_id,
            received_at=result.received_at,
            message=result.message
        )
    except IntegrationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MachineMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error during event ingestion"
        ) from exc
