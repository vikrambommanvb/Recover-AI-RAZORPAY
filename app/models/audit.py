from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RecoveryActionRecord(BaseModel):
    """Represents a record of a recovery action execution status."""
    action_id: str = Field(..., description="Unique action transaction ID")
    case_id: str = Field(..., description="Reference to the associated recovery case")
    action_type: str = Field(..., description="Type of action executed (e.g. RETRY, REMIND)")
    status: str = Field("pending", description="Status of the action: pending, triggered, success, failed")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Payload sent to execution system")
    response: Dict[str, Any] = Field(default_factory=dict, description="Response from execution system")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog(BaseModel):
    """Represents a record in the system audit trail."""
    log_id: str = Field(..., description="Unique log ID")
    actor: str = Field("system", description="Identity performing the action (e.g. system, user_id, api_key)")
    action: str = Field(..., description="Action performed, e.g. CASE_CREATED, GUARDRAIL_ALLOWED")
    entity_type: str = Field(..., description="Type of entity, e.g. payment, recovery_case")
    entity_id: str = Field(..., description="ID of the entity")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed changes or log data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluationRun(BaseModel):
    """Represents a record of an evaluation benchmark run."""
    run_id: str = Field(..., description="Unique run identifier")
    dataset_name: str = Field(..., description="Name of evaluation dataset used")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Result metrics (e.g., accuracy, recovery_rate)")
    notes: Optional[str] = Field(None, description="Optional text context or settings for this run")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
