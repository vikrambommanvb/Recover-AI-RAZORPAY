import json
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from app.models.payment import Payment
from app.models.recovery import RecoveryCase

class SanitizedContext(BaseModel):
    payment_id: str
    amount: int
    currency: str
    payment_status: str
    failure_reason: Optional[str] = None
    root_cause: Optional[str] = None
    amount_at_risk: int
    customer_id: Optional[str] = None
    previous_payment_count: int = 0
    successful_payment_count: int = 0
    previous_failure_count: int = 0
    retry_count: int = 0
    recovery_case_status: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RecoveryContextBuilder:
    @staticmethod
    def sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Remove any potentially sensitive keys from payment metadata to ensure secrets
        are never sent to the AI provider.
        """
        if not metadata:
            return {}
        
        sensitive_keys = {
            "api_key", "secret", "password", "token", "credential", 
            "auth", "key", "cert", "private", "passphrase"
        }
        
        sanitized = {}
        for k, v in metadata.items():
            if any(sk in k.lower() for sk in sensitive_keys):
                continue
            sanitized[k] = v
        return sanitized

    @classmethod
    def build_context(cls, case: RecoveryCase, payment: Payment, retry_count: int) -> SanitizedContext:
        """
        Assemble and sanitize the context required by the AI provider to diagnose the case.
        """
        sanitized_metadata = cls.sanitize_metadata(payment.metadata)
        
        return SanitizedContext(
            payment_id=payment.payment_id,
            amount=payment.amount,
            currency=payment.currency,
            payment_status=payment.status,
            failure_reason=payment.failure_reason,
            root_cause=case.root_cause,
            amount_at_risk=case.amount_at_risk,
            customer_id=payment.customer_id,
            previous_payment_count=case.previous_payment_count,
            successful_payment_count=case.successful_payment_count,
            previous_failure_count=case.previous_failure_count,
            retry_count=retry_count,
            recovery_case_status=case.status,
            metadata=sanitized_metadata
        )
