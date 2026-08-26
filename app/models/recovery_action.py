from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from app.core.logging import correlation_id_var


class RecoveryActionStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"


class RecoveryAction(BaseModel):
    """
    RecoveryAction Model.
    Tracks a specific recovery attempt executed against the payment gateway (Razorpay).
    All monetary amounts are represented as integers in minor units (paise).
    """
    action_id: str = Field(..., description="Unique identifier for the recovery action, e.g. act_XYZ")
    case_id: str = Field(..., description="Reference to the associated recovery case")
    payment_id: str = Field(..., description="Reference to the original failed payment")
    action_type: str = Field(..., description="Type of action attempted, e.g. RETRY, REMIND")
    amount: int = Field(..., gt=0, description="Amount in minor units (paise) to recover")
    currency: str = Field("INR", description="3-letter currency code")
    status: RecoveryActionStatus = Field(RecoveryActionStatus.PENDING, description="State of the action")
    razorpay_order_id: Optional[str] = Field(None, description="Razorpay Order ID created/reused for the retry")
    razorpay_payment_id: Optional[str] = Field(None, description="Razorpay Payment ID if captured successfully")
    attempt_number: int = Field(1, description="Number of recovery attempts made for this case")
    policy_decision: str = Field("ALLOW", description="Outcome of the deterministic PolicyEngine evaluation")
    reason: Optional[str] = Field(None, description="Detailed explanation/reasoning of the execution result")
    correlation_id: str = Field(
        default_factory=lambda: correlation_id_var.get() if 'correlation_id_var' in globals() else "req_system",
        description="Request correlation ID to trace workflows"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
