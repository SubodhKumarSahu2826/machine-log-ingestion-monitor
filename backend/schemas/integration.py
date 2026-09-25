from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from backend.models import IntegrationHealthState


class IntegrationResponse(BaseModel):
    """Response schema for integration health and metadata inspection."""
    id: int
    machine_id: int
    name: str
    type: str
    health_state: IntegrationHealthState
    last_seen_at: Optional[datetime] = None
    expected_interval_seconds: Optional[int] = None
    warning_threshold_seconds: Optional[int] = None
    stale_threshold_seconds: Optional[int] = None

    model_config = {"from_attributes": True}
