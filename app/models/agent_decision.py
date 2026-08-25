from enum import Enum
from typing import List
from pydantic import BaseModel, Field, field_validator


class RecoveryAction(str, Enum):
    RETRY = "RETRY"
    REMIND = "REMIND"
    ESCALATE = "ESCALATE"
    STOP = "STOP"
    NO_ACTION = "NO_ACTION"


class AgentDecision(BaseModel):
    """
    AgentDecision Model representing an AI recommendation.
    
    CRITICAL SAFETY PRINCIPLE:
    The AI decision is a recommendation ONLY. It must never directly authorize 
    any financial action. Deterministic guardrails must approve decisions first.
    """
    action: RecoveryAction = Field(
        ..., 
        description="Recommended action: RETRY, REMIND, ESCALATE, STOP, NO_ACTION"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence score of the recommendation between 0.0 and 1.0"
    )
    reason: str = Field(..., description="Detailed explanation/reasoning behind the recommendation")
    risk_factors: List[str] = Field(
        default_factory=list, 
        description="List of risk factors identified by the AI agent"
    )
