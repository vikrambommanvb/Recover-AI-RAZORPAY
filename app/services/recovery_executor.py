import uuid
from datetime import datetime, timezone
from typing import Optional
import httpx

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import settings
from app.core.logging import logger
from app.db.collections import (
    RECOVERY_ACTIONS_COLLECTION,
    AGENT_DECISIONS_COLLECTION,
    RECOVERY_CASES_COLLECTION,
    AUDIT_LOGS_COLLECTION,
    PAYMENTS_COLLECTION
)
from app.services.payment_service import PaymentService
from app.services.risk_service import RiskService
from app.services.razorpay_service import RazorpayService
from app.models.recovery_action import RecoveryAction, RecoveryActionStatus
from app.models.audit import AuditLog


class RecoveryExecutor:
    @staticmethod
    async def get_latest_action(db: AsyncIOMotorDatabase, case_id: str) -> Optional[RecoveryAction]:
        """Fetch the most recent recovery action for a case."""
        cursor = db[RECOVERY_ACTIONS_COLLECTION].find({"case_id": case_id}).sort("created_at", -1).limit(1)
        async for doc in cursor:
            return RecoveryAction(**doc)
        return None

    @staticmethod
    async def get_attempt_count(db: AsyncIOMotorDatabase, case_id: str) -> int:
        """Count the number of actual triggered recovery attempts for a case."""
        query = {
            "case_id": case_id,
            "status": {"$in": [
                RecoveryActionStatus.VERIFICATION_REQUIRED, 
                RecoveryActionStatus.SUCCEEDED, 
                RecoveryActionStatus.FAILED
            ]}
        }
        return await db[RECOVERY_ACTIONS_COLLECTION].count_documents(query)

    @staticmethod
    async def execute_recovery(db: AsyncIOMotorDatabase, case_id: str, razorpay_service: RazorpayService) -> dict:
        """
        Execute a recovery action for a case.
        Enforces:
        - Case existence and openness
        - Prior AI decision with ALLOW policy decision
        - Gateway-level payment state check (bypasses if already captured)
        - Max recovery amount limit (₹5,000 / 500000 paise)
        - Max retry attempt limit (2 attempts)
        - Cooldown period (300 seconds)
        - Request idempotency
        - Audit trail logging
        """
        # 1. Load Recovery Case
        case = await RiskService.get_recovery_case_by_id(db, case_id)
        if not case:
            raise ValueError(f"Recovery case with ID '{case_id}' not found.")
            
        if case.final_status == "closed" or case.status == "CLOSED":
            # If case is already closed, reject execution
            raise ValueError(f"Recovery case '{case_id}' is already closed.")

        # 2. Load Payment
        payment = await PaymentService.get_payment_by_id(db, case.payment_id)
        if not payment:
            raise ValueError(f"Payment with ID '{case.payment_id}' not found.")

        # 3. Load latest AI Decision
        cursor = db[AGENT_DECISIONS_COLLECTION].find({"case_id": case_id, "is_latest": True}).limit(1)
        latest_decision = None
        async for doc in cursor:
            latest_decision = doc
            
        if not latest_decision:
            raise ValueError(f"No AI recommendation found for case '{case_id}'. Decide recovery action first.")

        # 4. Check Policy Gate
        policy_result = latest_decision.get("policy_result", {})
        policy_decision = policy_result.get("decision", "BLOCK")
        if policy_decision != "ALLOW":
            raise ValueError(f"Safety Gate Rejection: AI action is not allowed by policy (decision is {policy_decision}).")

        # 5. Fetch current payment status on Razorpay
        try:
            logger.info(f"Verifying payment '{payment.payment_id}' state on Razorpay...")
            rzp_payment = await razorpay_service.fetch_payment(payment.payment_id)
            rzp_status = rzp_payment.get("status", "").lower()
            
            if rzp_status in ["captured", "authorized", "success", "successful"]:
                # Gateway shows payment succeeded, local DB is stale. Safe bypass / block retry!
                logger.warning(
                    f"Safety check: Payment '{payment.payment_id}' is already {rzp_status} on Razorpay. "
                    "Bypassing recovery attempt to prevent double capture."
                )
                # Sync local payment status
                payment.status = "captured"
                await PaymentService.save_payment(db, payment)
                
                # Sync recovery case status
                case.status = "CLOSED"
                case.final_status = "closed"
                case.guardrail_status = "allowed"
                case.amount_at_risk = 0
                await db[RECOVERY_CASES_COLLECTION].update_one(
                    {"case_id": case_id},
                    {"$set": case.model_dump()}
                )
                
                # Persist a BLOCKED recovery action
                action_id = f"act_{uuid.uuid4().hex[:8]}"
                action = RecoveryAction(
                    action_id=action_id,
                    case_id=case_id,
                    payment_id=payment.payment_id,
                    action_type=latest_decision.get("recommended_action"),
                    amount=payment.amount,
                    currency=payment.currency,
                    status=RecoveryActionStatus.BLOCKED,
                    attempt_number=await RecoveryExecutor.get_attempt_count(db, case_id) + 1,
                    policy_decision="BLOCK",
                    reason="Payment already successfully captured on Razorpay."
                )
                await db[RECOVERY_ACTIONS_COLLECTION].insert_one(action.model_dump())
                
                # Write audit event
                audit_id = f"aud_{uuid.uuid4().hex[:8]}"
                audit_log = AuditLog(
                    log_id=audit_id,
                    actor="system",
                    action="RECOVERY_BLOCKED_ALREADY_CAPTURED",
                    entity_type="recovery_case",
                    entity_id=case_id,
                    details={
                        "payment_id": payment.payment_id,
                        "action_id": action_id,
                        "reason": "Payment succeeded on gateway prior to execution."
                    }
                )
                await db[AUDIT_LOGS_COLLECTION].insert_one(audit_log.model_dump())
                
                return {
                    "case_id": case_id,
                    "action_id": action_id,
                    "decision": "BLOCK",
                    "action": "RECOVERY_BLOCKED",
                    "status": "BLOCKED",
                    "amount": payment.amount,
                    "currency": payment.currency
                }
        except Exception as e:
            # If fetching payment from gateway fails, log and proceed with safe local checks
            logger.warning(f"Unable to fetch payment '{payment.payment_id}' state from Razorpay: {e}. Relying on local checks.")

        # 6. Idempotency Check: check if there is an active/succeeded action
        existing_actions_cursor = db[RECOVERY_ACTIONS_COLLECTION].find({
            "case_id": case_id,
            "status": {"$in": [RecoveryActionStatus.VERIFICATION_REQUIRED, RecoveryActionStatus.SUCCEEDED]}
        }).limit(1)
        async for doc in existing_actions_cursor:
            logger.info(f"Idempotency hit: Case '{case_id}' already has action '{doc['action_id']}' in state '{doc['status']}'.")
            return {
                "case_id": case_id,
                "action_id": doc["action_id"],
                "decision": doc["policy_decision"],
                "action": "RECOVERY_ATTEMPT",
                "status": doc["status"],
                "amount": doc["amount"],
                "currency": doc["currency"]
            }

        # 7. Check Retry Limits
        attempt_count = await RecoveryExecutor.get_attempt_count(db, case_id)
        if attempt_count >= settings.MAX_RECOVERY_ATTEMPTS:
            logger.warning(f"Case '{case_id}' exceeded max attempts limit ({attempt_count}/{settings.MAX_RECOVERY_ATTEMPTS})")
            
            # Escalate the case
            case.status = "CLOSED"
            case.final_status = "closed"
            case.guardrail_status = "escalated"
            await db[RECOVERY_CASES_COLLECTION].update_one(
                {"case_id": case_id},
                {"$set": case.model_dump()}
            )
            
            action_id = f"act_{uuid.uuid4().hex[:8]}"
            action = RecoveryAction(
                action_id=action_id,
                case_id=case_id,
                payment_id=payment.payment_id,
                action_type=latest_decision.get("recommended_action"),
                amount=payment.amount,
                currency=payment.currency,
                status=RecoveryActionStatus.ESCALATED,
                attempt_number=attempt_count + 1,
                policy_decision="ESCALATE",
                reason=f"Recovery attempt limit reached ({attempt_count}). Escalated to human operator."
            )
            await db[RECOVERY_ACTIONS_COLLECTION].insert_one(action.model_dump())
            
            # Audit log
            audit_id = f"aud_{uuid.uuid4().hex[:8]}"
            audit_log = AuditLog(
                log_id=audit_id,
                actor="system",
                action="RECOVERY_ATTEMPTS_EXCEEDED",
                entity_type="recovery_case",
                entity_id=case_id,
                details={"attempts_count": attempt_count, "action_id": action_id}
            )
            await db[AUDIT_LOGS_COLLECTION].insert_one(audit_log.model_dump())
            
            return {
                "case_id": case_id,
                "action_id": action_id,
                "decision": "ESCALATE",
                "action": "RECOVERY_ESCALATED",
                "status": "ESCALATED",
                "amount": payment.amount,
                "currency": payment.currency
            }

        # 8. Check Cooldown Period
        latest_action = await RecoveryExecutor.get_latest_action(db, case_id)
        if latest_action:
            created_at = latest_action.created_at
            # Make timezone aware if it is naive
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            delta = (datetime.now(timezone.utc) - created_at).total_seconds()
            if delta < settings.RECOVERY_COOLDOWN_SECONDS:
                logger.warning(f"Cooldown period active for case '{case_id}'. Seconds elapsed: {delta:.1f}")
                action_id = f"act_{uuid.uuid4().hex[:8]}"
                action = RecoveryAction(
                    action_id=action_id,
                    case_id=case_id,
                    payment_id=payment.payment_id,
                    action_type=latest_decision.get("recommended_action"),
                    amount=payment.amount,
                    currency=payment.currency,
                    status=RecoveryActionStatus.BLOCKED,
                    attempt_number=attempt_count + 1,
                    policy_decision="BLOCK",
                    reason=f"Cooldown active. Please wait {settings.RECOVERY_COOLDOWN_SECONDS - delta:.0f} seconds."
                )
                await db[RECOVERY_ACTIONS_COLLECTION].insert_one(action.model_dump())
                return {
                    "case_id": case_id,
                    "action_id": action_id,
                    "decision": "BLOCK",
                    "action": "RECOVERY_BLOCKED",
                    "status": "BLOCKED",
                    "amount": payment.amount,
                    "currency": payment.currency
                }

        # 9. Check Amount Limits
        if payment.amount > settings.MAX_RECOVERY_AMOUNT_MINOR:
            logger.warning(f"Payment amount {payment.amount} paise exceeds max limit {settings.MAX_RECOVERY_AMOUNT_MINOR} paise.")
            action_id = f"act_{uuid.uuid4().hex[:8]}"
            action = RecoveryAction(
                action_id=action_id,
                case_id=case_id,
                payment_id=payment.payment_id,
                action_type=latest_decision.get("recommended_action"),
                amount=payment.amount,
                currency=payment.currency,
                status=RecoveryActionStatus.BLOCKED,
                attempt_number=attempt_count + 1,
                policy_decision="BLOCK",
                reason=f"Amount exceeds maximum recovery limit (₹{settings.MAX_RECOVERY_AMOUNT_MINOR/100:.2f})."
            )
            await db[RECOVERY_ACTIONS_COLLECTION].insert_one(action.model_dump())
            return {
                "case_id": case_id,
                "action_id": action_id,
                "decision": "BLOCK",
                "action": "RECOVERY_BLOCKED",
                "status": "BLOCKED",
                "amount": payment.amount,
                "currency": payment.currency
            }

        # 10. Execute Web Hook order creation (RETRY or REMIND)
        action_id = f"act_{uuid.uuid4().hex[:8]}"
        action = RecoveryAction(
            action_id=action_id,
            case_id=case_id,
            payment_id=payment.payment_id,
            action_type=latest_decision.get("recommended_action"),
            amount=payment.amount,
            currency=payment.currency,
            status=RecoveryActionStatus.EXECUTING,
            attempt_number=attempt_count + 1,
            policy_decision="ALLOW",
            reason="Recovery action execution started."
        )
        await db[RECOVERY_ACTIONS_COLLECTION].insert_one(action.model_dump())

        rec_action = latest_decision.get("recommended_action")
        if rec_action in ["RETRY", "REMIND"]:
            try:
                # Create Order on Razorpay
                order_response = await razorpay_service.create_order(
                    amount=payment.amount,
                    currency=payment.currency,
                    receipt=case_id
                )
                
                razorpay_order_id = order_response.get("id")
                
                # Update status to VERIFICATION_REQUIRED
                action.status = RecoveryActionStatus.VERIFICATION_REQUIRED
                action.razorpay_order_id = razorpay_order_id
                action.reason = f"Created Razorpay order '{razorpay_order_id}'. Awaiting customer payment webhook."
                action.updated_at = datetime.now(timezone.utc)
                await db[RECOVERY_ACTIONS_COLLECTION].update_one(
                    {"action_id": action_id},
                    {"$set": action.model_dump()}
                )
                
                # Update case status
                await db[RECOVERY_CASES_COLLECTION].update_one(
                    {"case_id": case_id},
                    {"$set": {"status": "IN_PROGRESS", "updated_at": datetime.now(timezone.utc)}}
                )
                
                # Audit log
                audit_id = f"aud_{uuid.uuid4().hex[:8]}"
                audit_log = AuditLog(
                    log_id=audit_id,
                    actor="system",
                    action="RECOVERY_ATTEMPT_CREATED",
                    entity_type="recovery_case",
                    entity_id=case_id,
                    details={
                        "action_id": action_id,
                        "razorpay_order_id": razorpay_order_id,
                        "attempt_number": action.attempt_number
                    }
                )
                await db[AUDIT_LOGS_COLLECTION].insert_one(audit_log.model_dump())
                
                return {
                    "case_id": case_id,
                    "action_id": action_id,
                    "decision": "ALLOW",
                    "action": "RECOVERY_ATTEMPT",
                    "status": "VERIFICATION_REQUIRED",
                    "amount": payment.amount,
                    "currency": payment.currency
                }
            except Exception as e:
                # API failure / Timeout handled gracefully
                logger.error(f"Razorpay order creation failed for case '{case_id}': {e}")
                action.status = RecoveryActionStatus.FAILED
                action.reason = f"Razorpay API Error: {str(e)}"
                action.updated_at = datetime.now(timezone.utc)
                await db[RECOVERY_ACTIONS_COLLECTION].update_one(
                    {"action_id": action_id},
                    {"$set": action.model_dump()}
                )
                
                # Audit log
                audit_id = f"aud_{uuid.uuid4().hex[:8]}"
                audit_log = AuditLog(
                    log_id=audit_id,
                    actor="system",
                    action="RECOVERY_ATTEMPT_FAILED",
                    entity_type="recovery_case",
                    entity_id=case_id,
                    details={
                        "action_id": action_id,
                        "error": str(e)
                    }
                )
                await db[AUDIT_LOGS_COLLECTION].insert_one(audit_log.model_dump())
                
                return {
                    "case_id": case_id,
                    "action_id": action_id,
                    "decision": "ALLOW",
                    "action": "RECOVERY_ATTEMPT",
                    "status": "FAILED",
                    "amount": payment.amount,
                    "currency": payment.currency
                }
        else:
            # STOP or other AI recommendations that are ALLOWED but don't call Razorpay
            action.status = RecoveryActionStatus.BLOCKED
            action.reason = f"AI recommended action is '{rec_action}', no gateway execution necessary."
            action.updated_at = datetime.now(timezone.utc)
            await db[RECOVERY_ACTIONS_COLLECTION].update_one(
                {"action_id": action_id},
                {"$set": action.model_dump()}
            )
            return {
                "case_id": case_id,
                "action_id": action_id,
                "decision": "ALLOW",
                "action": "RECOVERY_SKIPPED",
                "status": "BLOCKED",
                "amount": payment.amount,
                "currency": payment.currency
            }
