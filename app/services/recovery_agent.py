import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import settings
from app.core.logging import logger
from app.db.collections import (
    AGENT_DECISIONS_COLLECTION,
    AUDIT_LOGS_COLLECTION,
    RECOVERY_CASES_COLLECTION
)
from app.services.payment_service import PaymentService
from app.services.risk_service import RiskService
from app.services.context_builder import RecoveryContextBuilder
from app.services.ai_service import get_ai_provider
from app.ai.schemas import AIServiceRequest, AIServiceResponse
from app.models.agent_decision import AgentDecision, RecoveryAction
from app.models.audit import AuditLog
from app.guardrails.policy_engine import (
    PolicyEngine,
    MaxAmountRule,
    MinConfidenceRule,
    PaymentStatusRule,
    RetryLimitRule,
    EscalationRule,
    PolicyDecision
)

class RecoveryAgentService:
    @staticmethod
    async def get_authorized_retry_count(db: AsyncIOMotorDatabase, case_id: str) -> int:
        """
        Count the number of prior RETRY decisions for the given case that were
        allowed/authorized by the PolicyEngine.
        """
        query = {
            "case_id": case_id,
            "recommended_action": RecoveryAction.RETRY,
            "policy_result.decision": PolicyDecision.ALLOW
        }
        count = await db[AGENT_DECISIONS_COLLECTION].count_documents(query)
        return count

    @staticmethod
    async def decide_recovery_action(
        db: AsyncIOMotorDatabase, 
        case_id: str,
        ai_provider = None
    ) -> dict:
        """
        Execute the Recovery Decision pipeline for a specific Recovery Case.
        
        Steps:
        1. Load Recovery Case
        2. Load Payment
        3. Dynamic retry count lookup and payment metadata injection
        4. AI bypass optimization (NO_ACTION if payment already captured)
        5. Build sanitized case context
        6. Query AI Provider (with exponential backoff and safe escalation fallback)
        7. Evaluate AI recommendation with PolicyEngine
        8. Persist the decision record (setting previous decisions' is_latest to False)
        9. Write audit log
        10. Update case status in database
        11. Return structured response payload
        """
        # 1. Load Recovery Case
        case = await RiskService.get_recovery_case_by_id(db, case_id)
        if not case:
            raise ValueError(f"Recovery case with ID '{case_id}' not found.")
            
        # 2. Load Payment
        payment = await PaymentService.get_payment_by_id(db, case.payment_id)
        if not payment:
            raise ValueError(f"Payment with ID '{case.payment_id}' not found for case '{case_id}'.")
            
        # 3. Dynamic retry count lookup
        retry_count = await RecoveryAgentService.get_authorized_retry_count(db, case_id)
        
        # Inject retry count into payment metadata so PolicyRules can inspect it
        payment.metadata = payment.metadata or {}
        payment.metadata["retry_count"] = retry_count
        
        # 4. AI Bypass Optimization: If payment already successful, bypass LLM
        status = payment.status.lower() if payment.status else ""
        if status in ["captured", "authorized", "successful", "success"]:
            logger.info(f"Payment '{payment.payment_id}' is already successful. Bypassing AI call.")
            recommendation = AIServiceResponse(
                action=RecoveryAction.NO_ACTION,
                confidence=1.0,
                reason="Payment is already successful. AI decision bypassed.",
                root_cause=case.root_cause or "captured",
                risk_factors=[],
                recommended_message_type=None,
                requires_human_review=False
            )
        else:
            # 5. Build Sanitized Context
            context = RecoveryContextBuilder.build_context(case, payment, retry_count)
            
            # 6. Call AI Provider with Safe Fallback
            if ai_provider is None:
                ai_provider = get_ai_provider()
            ai_request = AIServiceRequest(
                payment_id=payment.payment_id,
                amount=payment.amount,
                currency=payment.currency,
                failure_reason=payment.failure_reason or "",
                customer_id=payment.customer_id or "",
                metadata=context.metadata
            )
            
            try:
                logger.info(f"Invoking AI Provider '{settings.AI_PROVIDER}' for case '{case_id}'")
                recommendation = await ai_provider.analyze_payment_failure(ai_request)
                logger.info(f"AI Provider recommendation for case '{case_id}': {recommendation.action} (Confidence: {recommendation.confidence})")
            except Exception as e:
                logger.error(f"AI Provider failed for case '{case_id}': {e}. Falling back to ESCALATE.")
                # Safe fallback escalation
                recommendation = AIServiceResponse(
                    action=RecoveryAction.ESCALATE,
                    confidence=1.0,
                    reason=f"AI provider failed: {str(e)}. Safe escalation fallback.",
                    root_cause=case.root_cause or "UNKNOWN",
                    risk_factors=["ai_provider_error"],
                    recommended_message_type=None,
                    requires_human_review=True
                )

        # 7. Policy Engine Evaluation
        # Register standard rules, configuring MinConfidenceRule to ESCALATE on failure
        rules = [
            MaxAmountRule(),
            MinConfidenceRule(min_confidence=0.60, action=PolicyDecision.ESCALATE),
            PaymentStatusRule(),
            RetryLimitRule(),
            EscalationRule()
        ]
        policy_engine = PolicyEngine(rules=rules)
        
        agent_decision = AgentDecision(
            action=recommendation.action,
            confidence=recommendation.confidence,
            reason=recommendation.reason,
            risk_factors=recommendation.risk_factors
        )
        
        policy_response = policy_engine.evaluate(payment, agent_decision)
        logger.info(f"PolicyEngine evaluation completed for case '{case_id}': {policy_response.decision}")

        # 8. Persist Decision
        # Ensure previous decisions are not marked as latest
        await db[AGENT_DECISIONS_COLLECTION].update_many(
            {"case_id": case_id, "is_latest": True},
            {"$set": {"is_latest": False}}
        )
        
        decision_id = f"dec_{uuid.uuid4().hex[:8]}"
        decision_doc = {
            "decision_id": decision_id,
            "case_id": case_id,
            "payment_id": payment.payment_id,
            "ai_provider": settings.AI_PROVIDER,
            "ai_model": settings.GROQ_MODEL if settings.AI_PROVIDER.lower() == "groq" else "mock",
            "recommended_action": recommendation.action,
            "confidence": recommendation.confidence,
            "reason": recommendation.reason,
            "risk_factors": recommendation.risk_factors,
            "recommended_message_type": recommendation.recommended_message_type,
            "requires_human_review": recommendation.requires_human_review,
            "policy_result": policy_response.model_dump(),
            "is_latest": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db[AGENT_DECISIONS_COLLECTION].insert_one(decision_doc)
        logger.info(f"Persisted agent decision '{decision_id}' for case '{case_id}'")

        # 9. Update Recovery Case in Database
        await db[RECOVERY_CASES_COLLECTION].update_one(
            {"case_id": case_id},
            {
                "$set": {
                    "recommended_action": recommendation.action,
                    "guardrail_status": policy_response.decision.lower(),
                    "status": "CLOSED" if policy_response.decision == PolicyDecision.BLOCK else "IN_PROGRESS",
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        # 10. Write Audit Log
        audit_id = f"aud_{uuid.uuid4().hex[:8]}"
        audit_log = AuditLog(
            log_id=audit_id,
            actor="system",
            action="RECOVERY_DECISION_MADE",
            entity_type="recovery_case",
            entity_id=case_id,
            details={
                "payment_id": payment.payment_id,
                "decision_id": decision_id,
                "ai_provider": settings.AI_PROVIDER,
                "ai_recommendation": {
                    "action": recommendation.action,
                    "confidence": recommendation.confidence,
                    "reason": recommendation.reason,
                    "risk_factors": recommendation.risk_factors,
                    "recommended_message_type": recommendation.recommended_message_type,
                    "requires_human_review": recommendation.requires_human_review
                },
                "policy_decision": policy_response.model_dump()
            },
            timestamp=datetime.now(timezone.utc)
        )
        await db[AUDIT_LOGS_COLLECTION].insert_one(audit_log.model_dump())
        logger.info(f"Written audit log '{audit_id}' for decision '{decision_id}'")

        # 11. Return response payload
        return {
            "case_id": case_id,
            "ai_recommendation": {
                "action": recommendation.action,
                "confidence": recommendation.confidence,
                "reason": recommendation.reason
            },
            "policy_decision": {
                "decision": policy_response.decision,
                "reason": policy_response.reason
            }
        }
