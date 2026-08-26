import uuid
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from app.core.logging import logger
from app.db.collections import (
    RECOVERY_CASES_COLLECTION,
    AUDIT_LOGS_COLLECTION,
    AGENT_DECISIONS_COLLECTION,
    PAYMENTS_COLLECTION
)
from app.models.recovery import RecoveryCase, RevenueRiskCase
from app.models.audit import AuditLog
from app.integrations.razorpay_client import RazorpayClient, get_razorpay_client
from app.services.risk_service import RiskService, RevenueRiskDetector
from app.services.root_cause_classifier import RootCauseClassifier
from app.services.recovery_agent import RecoveryAgentService
from app.services.recovery_executor import RecoveryExecutor
from app.services.payment_service import PaymentService
from app.ai.schemas import AIServiceRequest
from app.services.ai_service import get_ai_provider


class RecoveryResult(BaseModel):
    """Result details returned after running the recovery lifecycle orchestration."""
    case_id: str
    recommended_action: Optional[str] = None
    policy_decision: str
    execution_status: str
    verification_status: str
    recovered_amount_minor: int
    final_outcome: str
    audit_reference: str


class RecoveryService:
    """
    Central orchestration service for RecoverAI.
    Manages end-to-end lifecycle flow:
    Detection -> AI Recommendation -> Policy Gate -> Execution -> Verification.
    """
    @staticmethod
    async def recover(db: AsyncIOMotorDatabase, case_id: str, razorpay_client: Optional[RazorpayClient] = None, ai_provider = None) -> RecoveryResult:
        if razorpay_client is None:
            razorpay_client = get_razorpay_client()
        if ai_provider is None:
            ai_provider = get_ai_provider()

        logger.info(f"Orchestrated Recovery lifecycle start for case '{case_id}'")

        # 1. Load Recovery Case
        case = await RiskService.get_recovery_case_by_id(db, case_id)
        if not case:
            raise ValueError(f"Recovery case with ID '{case_id}' not found.")

        # 2. Retrieve Payment & Verify Gateway State
        payment = await PaymentService.get_payment_by_id(db, case.payment_id)
        if not payment:
            raise ValueError(f"Associated payment record '{case.payment_id}' not found.")

        normalized_payment = await razorpay_client.get_payment(payment.payment_id)
        
        # 3. Detect Risk Deterministically
        risk_case = RevenueRiskDetector.detect_risk(normalized_payment, retry_count=case.retry_count)
        
        # Update case model with risk classification parameters
        case.risk_type = risk_case.risk_type
        case.root_cause = risk_case.root_cause
        case.eligibility = risk_case.eligibility
        case.reason = risk_case.reason
        await db[RECOVERY_CASES_COLLECTION].update_one(
            {"case_id": case_id},
            {"$set": case.model_dump()}
        )

        # 4. Check Eligibility
        if not risk_case.eligibility:
            # Not eligible for active recovery
            audit_id = f"aud_{uuid.uuid4().hex[:8]}"
            audit_log = AuditLog(
                log_id=audit_id,
                actor="system",
                action="RECOVERY_SKIPPED_INELIGIBLE",
                entity_type="recovery_case",
                entity_id=case_id,
                details={"reason": risk_case.reason}
            )
            await db[AUDIT_LOGS_COLLECTION].insert_one(audit_log.model_dump())
            
            return RecoveryResult(
                case_id=case_id,
                recommended_action="NO_ACTION",
                policy_decision="BLOCK",
                execution_status="BLOCKED",
                verification_status="UNKNOWN",
                recovered_amount_minor=0,
                final_outcome="Skipped: Case is not eligible for recovery.",
                audit_reference=audit_id
            )

        # 5. Run AI Recommendation & Policy Engine Guardrails
        decision_payload = await RecoveryAgentService.decide_recovery_action(
            db, case_id, ai_provider=ai_provider
        )
        recommended_action = decision_payload["ai_recommendation"]["action"]
        policy_decision = decision_payload["policy_decision"]["decision"]
        policy_reason = decision_payload["policy_decision"]["reason"]

        execution_status = "NOT_ATTEMPTED"
        verification_status = "UNKNOWN"
        recovered_amount = 0
        final_outcome = f"Policy evaluated: {policy_decision}. {policy_reason}"
        audit_id = f"aud_{uuid.uuid4().hex[:8]}"

        # 6. Safe execution & gateway verification (only for ALLOW decision)
        if policy_decision == "ALLOW":
            try:
                # Trigger retry execution link
                exec_result = await RecoveryExecutor.execute_recovery(db, case_id, razorpay_client)
                execution_status = exec_result.get("status", "FAILED")
                
                if execution_status == "VERIFICATION_REQUIRED":
                    # Verify capture outcome status on the gateway
                    verify_result = await RecoveryExecutor.verify_recovery(db, case_id, razorpay_client)
                    verification_status = verify_result.get("verification_status", "UNKNOWN")
                    recovered_amount = verify_result.get("recovered_amount_minor", 0)
                    
                    if verification_status == "VERIFIED_SUCCESS":
                        final_outcome = "Recovery succeeded and transaction capture verified."
                    else:
                        final_outcome = f"Recovery attempt executed, but verification status resolved to {verification_status}."
                else:
                    final_outcome = f"Execution completed with status {execution_status}."
            except Exception as e:
                logger.error(f"Error during execution/verification logic: {e}")
                execution_status = "FAILED"
                final_outcome = f"Execution failed: {str(e)}"
        else:
            execution_status = "BLOCKED"

        # 7. Write final outcome audit log
        audit_log = AuditLog(
            log_id=audit_id,
            actor="system",
            action="RECOVERY_LIFECYCLE_COMPLETED",
            entity_type="recovery_case",
            entity_id=case_id,
            details={
                "recommended_action": recommended_action,
                "policy_decision": policy_decision,
                "execution_status": execution_status,
                "verification_status": verification_status,
                "recovered_amount": recovered_amount,
                "outcome": final_outcome
            }
        )
        await db[AUDIT_LOGS_COLLECTION].insert_one(audit_log.model_dump())

        # Update case retry count if execution was attempted
        if execution_status in ["VERIFICATION_REQUIRED", "SUCCESS", "FAILED"]:
            await db[RECOVERY_CASES_COLLECTION].update_one(
                {"case_id": case_id},
                {"$inc": {"retry_count": 1}}
            )

        return RecoveryResult(
            case_id=case_id,
            recommended_action=recommended_action,
            policy_decision=policy_decision,
            execution_status=execution_status,
            verification_status=verification_status,
            recovered_amount_minor=recovered_amount,
            final_outcome=final_outcome,
            audit_reference=audit_id
        )
