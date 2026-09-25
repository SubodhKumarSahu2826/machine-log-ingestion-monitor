from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.repositories.monitoring_repository import MonitoringRepository
from backend.schemas.integration import IntegrationResponse

router = APIRouter(prefix="/integrations", tags=["integrations"])


def get_monitoring_repository(db: Session = Depends(get_db)) -> MonitoringRepository:
    """Dependency provider for MonitoringRepository."""
    return MonitoringRepository(db)


@router.get(
    "",
    response_model=List[IntegrationResponse],
    summary="List all integrations and health states"
)
def list_integrations(
    repo: MonitoringRepository = Depends(get_monitoring_repository)
) -> List[IntegrationResponse]:
    """Retrieve all factory integrations with their current health states and freshness metadata."""
    return repo.get_all_integrations()


@router.get(
    "/{integration_id}",
    response_model=IntegrationResponse,
    summary="Get single integration by ID"
)
def get_integration(
    integration_id: int,
    repo: MonitoringRepository = Depends(get_monitoring_repository)
) -> IntegrationResponse:
    """Retrieve details and health state of a specific integration."""
    integration = repo.get_integration_by_id(integration_id)
    if integration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration with id {integration_id} not found"
        )
    return integration
