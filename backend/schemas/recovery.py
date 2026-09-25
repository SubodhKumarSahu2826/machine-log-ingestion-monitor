from datetime import datetime
import enum
from typing import Optional
from pydantic import BaseModel, Field


class RecoveryAction(str, enum.Enum):
    """Explicitly supported controlled recovery actions."""
    RETRY_CONNECTION = "RETRY_CONNECTION"
    RECONNECT_CONNECTOR = "RECONNECT_CONNECTOR"
    REPLAY_EVENTS = "REPLAY_EVENTS"


class RecoveryAttemptStatus(str, enum.Enum):
    """Status of a recovery attempt."""
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class RecoveryRequest(BaseModel):
    """Request payload to initiate incident recovery."""
    action: RecoveryAction
    timeout_seconds: Optional[float] = Field(
        default=None,
        description="Optional timeout to wait synchronously for verification. If omitted, initiates recovery asynchronously."
    )


class RecoveryAttemptResponse(BaseModel):
    """Schema for recovery attempt records."""
    id: int
    incident_id: int
    action: str
    status: str
    attempted_at: datetime
    completed_at: Optional[datetime] = None
    result_message: Optional[str] = None

    model_config = {"from_attributes": True}


class RecoveryResponse(BaseModel):
    """Response returned upon initiating recovery."""
    incident_id: int
    integration_id: int
    incident_state: str
    attempt: RecoveryAttemptResponse
    message: str


class VerificationResponse(BaseModel):
    """Response returned upon recovery verification."""
    incident_id: int
    integration_id: int
    incident_state: str
    verified: bool
    message: str
    attempt: Optional[RecoveryAttemptResponse] = None
