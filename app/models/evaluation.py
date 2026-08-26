from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class EvaluationRun(BaseModel):
    """
    EvaluationRun Model.
    Stores metadata and aggregated statistics of a batch simulation run.
    Amounts are stored in minor units (paise) to prevent floating-point calculation errors.
    """
    evaluation_id: str = Field(..., description="Unique ID for this evaluation run, e.g. eval_XYZ")
    dataset_size: int = Field(..., description="Number of payments analyzed in the dataset")
    seed: int = Field(42, description="Deterministic random seed used to reproduce the simulation")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    # Financial metrics
    revenue_at_risk: int = Field(0, ge=0, description="Total amount at risk (paise)")
    revenue_recovered: int = Field(0, ge=0, description="Verified recovered amount from captured payments (paise)")
    
    # Case conversion counts
    eligible_cases: int = Field(0, ge=0, description="Count of recovery-eligible cases (risk status AT_RISK or UNKNOWN)")
    recovery_attempts: int = Field(0, ge=0, description="Count of recovery execution actions initiated")
    successful_recoveries: int = Field(0, ge=0, description="Count of verified successful recoveries")
    failed_recoveries: int = Field(0, ge=0, description="Count of failed execution actions")
    blocked_actions: int = Field(0, ge=0, description="Count of actions blocked by PolicyEngine or executor limits")
    escalated_cases: int = Field(0, ge=0, description="Count of cases escalated to human review")
    stopped_cases: int = Field(0, ge=0, description="Count of cases stopped by rules (e.g. STOP action)")
    
    # AI recommendations breakdown
    ai_decisions: int = Field(0, ge=0, description="Total number of AI decisions analyzed")
    ai_retry_count: int = Field(0, ge=0)
    ai_remind_count: int = Field(0, ge=0)
    ai_stop_count: int = Field(0, ge=0)
    ai_escalate_count: int = Field(0, ge=0)
    ai_no_action_count: int = Field(0, ge=0)
    
    # Policy decisions breakdown
    policy_allowed_count: int = Field(0, ge=0)
    policy_blocked_count: int = Field(0, ge=0)
    policy_escalated_count: int = Field(0, ge=0)
    policy_overrides: int = Field(0, ge=0, description="Count of decisions where Policy Engine overrode AI suggestion")
    
    # Rates
    recovery_rate: float = Field(0.0, description="revenue_recovered / revenue_at_risk")
    case_recovery_rate: float = Field(0.0, description="successful_recoveries / eligible_cases")
    policy_override_rate: float = Field(0.0, description="policy_overrides / valid_ai_decisions")
    
    # Settings and Metadata
    ai_provider: str = Field(..., description="AI Provider used (mock, groq)")
    ai_model: str = Field(..., description="LLM model name used")
    evaluation_mode: str = Field("MOCK", description="DEMO, MOCK, LIVE_TEST")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CaseEvaluationResult(BaseModel):
    """
    CaseEvaluationResult Model.
    Tracks drilldown facts of a single recovery case in the evaluation dataset.
    """
    result_id: str = Field(..., description="Unique result identifier")
    evaluation_id: str = Field(..., description="Reference to the parent EvaluationRun")
    case_id: str = Field(..., description="Reference to the associated recovery case")
    payment_id: str = Field(..., description="Reference to the original payment")
    amount: int = Field(..., ge=0, description="Transaction amount in paise")
    initial_status: str = Field(..., description="Original payment status, e.g. failed")
    root_cause: str = Field(..., description="Classified root cause, e.g. TRANSIENT_FAILURE")
    
    # AI and Policy Result
    ai_action: str = Field(..., description="AI recommended action, e.g. RETRY")
    ai_confidence: float = Field(..., description="AI confidence score")
    policy_decision: str = Field(..., description="Policy Engine final decision, e.g. ALLOW")
    
    # Execution
    execution_status: str = Field(..., description="Execution status, e.g. SUCCEEDED, BLOCKED, ESCALATED, etc.")
    final_payment_status: str = Field(..., description="Final gateway status, e.g. captured, failed")
    amount_recovered: int = Field(0, ge=0, description="Recovered amount in paise (only if captured)")
    
    stop_reason: Optional[str] = Field(None, description="Detailed stopping reason if stopped")
    escalation_reason: Optional[str] = Field(None, description="Detailed escalation reason if escalated")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
