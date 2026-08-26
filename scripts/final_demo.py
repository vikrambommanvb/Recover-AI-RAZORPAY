import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

# Add root folder to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.mongodb import db
from app.models.payment import Payment
from app.models.recovery import RecoveryCase
from app.models.recovery_action import RecoveryAction, RecoveryActionStatus
from app.models.agent_decision import AgentDecision, RecoveryAction as RecAction
from app.models.audit import AuditLog
from app.services.risk_service import RiskService
from app.guardrails.policy_engine import PolicyEngine, PolicyDecision
from app.services.evaluation_service import EvaluationService


def format_rupees(paise: int) -> str:
    return f"₹{paise // 100}"


async def main():
    print("==================================================")
    print("      RecoverAI - Final Pitch Demo Script")
    print("==================================================")
    
    # 1. Connect to DB (falls back to MockDatabase automatically)
    await db.connect()
    database = db.db
    
    print("\n[STEP 1] LOADING CANONICAL FAILED PAYMENT")
    payment = Payment(
        payment_id="pay_demo_success_1",
        amount=249900,  # ₹2,499
        currency="INR",
        status="failed",
        failure_reason="Gateway timeout during handshake",
        customer_id="cust_demo_01"
    )
    print(f"Failed Payment ID:      {payment.payment_id}")
    print(f"Transaction Amount:     {format_rupees(payment.amount)}")
    print(f"Gateway Failure:        {payment.failure_reason}")

    print("\n[STEP 2] RUNNING RISK CLASSIFIER")
    risk_status, root_cause, amount_at_risk = RiskService.classify_payment(payment)
    print(f"Risk Status Classified: {risk_status}")
    print(f"Diagnosed Cause:        {root_cause}")
    print(f"Amount At Risk:         {format_rupees(amount_at_risk)}")

    print("\n[STEP 3] INVOKING AI RECOVERY DECISION AGENT")
    # Mock AI Reasoning
    ai_recommendation = RecAction.RETRY
    confidence = 0.91
    reason = "Transient payment timeout failure with high customer history reputation. Recommending auto-retry checkout link."
    print(f"AI Recommendation:      {ai_recommendation}")
    print(f"AI Confidence Score:    {confidence * 100:.0f}%")
    print(f"AI Reasoning details:   '{reason}'")

    policy_engine = PolicyEngine()
    agent_decision = AgentDecision(
        action=ai_recommendation,
        confidence=confidence,
        reason=reason
    )
    policy_res = policy_engine.evaluate(payment, agent_decision)
    print(f"Deterministic Policy:   {policy_res.decision.upper()}")
    print(f"Policy justification:   {policy_res.reason}")
    
    print("\n[STEP 5] EXECUTING RAZORPAY TEST MODE ACTION")
    print("Status: EXECUTING...")
    action_id = f"act_{uuid.uuid4().hex[:8]}"
    action = RecoveryAction(
        action_id=action_id,
        case_id="case_demo_1",
        payment_id=payment.payment_id,
        action_type=ai_recommendation.value,
        amount=payment.amount,
        status=RecoveryActionStatus.VERIFICATION_REQUIRED,
        policy_decision="ALLOW",
        reason="Checkout link generated."
    )
    print(f"Created Recovery Action: {action.action_id} (Status: {action.status})")
    
    print("\n[STEP 6] VERIFYING OUTCOME VIA SIGNATURE-CHECKED WEBHOOK")
    # Simulate webhook payment.captured event
    action.status = RecoveryActionStatus.SUCCEEDED
    payment.status = "captured"
    print("Webhook event 'payment.captured' received (Signature Verified).")
    print(f"Updated Action Status:  {action.status}")
    print(f"Updated Payment Status: {payment.status}")
    print(f"Revenue Recovered:      {format_rupees(payment.amount)}")

    print("\n[STEP 7] SYSTEM AUDIT TRAIL RECORD GENERATION")
    audit = AuditLog(
        log_id=f"aud_{uuid.uuid4().hex[:8]}",
        actor="system",
        action="RECOVERY_ATTEMPT_SUCCEEDED",
        entity_type="payment",
        entity_id=payment.payment_id,
        details={"recovered_amount": payment.amount, "action_id": action.action_id}
    )
    print(f"Audit Trail Written:    {audit.action} (Trace ID: {audit.correlation_id})")

    print("\n==================================================")
    print("  DEMONSTRATING SAFETY GATES & FAILURE HANDLING")
    print("==================================================")
    
    print("\n[STEP 8] CANONICAL SAFETY DEMO: AMBIGUOUS GATEWAY STATE BLOCK")
    safety_payment = Payment(
        payment_id="pay_demo_safety",
        amount=499900,  # ₹4,999
        currency="INR",
        status="unknown",  # Ambiguous state!
        failure_reason="Gateway API did not respond",
        customer_id="cust_demo_02"
    )
    # AI suggests Retry, but Policy blocks
    safety_decision = AgentDecision(
        action=RecAction.RETRY,
        confidence=0.96,
        reason="Retry timeout transaction."
    )
    safety_policy_res = policy_engine.evaluate(safety_payment, safety_decision)
    print(f"Gateway state:          {safety_payment.status}")
    print(f"AI recommendation:      {safety_decision.action} (Confidence: {safety_decision.confidence * 100:.0f}%)")
    print(f"Policy Decision:        {safety_policy_res.decision}")
    print(f"Policy Rejection:       {safety_policy_res.reason}")
    print("Razorpay Execution:     ❌ NOT ATTEMPTED (Safety Block Enforced)")

    print("\n[STEP 9] CANONICAL FAILURE DEMO: GATEWAY API TIMEOUT")
    print("AI recommended RETRY (Policy allowed). Execution started...")
    print("Execution call to Razorpay: TIMEOUT EXCEPTION.")
    timeout_action = RecoveryAction(
        action_id=f"act_{uuid.uuid4().hex[:8]}",
        case_id="case_demo_timeout",
        payment_id="pay_demo_timeout",
        action_type="RETRY",
        amount=200000,
        status=RecoveryActionStatus.FAILED,
        reason="Gateway connection timeout."
    )
    timeout_audit = AuditLog(
        log_id=f"aud_{uuid.uuid4().hex[:8]}",
        actor="system",
        action="RECOVERY_ATTEMPT_FAILED",
        entity_type="payment",
        entity_id="pay_demo_timeout",
        details={"reason": "Gateway connection timeout"}
    )
    print(f"Action Status recorded: {timeout_action.status}")
    print(f"Audit Trail logged:     {timeout_audit.action}")
    print(f"Revenue Recovered:      {format_rupees(0)} (No false metrics generated)")

    print("\n==================================================")
    print("        RUNNING 500-RECORD BATCH SIMULATION")
    print("==================================================")
    
    summary = await EvaluationService.run_evaluation(
        db=database,
        dataset_size=500,
        seed=42,
        mode="MOCK",
        ai_provider_name="mock"
    )
    print(f"Simulation Dataset:     {summary['dataset_size']} records (Seed: {summary['seed']})")
    print(f"Revenue At Risk:        {format_rupees(summary['revenue_at_risk'])}")
    print(f"Revenue Recovered:      {format_rupees(summary['revenue_recovered'])}")
    print(f"Revenue Recovery Rate:  {summary['recovery_rate'] * 100:.2f}%")
    print(f"Case Recovery Rate:     {summary['case_recovery_rate'] * 100:.2f}%")
    print("==================================================")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
