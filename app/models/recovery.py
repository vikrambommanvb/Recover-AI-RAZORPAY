from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class RecoveryCase(BaseModel):
    """
    RecoveryCase Model representing a revenue-recovery case.
    
    Design Decision: Financial amounts (amount_at_risk) are represented as integers
    in minor units (paise) to prevent floating-point calculation errors.
    """
    case_id: str = Field(..., description="Unique identifier for the recovery case")
    payment_id: str = Field(..., description="Reference to the failed payment")
    amount_at_risk: int = Field(..., ge=0, description="Amount at risk in minor units (paise)")
    risk_status: str = Field(
        "at_risk", 
        description="Current risk status: e.g. at_risk, recovered, unrecoverable"
    )
    root_cause: Optional[str] = Field(None, description="Diagnosed root cause for payment failure")
    recommended_action: Optional[str] = Field(None, description="AI Recommended recovery action")
    guardrail_status: str = Field(
        "pending",
        description="Result of deterministic guardrail check: e.g. pending, allowed, blocked, escalated"
    )
    final_status: str = Field(
        "open",
        description="Workflow state: e.g. open, in_progress, closed"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
