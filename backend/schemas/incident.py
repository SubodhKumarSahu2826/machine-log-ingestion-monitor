from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel
from backend.models import IncidentState


class IncidentResponse(BaseModel):
    """Schema for incident inspection."""
    id: int
    integration_id: int
    state: IncidentState
    probable_cause: Optional[str] = None
    diagnostic_details: Optional[Dict[str, Any]] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
