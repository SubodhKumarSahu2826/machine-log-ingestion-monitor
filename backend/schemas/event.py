from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventCreate(BaseModel):
    """Schema for machine event ingestion request."""
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(..., min_length=1, description="Unique identifier for the event")
    machine_id: int = Field(..., gt=0, description="Identifier of the machine")
    integration_id: int = Field(..., gt=0, description="Identifier of the integration")
    event_type: str = Field(..., min_length=1, description="Type/category of event")
    occurred_at: datetime = Field(..., description="Timestamp when the event occurred on the machine")
    payload: Dict[str, Any] = Field(..., description="Telemetry payload as valid JSON object")

    @field_validator("event_id", "event_type")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Must not be empty or whitespace")
        return v.strip()

    @field_validator("occurred_at")
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("occurred_at must be a timezone-aware timestamp")
        return v


class EventIngestResponse(BaseModel):
    """Schema for machine event ingestion response."""
    status: str
    event_id: str
    received_at: datetime
    message: str
