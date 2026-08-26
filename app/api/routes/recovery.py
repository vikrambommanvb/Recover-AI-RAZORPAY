from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from datetime import datetime

from app.api.dependencies import get_db, get_ai_provider, get_razorpay_client
from app.integrations.razorpay_client import RazorpayClient, NormalizedPayment
from app.services.ai_service import AIProvider
from app.services.recovery_agent import RecoveryAgentService
from app.services.recovery_executor import RecoveryExecutor
from app.services.recovery_service import RecoveryService, RecoveryResult
from app.services.risk_service import RiskService, RevenueRiskDetector
from app.db.collections import (
    RECOVERY_ACTIONS_COLLECTION, 
    RECOVERY_CASES_COLLECTION, 
    AUDIT_LOGS_COLLECTION,
    PAYMENTS_COLLECTION
)
from app.models.recovery import RecoveryCase
from app.models.recovery_action import RecoveryAction
from app.models.payment import Payment

router = APIRouter()

# Schema definitions
class CaseCreateRequest(BaseModel):
    payment_id: str = Field(..., description="Unique payment identifier to analyze and recovery")

class CaseResponse(BaseModel):
    case_id: str
    payment_id: str
    amount_minor: int
    currency: str
    risk_type: str
    root_cause: str
    detected_at: datetime
    retry_count: int
    eligibility: bool
    reason: str

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

class VerifyRecoveryResponse(BaseModel):
    case_id: str
    verification_status: str
    gateway_status: str
    recovered_amount_minor: int

class MetricsResponse(BaseModel):
    revenue_at_risk: int
    recovery_attempted: int
    revenue_recovered: int
    recovery_rate: float
    attempts: int
    success_recoveries: int
    failed_recoveries: int
    blocked_actions: int
    escalations: int
    stopped_cases: int
    unknown_outcomes: int

# Old endpoints (maintained for backward compatibility)
@router.post("/{case_id}/decide", response_model=DecideRecoveryResponse)
async def decide_recovery_action(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider)
):
    try:
        result = await RecoveryAgentService.decide_recovery_action(db, case_id, ai_provider=ai_provider)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{case_id}/execute", response_model=ExecuteRecoveryResponse)
async def execute_recovery(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    razorpay_client = Depends(get_razorpay_client)
):
    try:
        result = await RecoveryExecutor.execute_recovery(db, case_id, razorpay_client)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{case_id}/actions", response_model=List[RecoveryAction])
async def get_recovery_actions(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    try:
        cursor = db[RECOVERY_ACTIONS_COLLECTION].find({"case_id": case_id}).sort("created_at", -1)
        actions = []
        async for doc in cursor:
            actions.append(RecoveryAction(**doc))
        return actions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{case_id}/status")
async def get_case_status(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    try:
        case = await RiskService.get_recovery_case_by_id(db, case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Recovery case '{case_id}' not found.")
        return case
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Phase 6 Endpoints under /api/recovery prefix
@router.post("/cases", response_model=CaseResponse)
async def create_recovery_case(
    req: CaseCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Detect and create a recovery case from raw payment ID."""
    try:
        # Load payment
        payment_doc = await db[PAYMENTS_COLLECTION].find_one({"payment_id": req.payment_id})
        if not payment_doc:
            raise HTTPException(status_code=404, detail=f"Payment with ID '{req.payment_id}' not found.")
        
        # Analyze payment and generate RecoveryCase
        case = await RiskService.analyze_payment(db, req.payment_id)
        
        # Convert raw payment to NormalizedPayment for risk detector
        norm_payment = NormalizedPayment(
            payment_id=payment_doc.get("payment_id"),
            order_id=payment_doc.get("order_id"),
            amount_minor=payment_doc.get("amount"),
            currency=payment_doc.get("currency", "INR"),
            status=payment_doc.get("status", "failed"),
            created_at=payment_doc.get("created_at") or datetime.now(),
            captured=payment_doc.get("status") == "captured",
            failure_reason=payment_doc.get("failure_reason")
        )
        
        # Run Risk Detector
        risk_case = RevenueRiskDetector.detect_risk(norm_payment, retry_count=case.retry_count)
        
        # Save extended fields to DB
        await db[RECOVERY_CASES_COLLECTION].update_one(
            {"case_id": case.case_id},
            {"$set": {
                "risk_type": risk_case.risk_type,
                "root_cause": risk_case.root_cause,
                "eligibility": risk_case.eligibility,
                "reason": risk_case.reason,
                "detected_at": risk_case.detected_at
            }}
        )
        
        return CaseResponse(
            case_id=case.case_id,
            payment_id=case.payment_id,
            amount_minor=risk_case.amount_minor,
            currency=risk_case.currency,
            risk_type=risk_case.risk_type,
            root_cause=risk_case.root_cause,
            detected_at=risk_case.detected_at,
            retry_count=case.retry_count,
            eligibility=risk_case.eligibility,
            reason=risk_case.reason
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{case_id}/recommend", response_model=DecideRecoveryResponse)
async def recommend_recovery(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider)
):
    """Run root cause classifier and prompt AI for recommendation."""
    try:
        # Load Case
        case = await RiskService.get_recovery_case_by_id(db, case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Recovery case '{case_id}' not found.")
            
        # Invoke decide pipeline
        result = await RecoveryAgentService.decide_recovery_action(db, case_id, ai_provider=ai_provider)
        return DecideRecoveryResponse(
            case_id=case_id,
            ai_recommendation=AIRecommendationModel(
                action=result["ai_recommendation"]["action"],
                confidence=result["ai_recommendation"]["confidence"],
                reason=result["ai_recommendation"]["reason"]
            ),
            policy_decision=PolicyDecisionModel(
                decision=result["policy_decision"]["decision"],
                reason=result["policy_decision"]["reason"]
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{case_id}/verify", response_model=VerifyRecoveryResponse)
async def verify_recovery(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    razorpay_client = Depends(get_razorpay_client)
):
    """Verify execution outcome against Razorpay payment gateway."""
    try:
        res = await RecoveryExecutor.verify_recovery(db, case_id, razorpay_client)
        return VerifyRecoveryResponse(
            case_id=case_id,
            verification_status=res["verification_status"],
            gateway_status=res["gateway_status"],
            recovered_amount_minor=res["recovered_amount_minor"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{case_id}/run", response_model=RecoveryResult)
async def run_recovery_lifecycle(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
    razorpay_client = Depends(get_razorpay_client)
):
    """Execute the full end-to-end recovery orchestration flow."""
    try:
        res = await RecoveryService.recover(db, case_id, razorpay_client, ai_provider)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Retrieve recovery case details."""
    case = await RiskService.get_recovery_case_by_id(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Recovery case '{case_id}' not found.")
    
    # Map back to CaseResponse
    return CaseResponse(
        case_id=case.case_id,
        payment_id=case.payment_id,
        amount_minor=case.amount_at_risk,
        currency="INR",
        risk_type=getattr(case, "risk_type", "UNKNOWN"),
        root_cause=case.root_cause or "UNKNOWN",
        detected_at=getattr(case, "detected_at", datetime.now()),
        retry_count=case.retry_count,
        eligibility=getattr(case, "eligibility", True),
        reason=getattr(case, "reason", "Eligible")
    )

@router.get("/{case_id}/audit")
async def get_case_audit(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get all audit trail logs for a case."""
    cursor = db[AUDIT_LOGS_COLLECTION].find({"entity_id": case_id}).sort("timestamp", 1)
    logs = []
    async for doc in cursor:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        logs.append(doc)
    return logs

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get aggregated recovery metrics."""
    try:
        # Total revenue at risk
        risk_cursor = db[RECOVERY_CASES_COLLECTION].find()
        revenue_at_risk = 0
        async for doc in risk_cursor:
            # Only count failed or unknown state payments as at risk
            revenue_at_risk += doc.get("amount_at_risk", 0)
            
        # Total revenue recovered
        action_cursor = db[RECOVERY_ACTIONS_COLLECTION].find({"status": "SUCCEEDED"})
        revenue_recovered = 0
        async for doc in action_cursor:
            revenue_recovered += doc.get("amount", 0)
            
        total_attempts = await db[RECOVERY_ACTIONS_COLLECTION].count_documents({"status": {"$in": ["SUCCEEDED", "FAILED", "VERIFICATION_REQUIRED"]}})
        success_recoveries = await db[RECOVERY_ACTIONS_COLLECTION].count_documents({"status": "SUCCEEDED"})
        failed_recoveries = await db[RECOVERY_ACTIONS_COLLECTION].count_documents({"status": "FAILED"})
        blocked_actions = await db[RECOVERY_ACTIONS_COLLECTION].count_documents({"status": "BLOCKED"})
        escalations = await db[RECOVERY_ACTIONS_COLLECTION].count_documents({"status": "ESCALATED"})
        stopped_cases = await db[RECOVERY_CASES_COLLECTION].count_documents({"status": "CLOSED", "guardrail_status": "blocked"})
        unknown_outcomes = await db[RECOVERY_ACTIONS_COLLECTION].count_documents({"status": "UNKNOWN"})
        
        recovery_rate = 0.0
        if revenue_at_risk > 0:
            recovery_rate = float(revenue_recovered) / float(revenue_at_risk)
            
        return MetricsResponse(
            revenue_at_risk=revenue_at_risk,
            recovery_attempted=total_attempts,
            revenue_recovered=revenue_recovered,
            recovery_rate=recovery_rate,
            attempts=total_attempts,
            success_recoveries=success_recoveries,
            failed_recoveries=failed_recoveries,
            blocked_actions=blocked_actions,
            escalations=escalations,
            stopped_cases=stopped_cases,
            unknown_outcomes=unknown_outcomes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
