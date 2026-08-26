from pydantic import BaseModel, Field
from typing import List, Optional
from app.models.agent_decision import RecoveryAction


class AIServiceRequest(BaseModel):
    """Input payload sent to AI provider for recovery recommendation."""
    payment_id: str = Field(..., description="Unique payment identifier")
    amount: int = Field(..., description="Amount of payment in paise")
    currency: str = Field(..., description="3-letter currency code")
    failure_reason: str = Field(..., description="Raw failure reason from the payment gateway")
    customer_id: str = Field(..., description="Identifier for the customer")
    metadata: dict = Field(default_factory=dict, description="Metadata associated with the payment")


class AIServiceResponse(BaseModel):
    """Structured response expected from the AI provider."""
    action: RecoveryAction = Field(..., description="Recommended recovery action")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")
    reason: str = Field(..., description="Reasoning/justification for the action")
    root_cause: str = Field(..., description="Diagnosed root cause for the failure")
    risk_factors: List[str] = Field(default_factory=list, description="Identified risk factors")
    recommended_message_type: Optional[str] = Field(None, description="Recommended message type to send")
    requires_human_review: bool = Field(default=False, description="Flag indicating if human review is required")

