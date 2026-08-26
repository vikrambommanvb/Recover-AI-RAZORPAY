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
        description="Current risk status: e.g. AT_RISK, NOT_AT_RISK, UNKNOWN"
    )
    root_cause: Optional[str] = Field(None, description="Diagnosed root cause for payment failure: e.g. TRANSIENT_FAILURE, CUSTOMER_FUNDS, PAYMENT_DECLINED, UNKNOWN")
    recommended_action: Optional[str] = Field(None, description="AI Recommended recovery action")
    guardrail_status: str = Field(
        "pending",
        description="Result of deterministic guardrail check: e.g. pending, allowed, blocked, escalated"
    )
    status: str = Field(
        "PENDING",
        description="Workflow state: e.g. PENDING, IN_PROGRESS, CLOSED"
    )
    customer_id: Optional[str] = Field(None, description="Reference to the customer")
    failure_reason: Optional[str] = Field(None, description="Detailed failure reason from the payment")
    previous_payment_count: int = Field(0, description="Count of previous payments from customer history")
    successful_payment_count: int = Field(0, description="Count of previous successful payments from customer history")
    previous_failure_count: int = Field(0, description="Count of previous failed payments from customer history")
    final_status: str = Field(
        "open",
        description="Workflow state: e.g. open, in_progress, closed"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
