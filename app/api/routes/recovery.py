from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from app.api.dependencies import get_db, get_ai_provider
from app.services.ai_service import AIProvider
from app.services.recovery_agent import RecoveryAgentService

router = APIRouter()

class AIRecommendationModel(BaseModel):
    action: str = Field(..., description="Action recommended by AI")
    confidence: float = Field(..., description="Confidence score")
    reason: str = Field(..., description="Reasoning/justification")

class PolicyDecisionModel(BaseModel):
    decision: str = Field(..., description="Policy decision result (ALLOW, BLOCK, ESCALATE)")
    reason: str = Field(..., description="Summary explanation of the decision")

class DecideRecoveryResponse(BaseModel):
    case_id: str = Field(..., description="Associated recovery case ID")
    ai_recommendation: AIRecommendationModel = Field(..., description="AI Recommendation details")
    policy_decision: PolicyDecisionModel = Field(..., description="Policy Engine decision outcome")

@router.post("/{case_id}/decide", response_model=DecideRecoveryResponse)
async def decide_recovery_action(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider)
):
    """
    Triggers AI analysis and deterministic guardrail evaluation for a specific recovery case.
    The response contains the recommended recovery action and whether it was authorized.
    No money is moved, and no payment operation is executed.
    """
    try:
        result = await RecoveryAgentService.decide_recovery_action(db, case_id, ai_provider=ai_provider)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recovery decision processing failed: {str(e)}"
        )
