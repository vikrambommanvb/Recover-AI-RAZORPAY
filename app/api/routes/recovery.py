from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from app.api.dependencies import get_db, get_ai_provider, get_razorpay_service
from app.services.ai_service import AIProvider
from app.services.recovery_agent import RecoveryAgentService
from app.services.razorpay_service import RazorpayService
from app.services.recovery_executor import RecoveryExecutor
from app.services.risk_service import RiskService
from app.db.collections import RECOVERY_ACTIONS_COLLECTION
from app.models.recovery_action import RecoveryAction

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

class ExecuteRecoveryResponse(BaseModel):
    case_id: str = Field(..., description="Associated recovery case ID")
    action_id: str = Field(..., description="Generated/matched recovery action ID")
    decision: str = Field(..., description="Policy Engine decision")
    action: str = Field(..., description="Recovery action category")
    status: str = Field(..., description="Outcome execution status")
    amount: int = Field(..., description="Recovered/attempted amount in paise")
    currency: str = Field(..., description="3-letter currency code")

class CaseStatusResponse(BaseModel):
    case_id: str = Field(..., description="Unique case identifier")
    status: str = Field(..., description="Workflow status, e.g. PENDING, CLOSED")
    guardrail_status: str = Field(..., description="Guardrail status, e.g. allowed, blocked")
    risk_status: str = Field(..., description="Risk status, e.g. AT_RISK, NOT_AT_RISK")
    amount_at_risk: int = Field(..., description="Amount at risk in minor units (paise)")

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

@router.post("/{case_id}/execute", response_model=ExecuteRecoveryResponse)
async def execute_recovery(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    razorpay_service: RazorpayService = Depends(get_razorpay_service)
):
    """
    Triggers execution of the recovery plan for a case.
    Validates limits and credentials, and runs only allowed test mode operations.
    """
    try:
        result = await RecoveryExecutor.execute_recovery(db, case_id, razorpay_service)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recovery execution failed: {str(e)}"
        )

@router.get("/{case_id}/actions", response_model=List[RecoveryAction])
async def get_recovery_actions(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    List all recovery actions attempted for a specific case.
    """
    try:
        cursor = db[RECOVERY_ACTIONS_COLLECTION].find({"case_id": case_id}).sort("created_at", -1)
        actions = []
        async for doc in cursor:
            actions.append(RecoveryAction(**doc))
        return actions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )

@router.get("/{case_id}/status", response_model=CaseStatusResponse)
async def get_case_status(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get current workflow, risk, and guardrail status details for a recovery case.
    """
    try:
        case = await RiskService.get_recovery_case_by_id(db, case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recovery case with ID '{case_id}' not found."
            )
        return CaseStatusResponse(
            case_id=case.case_id,
            status=case.status,
            guardrail_status=case.guardrail_status,
            risk_status=case.risk_status,
            amount_at_risk=case.amount_at_risk
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )

