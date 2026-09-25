from datetime import datetime
import enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class CheckStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class ProbableCause(str, enum.Enum):
    MACHINE_OFFLINE = "MACHINE_OFFLINE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    CONNECTOR_FAILURE = "CONNECTOR_FAILURE"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    PARSER_FAILURE = "PARSER_FAILURE"
    INGESTION_FAILURE = "INGESTION_FAILURE"
    UNKNOWN = "UNKNOWN"


class DiagnosticRequest(BaseModel):
    """Optional diagnostic parameters or probe overrides for controlled testing."""
    probe_overrides: Optional[Dict[str, CheckStatus]] = Field(
        default=None,
        description="Optional overrides for diagnostic checks (e.g. simulated network/connector status)"
    )


class DiagnosticResult(BaseModel):
    """Structured deterministic diagnostic assessment."""
    incident_id: int
    integration_id: int
    checked_at: datetime
    checks: Dict[str, str]
    probable_cause: ProbableCause
    explanation: str

    model_config = {"from_attributes": True}
