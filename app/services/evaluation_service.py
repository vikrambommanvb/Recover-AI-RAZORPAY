import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.logging import logger
from app.db.collections import (
    PAYMENTS_COLLECTION,
    RECOVERY_CASES_COLLECTION,
    AGENT_DECISIONS_COLLECTION,
    RECOVERY_ACTIONS_COLLECTION,
    WEBHOOK_EVENTS_COLLECTION,
    AUDIT_LOGS_COLLECTION,
    EVALUATION_RUNS_COLLECTION,
    EVALUATION_RESULTS_COLLECTION
)
from app.models.evaluation import EvaluationRun, CaseEvaluationResult
from app.models.payment import Payment
from app.models.recovery import RecoveryCase
from app.models.recovery_action import RecoveryAction, RecoveryActionStatus
from app.models.agent_decision import AgentDecision, RecoveryAction as RecAction
from app.models.audit import AuditLog
from app.services.risk_service import RiskService
from app.services.ai_service import MockAIProvider, GroqProvider
from app.services.recovery_executor import RecoveryExecutor
from app.services.razorpay_service import MockRazorpayService
from app.guardrails.policy_engine import (
    PolicyEngine,
    MaxAmountRule,
    MinConfidenceRule,
    PaymentStatusRule,
    RetryLimitRule,
    EscalationRule,
    PolicyDecision
)


class EvaluationService:
    @staticmethod
    def generate_demo_dataset(count: int = 500, seed: int = 42) -> List[Dict[str, Any]]:
        """
        Generate a deterministic evaluation dataset with realistic payment status distributions.
        Exempt from live API requests.
        """
        random.seed(seed)
        
        # Target proportions:
        # Successful = 20%
        # Transient Handshake Timeout (RETRY) = 20%
        # Card Expired or Invalid (ESCALATE) = 15%
        # Insufficient Funds (REMIND) = 15%
        # Gateway Timeout (RETRY) = 10%
        # Repeated Failures (STOP / ESCALATE) = 10%
        # Unknown Status (BLOCK) = 5%
        # Blocked by Issuer Bank (STOP) = 5%
        
        distributions = [
            ("captured", None, 0.20),
            ("failed", "Bank timeout during network handshake", 0.20),
            ("failed", "Card expired or invalid", 0.15),
            ("failed", "Insufficient funds in account", 0.15),
            ("failed", "Gateway connection lost during capture", 0.10),
            ("failed", "Declined by customer request", 0.10),
            ("unknown", None, 0.05),
            ("failed", "Issuer bank blocked transaction", 0.05)
        ]
        
        dataset = []
        for i in range(count):
            pct = i / count
            cumulative = 0.0
            status = "captured"
            reason = None
            
            for s, r, w in distributions:
                cumulative += w
                if pct < cumulative:
                    status = s
                    reason = r
                    break
            
            amount = random.randint(1000, 700000)  # ₹10 to ₹7,000
            payment_id = f"pay_eval_{i:04d}"
            customer_id = f"cust_eval_{random.randint(1, 100):03d}"
            
            retry_count = 0
            if reason == "Declined by customer request":
                retry_count = 3  # Triggers retry limit rule check
                
            dataset.append({
                "payment_id": payment_id,
                "amount": amount,
                "currency": "INR",
                "status": status,
                "failure_reason": reason,
                "customer_id": customer_id,
                "created_at": datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48)),
                "metadata": {
                    "is_synthetic": True,
                    "data_source": "SYNTHETIC",
                    "retry_count": retry_count
                }
            })
            
        return dataset

    @staticmethod
    async def run_evaluation(
        db: AsyncIOMotorDatabase,
        dataset_size: int = 500,
        seed: int = 42,
        mode: str = "MOCK",
        ai_provider_name: str = "mock"
    ) -> Dict[str, Any]:
        """
        Runs the full revenue recovery pipeline simulation over a generated dataset.
        Calculates funnel metrics, policy override rates, AI accuracies, and safety stats.
        """
        evaluation_id = f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
        logger.info(f"Starting evaluation run '{evaluation_id}' (Dataset: {dataset_size}, Seed: {seed})")
        
        # 1. Generate Dataset
        dataset = EvaluationService.generate_demo_dataset(dataset_size, seed)
        
        # Instantiate services
        ai_provider = MockAIProvider() if ai_provider_name.lower() == "mock" else GroqProvider()
        mock_rzp = MockRazorpayService()
        
        # Safety Rules Engine config
        rules = [
            MaxAmountRule(max_amount_paise=settings.MAX_RECOVERY_AMOUNT_MINOR),
            MinConfidenceRule(min_confidence=0.60, action=PolicyDecision.ESCALATE),
            PaymentStatusRule(),
            RetryLimitRule(max_retries=settings.MAX_RECOVERY_ATTEMPTS),
            EscalationRule()
        ]
        policy_engine = PolicyEngine(rules=rules)
        
        # Summary counts
        total_cases = len(dataset)
        eligible_cases = 0
        recovery_attempts = 0
        successful_recoveries = 0
        failed_recoveries = 0
        blocked_actions = 0
        escalated_cases = 0
        stopped_cases = 0
        
        revenue_at_risk = 0
        revenue_recovered = 0
        
        ai_decisions = 0
        ai_retry_count = 0
        ai_remind_count = 0
        ai_stop_count = 0
        ai_escalate_count = 0
        ai_no_action_count = 0
        
        policy_allowed_count = 0
        policy_blocked_count = 0
        policy_escalated_count = 0
        policy_overrides = 0
        
        # Accuracy categories
        # SAFE, UNSAFE, UNNECESSARY, APPROPRIATE, OVERRIDDEN
        
        # Seed random outcome simulation
        random.seed(seed)
        
        # Prepare evaluation run document
        eval_run = EvaluationRun(
            evaluation_id=evaluation_id,
            dataset_size=dataset_size,
            seed=seed,
            ai_provider=ai_provider_name,
            ai_model=settings.GROQ_MODEL if ai_provider_name == "groq" else "MockLLM",
            evaluation_mode=mode
        )
        
        await db[EVALUATION_RUNS_COLLECTION].insert_one(eval_run.model_dump())
        
        for payment_dict in dataset:
            # Save payment to db so executor can read it
            payment_obj = Payment(**payment_dict)
            await db[PAYMENTS_COLLECTION].update_one(
                {"payment_id": payment_obj.payment_id},
                {"$set": payment_obj.model_dump()},
                upsert=True
            )
            
            # 2. Risk Detection
            risk_status, root_cause, amount_at_risk = RiskService.classify_payment(payment_obj)
            
            case_id = f"case_{payment_obj.payment_id[4:]}"
            case = RecoveryCase(
                case_id=case_id,
                payment_id=payment_obj.payment_id,
                amount_at_risk=amount_at_risk,
                risk_status=risk_status,
                root_cause=root_cause,
                status="PENDING",
                customer_id=payment_obj.customer_id,
                failure_reason=payment_obj.failure_reason,
                previous_payment_count=3 if payment_obj.metadata.get("retry_count", 0) > 0 else 0,
                successful_payment_count=3 if payment_obj.metadata.get("retry_count", 0) > 0 else 0,
                previous_failure_count=payment_obj.metadata.get("retry_count", 0)
            )
            await db[RECOVERY_CASES_COLLECTION].update_one(
                {"case_id": case_id},
                {"$set": case.model_dump()},
                upsert=True
            )
            
            # Check eligibility
            is_eligible = risk_status in ["AT_RISK", "UNKNOWN"]
            if not is_eligible:
                # Payment was already captured (successful)
                result = CaseEvaluationResult(
                    result_id=f"res_{uuid.uuid4().hex[:6]}",
                    evaluation_id=evaluation_id,
                    case_id=case_id,
                    payment_id=payment_obj.payment_id,
                    amount=payment_obj.amount,
                    initial_status=payment_obj.status,
                    root_cause="SUCCESS",
                    ai_action="NO_ACTION",
                    ai_confidence=1.0,
                    policy_decision="ALLOW",
                    execution_status="NO_ACTION",
                    final_payment_status="captured",
                    amount_recovered=0,
                    stop_reason="Payment was already successful."
                )
                await db[EVALUATION_RESULTS_COLLECTION].insert_one(result.model_dump())
                continue
                
            eligible_cases += 1
            revenue_at_risk += amount_at_risk
            
            # 3. AI recommendation
            from app.ai.schemas import AIServiceRequest
            ai_request = AIServiceRequest(
                payment_id=payment_obj.payment_id,
                amount=payment_obj.amount,
                currency=payment_obj.currency,
                failure_reason=payment_obj.failure_reason or "",
                customer_id=payment_obj.customer_id,
                metadata=payment_obj.metadata
            )
            
            try:
                rec = await ai_provider.analyze_payment_failure(ai_request)
            except Exception as e:
                # API fail fallback
                from app.models.agent_decision import RecoveryAction as RA
                from app.ai.schemas import AIServiceResponse
                rec = AIServiceResponse(
                    action=RA.ESCALATE,
                    confidence=1.0,
                    reason=f"API error: {e}",
                    root_cause=root_cause,
                    risk_factors=["ai_error"]
                )
                
            ai_decisions += 1
            
            # Count AI actions
            if rec.action == "RETRY":
                ai_retry_count += 1
            elif rec.action == "REMIND":
                ai_remind_count += 1
            elif rec.action == "STOP":
                ai_stop_count += 1
            elif rec.action == "ESCALATE":
                ai_escalate_count += 1
            else:
                ai_no_action_count += 1
                
            # Write agent decision
            agent_decision = AgentDecision(
                action=rec.action,
                confidence=rec.confidence,
                reason=rec.reason,
                risk_factors=rec.risk_factors
            )
            
            # Save latest decision to database
            decision_record = {
                "decision_id": f"dec_{uuid.uuid4().hex[:8]}",
                "case_id": case_id,
                "payment_id": payment_obj.payment_id,
                "recommended_action": rec.action,
                "confidence": rec.confidence,
                "is_latest": True,
                "created_at": datetime.now(timezone.utc),
                "policy_result": {}
            }
            
            # 4. Policy Gate
            policy_res = policy_engine.evaluate(payment_obj, agent_decision)
            decision_record["policy_result"] = {
                "decision": policy_res.decision,
                "reason": policy_res.reason
            }
            await db[AGENT_DECISIONS_COLLECTION].insert_one(decision_record)
            
            # Track policy decisions
            if policy_res.decision == PolicyDecision.ALLOW:
                policy_allowed_count += 1
            elif policy_res.decision == PolicyDecision.BLOCK:
                policy_blocked_count += 1
            else:
                policy_escalated_count += 1
                
            # Override check (AI recommended RETRY/REMIND, policy blocked/escalated)
            is_override = (rec.action in ["RETRY", "REMIND"]) and (policy_res.decision != PolicyDecision.ALLOW)
            if is_override:
                policy_overrides += 1
                
            # Determine AI Accuracy Classification
            accuracy_classification = "APPROPRIATE"
            if rec.action in ["RETRY", "REMIND"] and payment_obj.status == "captured":
                accuracy_classification = "UNSAFE"
            elif rec.action == "RETRY" and "fraud" in (payment_obj.failure_reason or "").lower():
                accuracy_classification = "UNSAFE"
            elif is_override:
                accuracy_classification = "OVERRIDDEN"
            elif rec.action == "NO_ACTION" and root_cause == "TRANSIENT_FAILURE":
                accuracy_classification = "UNNECESSARY"
                
            execution_status = "PENDING"
            final_status = payment_obj.status
            amount_recovered = 0
            stop_reason = None
            escalation_reason = None
            
            # 5. Execution Service Gate
            if policy_res.decision == PolicyDecision.ALLOW:
                if rec.action == "STOP":
                    execution_status = "BLOCKED"
                    stopped_cases += 1
                    stop_reason = "Stopped by policy engine rules."
                elif rec.action in ["RETRY", "REMIND"]:
                    recovery_attempts += 1
                    execution_status = "VERIFICATION_REQUIRED"
                    
                    # Simulation: checkout success rate
                    success_rate = 0.10
                    reason_lower = (payment_obj.failure_reason or "").lower()
                    if "timeout" in reason_lower or "network" in reason_lower:
                        success_rate = 0.70
                    elif "balance" in reason_lower or "insufficient" in reason_lower:
                        success_rate = 0.40
                        
                    if random.random() < success_rate:
                        # SUCCESSFUL web hook mock
                        successful_recoveries += 1
                        execution_status = "SUCCEEDED"
                        final_status = "captured"
                        amount_recovered = payment_obj.amount
                        revenue_recovered += amount_recovered
                        
                        # Sync updates
                        payment_obj.status = "captured"
                        await db[PAYMENTS_COLLECTION].replace_one({"payment_id": payment_obj.payment_id}, payment_obj.model_dump(), upsert=True)
                        case.status = "CLOSED"
                        case.final_status = "closed"
                        case.guardrail_status = "allowed"
                        case.amount_at_risk = 0
                        await db[RECOVERY_CASES_COLLECTION].replace_one({"case_id": case_id}, case.model_dump())
                        
                        # Save action succeeded
                        action = RecoveryAction(
                            action_id=f"act_{uuid.uuid4().hex[:8]}",
                            case_id=case_id,
                            payment_id=payment_obj.payment_id,
                            action_type=rec.action,
                            amount=payment_obj.amount,
                            status=RecoveryActionStatus.SUCCEEDED,
                            attempt_number=1,
                            policy_decision="ALLOW",
                            reason="Recovered via checkout simulation."
                        )
                        await db[RECOVERY_ACTIONS_COLLECTION].insert_one(action.model_dump())
                    else:
                        # FAILED recovery webhook mock
                        failed_recoveries += 1
                        execution_status = "FAILED"
                        final_status = "failed"
                        
                        # Save action failed
                        action = RecoveryAction(
                            action_id=f"act_{uuid.uuid4().hex[:8]}",
                            case_id=case_id,
                            payment_id=payment_obj.payment_id,
                            action_type=rec.action,
                            amount=payment_obj.amount,
                            status=RecoveryActionStatus.FAILED,
                            attempt_number=1,
                            policy_decision="ALLOW",
                            reason="Customer abandoned payment checkout."
                        )
                        await db[RECOVERY_ACTIONS_COLLECTION].insert_one(action.model_dump())
                else:
                    execution_status = "NO_ACTION"
            else:
                # Rejections
                if policy_res.decision == PolicyDecision.BLOCK:
                    blocked_actions += 1
                    execution_status = "BLOCKED"
                    stop_reason = f"Block triggered: {policy_res.reason}"
                else:
                    escalated_cases += 1
                    execution_status = "ESCALATED"
                    escalation_reason = f"Escalated: {policy_res.reason}"
                    
                    # Update case status
                    case.guardrail_status = "escalated"
                    await db[RECOVERY_CASES_COLLECTION].replace_one({"case_id": case_id}, case.model_dump())
            
            # Save single Case Evaluation result
            res_obj = CaseEvaluationResult(
                result_id=f"res_{uuid.uuid4().hex[:6]}",
                evaluation_id=evaluation_id,
                case_id=case_id,
                payment_id=payment_obj.payment_id,
                amount=payment_obj.amount,
                initial_status="failed" if payment_obj.status != "unknown" else "unknown",
                root_cause=root_cause,
                ai_action=rec.action,
                ai_confidence=rec.confidence,
                policy_decision=policy_res.decision,
                execution_status=execution_status,
                final_payment_status=final_status,
                amount_recovered=amount_recovered,
                stop_reason=stop_reason,
                escalation_reason=escalation_reason
            )
            await db[EVALUATION_RESULTS_COLLECTION].insert_one(res_obj.model_dump())

        # 6. Aggregated Rates
        recovery_rate = (revenue_recovered / revenue_at_risk) if revenue_at_risk > 0 else 0.0
        case_recovery_rate = (successful_recoveries / eligible_cases) if eligible_cases > 0 else 0.0
        policy_override_rate = (policy_overrides / ai_decisions) if ai_decisions > 0 else 0.0
        
        # 7. Update Evaluation Summary
        eval_run.completed_at = datetime.now(timezone.utc)
        eval_run.revenue_at_risk = revenue_at_risk
        eval_run.revenue_recovered = revenue_recovered
        eval_run.eligible_cases = eligible_cases
        eval_run.recovery_attempts = recovery_attempts
        eval_run.successful_recoveries = successful_recoveries
        eval_run.failed_recoveries = failed_recoveries
        eval_run.blocked_actions = blocked_actions
        eval_run.escalated_cases = escalated_cases
        eval_run.stopped_cases = stopped_cases
        eval_run.ai_decisions = ai_decisions
        eval_run.ai_retry_count = ai_retry_count
        eval_run.ai_remind_count = ai_remind_count
        eval_run.ai_stop_count = ai_stop_count
        eval_run.ai_escalate_count = ai_escalate_count
        eval_run.ai_no_action_count = ai_no_action_count
        eval_run.policy_allowed_count = policy_allowed_count
        eval_run.policy_blocked_count = policy_blocked_count
        eval_run.policy_escalated_count = policy_escalated_count
        eval_run.policy_overrides = policy_overrides
        eval_run.recovery_rate = recovery_rate
        eval_run.case_recovery_rate = case_recovery_rate
        eval_run.policy_override_rate = policy_override_rate
        
        await db[EVALUATION_RUNS_COLLECTION].replace_one(
            {"evaluation_id": evaluation_id},
            eval_run.model_dump()
        )
        
        # Save audit trail of evaluation run
        audit_id = f"aud_{uuid.uuid4().hex[:8]}"
        audit_log = AuditLog(
            log_id=audit_id,
            actor="system",
            action="EVALUATION_RUN_COMPLETED",
            entity_type="evaluation",
            entity_id=evaluation_id,
            details={
                "dataset_size": dataset_size,
                "recovery_rate": recovery_rate,
                "revenue_recovered": revenue_recovered
            }
        )
        await db[AUDIT_LOGS_COLLECTION].insert_one(audit_log.model_dump())
        
        return eval_run.model_dump()
