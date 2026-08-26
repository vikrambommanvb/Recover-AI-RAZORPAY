from datetime import datetime, timezone
from typing import Optional, Tuple, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.payment import Payment
from app.models.recovery import RecoveryCase, RevenueRiskCase
from app.services.payment_service import PaymentService
from app.db.collections import RECOVERY_CASES_COLLECTION
from app.core.logging import logger
from app.integrations.razorpay_client import NormalizedPayment
from app.services.payment_state_verifier import PaymentStateVerifier
from app.services.root_cause_classifier import RootCauseClassifier

class RiskService:
    @staticmethod
    def classify_payment(payment: Payment) -> Tuple[str, Optional[str], int]:
        """
        Classifies a payment's risk status, root cause, and amount at risk.
        Returns a tuple: (risk_status, root_cause, amount_at_risk)
        """
        status = payment.status.lower()
        
        # 1. SUCCESS -> NOT_AT_RISK
        if status in ["captured", "authorized", "successful", "success"]:
            return "NOT_AT_RISK", None, 0
            
        # 2. FAILED
        if status == "failed":
            reason = (payment.failure_reason or "").lower()
            
            # Match root cause
            if any(kw in reason for kw in ["timeout", "connection lost", "network", "gateway timeout", "bank_timeout"]):
                return "AT_RISK", "TRANSIENT_FAILURE", payment.amount
            elif any(kw in reason for kw in ["insufficient", "balance", "funds", "limit", "insufficient_funds"]):
                return "AT_RISK", "CUSTOMER_FUNDS", payment.amount
            elif any(kw in reason for kw in ["declined", "issuer", "blocked", "restricted", "expired"]):
                return "AT_RISK", "PAYMENT_DECLINED", payment.amount
            elif any(kw in reason for kw in ["unknown"]):
                return "UNKNOWN", "UNKNOWN", payment.amount
            else:
                # Default for failed but unrecognized failure reason
                return "UNKNOWN", "UNKNOWN", payment.amount
                
        # 3. UNKNOWN payment state -> UNKNOWN
        return "UNKNOWN", "UNKNOWN", payment.amount

    @staticmethod
    async def get_recovery_case_by_id(db: AsyncIOMotorDatabase, case_id: str) -> Optional[RecoveryCase]:
        """Retrieve a specific recovery case by its case_id."""
        doc = await db[RECOVERY_CASES_COLLECTION].find_one({"case_id": case_id})
        if doc:
            return RecoveryCase(**doc)
        return None

    @staticmethod
    async def list_recovery_cases(db: AsyncIOMotorDatabase, limit: int = 100, offset: int = 0) -> List[RecoveryCase]:
        """List recovery cases with limit and offset pagination."""
        cursor = db[RECOVERY_CASES_COLLECTION].find().skip(offset).limit(limit)
        cases = []
        async for doc in cursor:
            cases.append(RecoveryCase(**doc))
        return cases

    @staticmethod
    async def analyze_payment(db: AsyncIOMotorDatabase, payment_id: str) -> RecoveryCase:
        """
        Analyzes a payment record, determines risk, fetches customer payment history context,
        and creates/persists a recovery case. Guaranteed to be idempotent: if a case already
        exists for the payment, it is reused.
        """
        # Fetch payment
        payment = await PaymentService.get_payment_by_id(db, payment_id)
        if not payment:
            raise ValueError(f"Payment with ID '{payment_id}' not found.")
            
        # Idempotency check: see if case already exists for payment_id
        existing_doc = await db[RECOVERY_CASES_COLLECTION].find_one({"payment_id": payment_id})
        if existing_doc:
            logger.info(f"Existing recovery case found for payment_id '{payment_id}'. Reusing case_id '{existing_doc['case_id']}'.")
            return RecoveryCase(**existing_doc)
            
        # Perform classification
        risk_status, root_cause, amount_at_risk = RiskService.classify_payment(payment)
        
        # Retrieve customer history (payments created before this one)
        history = await PaymentService.get_customer_history(db, payment.customer_id, payment.created_at)
        
        # Construct RecoveryCase
        case_id = f"case_{payment_id}"
        case = RecoveryCase(
            case_id=case_id,
            payment_id=payment.payment_id,
            amount_at_risk=amount_at_risk,
            risk_status=risk_status,
            root_cause=root_cause,
            status="PENDING",
            customer_id=payment.customer_id,
            failure_reason=payment.failure_reason,
            previous_payment_count=history["previous_payment_count"],
            successful_payment_count=history["successful_payment_count"],
            previous_failure_count=history["previous_failure_count"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Save to DB (using update_one with upsert to prevent race conditions)
        case_dict = case.model_dump()
        await db[RECOVERY_CASES_COLLECTION].update_one(
            {"payment_id": payment.payment_id},
            {"$set": case_dict},
            upsert=True
        )
        logger.info(f"Created new recovery case '{case_id}' for payment '{payment_id}' with status '{risk_status}'.")
        return case


class RevenueRiskDetector:
    """
    Analyzes normalized payments to detect if they represent recoverable revenue.
    """
    @staticmethod
    def detect_risk(payment: NormalizedPayment, retry_count: int = 0) -> RevenueRiskCase:
        # Determine root cause
        root_cause = RootCauseClassifier.classify(payment.failure_reason)
        
        # Determine eligibility
        eligible, reason = PaymentStateVerifier.get_recovery_eligibility(payment.status)
        
        # Map risk type
        status = payment.status.upper()
        reason_lower = (payment.failure_reason or "").lower()
        
        if status == "PENDING":
            risk_type = "CHECKOUT_ABANDONED"
        elif "subscription" in reason_lower or "recurring" in reason_lower:
            risk_type = "SUBSCRIPTION_PAYMENT_FAILED"
        elif "timeout" in reason_lower or "network" in reason_lower or "gateway" in reason_lower:
            risk_type = "PAYMENT_TIMEOUT"
        elif status == "FAILED":
            risk_type = "PAYMENT_FAILED"
        else:
            risk_type = "UNKNOWN"

        case_id = f"case_{payment.payment_id}"
        
        return RevenueRiskCase(
            case_id=case_id,
            payment_id=payment.payment_id,
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            risk_type=risk_type,
            root_cause=root_cause,
            detected_at=datetime.now(timezone.utc),
            retry_count=retry_count,
            eligibility=eligible,
            reason=reason
        )

