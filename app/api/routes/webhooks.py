import hmac
import hashlib
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.dependencies import get_db
from app.core.config import settings
from app.core.logging import logger
from app.db.collections import (
    WEBHOOK_EVENTS_COLLECTION,
    RECOVERY_ACTIONS_COLLECTION,
    RECOVERY_CASES_COLLECTION,
    PAYMENTS_COLLECTION,
    AUDIT_LOGS_COLLECTION
)
from app.models.recovery_action import RecoveryActionStatus
from app.models.audit import AuditLog

router = APIRouter()


def verify_razorpay_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Validate Razorpay signature using HMAC SHA256."""
    if not secret:
        logger.error("Webhook secret is unconfigured. Signature verification failed.")
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Idempotently handles payment gateway status updates from Razorpay Webhook.
    Validates X-Razorpay-Signature against the raw request body before processing.
    """
    raw_body = await request.body()
    
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not signature:
        logger.warning("Webhook rejected: Missing X-Razorpay-Signature header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature header."
        )

    if not verify_razorpay_signature(raw_body, signature, settings.RAZORPAY_WEBHOOK_SECRET or ""):
        logger.warning("Webhook rejected: Signature validation failed.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature validation failed."
        )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        logger.error(f"Malformed webhook JSON payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload."
        )

    event_id = payload.get("id")
    event_type = payload.get("event")
    if not event_id or not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event ID or type."
        )

    logger.info(f"Received Webhook Event ID: {event_id} (Type: {event_type})")

    # Idempotency Check
    existing_event = await db[WEBHOOK_EVENTS_COLLECTION].find_one({"event_id": event_id})
    if existing_event:
        logger.info(f"Webhook Event ID {event_id} already processed. Skipping duplicate.")
        return {"status": "ok", "message": "Event already processed."}

    # Persist pending event record
    event_record = {
        "event_id": event_id,
        "event_type": event_type,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "processing_status": "PENDING",
        "payload": payload
    }
    await db[WEBHOOK_EVENTS_COLLECTION].insert_one(event_record)

    try:
        event_payload = payload.get("payload", {})
        payment_data = event_payload.get("payment", {}).get("entity", {})
        
        rzp_payment_id = payment_data.get("id")
        rzp_order_id = payment_data.get("order_id")
        rzp_status = payment_data.get("status", "").lower()
        rzp_amount = payment_data.get("amount")
        
        if rzp_order_id:
            # Find the corresponding recovery action waiting for payment completion
            action_doc = await db[RECOVERY_ACTIONS_COLLECTION].find_one({
                "razorpay_order_id": rzp_order_id,
                "status": RecoveryActionStatus.VERIFICATION_REQUIRED
            })
            
            if action_doc:
                action_id = action_doc["action_id"]
                case_id = action_doc["case_id"]
                
                # Check for state transitions
                if rzp_status == "captured":
                    # Update action status to SUCCEEDED
                    await db[RECOVERY_ACTIONS_COLLECTION].update_one(
                        {"action_id": action_id},
                        {"$set": {
                            "status": RecoveryActionStatus.SUCCEEDED,
                            "razorpay_payment_id": rzp_payment_id,
                            "reason": "Payment captured successfully on gateway. Recovery completed.",
                            "updated_at": datetime.now(timezone.utc)
                        }}
                    )
                    
                    # Update Case to CLOSED / ALLOWED
                    await db[RECOVERY_CASES_COLLECTION].update_one(
                        {"case_id": case_id},
                        {"$set": {
                            "status": "CLOSED",
                            "final_status": "closed",
                            "guardrail_status": "allowed",
                            "amount_at_risk": 0,
                            "updated_at": datetime.now(timezone.utc)
                        }}
                    )
                    
                    # Sync local Payment model status to captured
                    await db[PAYMENTS_COLLECTION].update_one(
                        {"payment_id": action_doc["payment_id"]},
                        {"$set": {
                            "status": "captured",
                            "updated_at": datetime.now(timezone.utc)
                        }}
                    )
                    
                    # Write audit log
                    audit_id = f"aud_{uuid.uuid4().hex[:8]}"
                    audit_log = AuditLog(
                        log_id=audit_id,
                        actor="webhook",
                        action="RECOVERY_WEBHOOK_PROCESSED_SUCCESS",
                        entity_type="recovery_case",
                        entity_id=case_id,
                        details={
                            "event_id": event_id,
                            "action_id": action_id,
                            "payment_id": rzp_payment_id,
                            "amount": rzp_amount
                        },
                        timestamp=datetime.now(timezone.utc)
                    )
                    await db[AUDIT_LOGS_COLLECTION].insert_one(audit_log.model_dump())
                    logger.info(f"Webhook processing: case '{case_id}' successfully recovered.")
                    
                elif rzp_status == "failed":
                    # Update action status to FAILED
                    await db[RECOVERY_ACTIONS_COLLECTION].update_one(
                        {"action_id": action_id},
                        {"$set": {
                            "status": RecoveryActionStatus.FAILED,
                            "reason": payment_data.get("error_description", "Payment attempt failed on gateway."),
                            "updated_at": datetime.now(timezone.utc)
                        }}
                    )
                    
                    # Reset case status to PENDING so it can be re-evaluated
                    await db[RECOVERY_CASES_COLLECTION].update_one(
                        {"case_id": case_id},
                        {"$set": {
                            "status": "PENDING",
                            "updated_at": datetime.now(timezone.utc)
                        }}
                    )
                    
                    # Write audit log
                    audit_id = f"aud_{uuid.uuid4().hex[:8]}"
                    audit_log = AuditLog(
                        log_id=audit_id,
                        actor="webhook",
                        action="RECOVERY_WEBHOOK_PROCESSED_FAILURE",
                        entity_type="recovery_case",
                        entity_id=case_id,
                        details={
                            "event_id": event_id,
                            "action_id": action_id,
                            "reason": payment_data.get("error_description", "Payment attempt failed.")
                        },
                        timestamp=datetime.now(timezone.utc)
                    )
                    await db[AUDIT_LOGS_COLLECTION].insert_one(audit_log.model_dump())
                    logger.info(f"Webhook processing: recovery attempt failed for case '{case_id}'.")
                    
        # Update Webhook processing status to PROCESSED
        await db[WEBHOOK_EVENTS_COLLECTION].update_one(
            {"event_id": event_id},
            {"$set": {
                "processing_status": "PROCESSED",
                "processed_at": datetime.now(timezone.utc)
            }}
        )
        return {"status": "ok", "message": "Webhook processed successfully."}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        await db[WEBHOOK_EVENTS_COLLECTION].update_one(
            {"event_id": event_id},
            {"$set": {"processing_status": "FAILED"}}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed internally."
        )
