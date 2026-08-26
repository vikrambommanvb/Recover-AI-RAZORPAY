import asyncio
import os
import sys
import random
from motor.motor_asyncio import AsyncIOMotorClient

# Add root folder to python path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.collections import PAYMENTS_COLLECTION, RECOVERY_CASES_COLLECTION
from app.services.payment_service import PaymentService
from app.services.risk_service import RiskService
from app.services.ai_service import MockAIProvider
from app.ai.schemas import AIServiceRequest
from app.guardrails.policy_engine import (
    PolicyEngine,
    MaxAmountRule,
    MinConfidenceRule,
    PaymentStatusRule,
    RetryLimitRule,
    EscalationRule,
    PolicyDecision
)


def format_rupees(paise: int) -> str:
    """Format minor unit paise value to human-readable Indian Rupee (₹) format."""
    rupees = paise // 100
    s = str(rupees)
    if len(s) <= 3:
        return f"₹{s}"
    
    last_three = s[-3:]
    remaining = s[:-3]
    
    groups = []
    while remaining:
        if len(remaining) >= 2:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        else:
            groups.append(remaining)
            remaining = ""
            
    groups.reverse()
    formatted = ",".join(groups) + "," + last_three
    return f"₹{formatted}"


async def evaluate_batch():
    if not settings.MONGODB_URI:
        print("Error: MONGODB_URI environment variable is missing.")
        sys.exit(1)

    print("Connecting to MongoDB...")
    client_kwargs = {}
    try:
        import certifi
        client_kwargs["tlsCAFile"] = certifi.where()
    except ImportError:
        client_kwargs["tlsAllowInvalidCertificates"] = True

    client = None
    payments = []
    use_in_memory_fallback = False

    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=3000, **client_kwargs)
        db = client[settings.MONGODB_DATABASE]
        # Fetch payments
        cursor = db[PAYMENTS_COLLECTION].find()
        async for doc in cursor:
            payments.append(doc)
            
        if not payments:
            print("No payments found in MongoDB database. Using in-memory synthetic generation.")
            use_in_memory_fallback = True
    except Exception as e:
        print(f"MongoDB connection/read failed: {e}")
        print("Falling back to generating 500+ synthetic payments in-memory for evaluation...")
        use_in_memory_fallback = True

    if use_in_memory_fallback:
        # Generate 500+ synthetic payments in-memory
        import random
        random.seed(42)
        failure_reasons = [
            "Bank timeout during network handshake",
            "Insufficient funds in account",
            "Card expired or invalid",
            "Stolen card / suspected fraud",
            "Unknown card error"
        ]
        statuses = ["failed"] * 85 + ["captured"] * 12 + ["unknown"] * 3
        
        for i in range(500):
            status = random.choice(statuses)
            amount = random.randint(10000, 800000)  # ₹100 to ₹8,000
            reason = random.choice(failure_reasons) if status == "failed" else None
            
            payments.append({
                "payment_id": f"pay_syn_{i:03d}",
                "amount": amount,
                "currency": "INR",
                "status": status,
                "failure_reason": reason,
                "customer_id": f"cust_{random.randint(1, 50)}",
                "metadata": {"is_synthetic": True, "retry_count": 0}
            })

    total_payments = len(payments)


    print(f"Loaded {len(payments)} payments. Running risk analysis & recovery evaluation...")

    # Metrics
    total_cases = 0
    eligible_cases = 0
    ai_recommendations = 0
    policy_allowed = 0
    recovery_attempted = 0
    successful_recoveries = 0
    failed_recoveries = 0
    blocked_actions = 0
    escalated_cases = 0
    
    revenue_at_risk = 0
    revenue_recovered = 0

    ai_provider = MockAIProvider()
    
    # Initialize PolicyEngine with Phase 4 standard rules
    rules = [
        MaxAmountRule(max_amount_paise=settings.MAX_RECOVERY_AMOUNT_MINOR),
        MinConfidenceRule(min_confidence=0.60, action=PolicyDecision.ESCALATE),
        PaymentStatusRule(),
        RetryLimitRule(max_retries=settings.MAX_RECOVERY_ATTEMPTS),
        EscalationRule()
    ]
    policy_engine = PolicyEngine(rules=rules)

    # Use a fixed seed for reproducible simulation outcomes
    random.seed(42)

    for payment_doc in payments:
        total_cases += 1
        
        # 1. Classify payment risk
        payment_id = payment_doc["payment_id"]
        status = payment_doc.get("status", "").lower()
        amount = payment_doc.get("amount", 0)
        currency = payment_doc.get("currency", "INR")
        failure_reason = payment_doc.get("failure_reason") or ""
        customer_id = payment_doc.get("customer_id")
        metadata = payment_doc.get("metadata") or {}
        
        # Determine risk status (Risk Engine)
        # Re-use classification logic
        from app.models.payment import Payment
        payment_obj = Payment(**payment_doc)
        risk_status, root_cause, amount_at_risk = RiskService.classify_payment(payment_obj)
        
        is_eligible = risk_status in ["AT_RISK", "UNKNOWN"]
        if not is_eligible:
            continue
            
        eligible_cases += 1
        revenue_at_risk += amount_at_risk

        # 2. Query AI Recommendation
        ai_request = AIServiceRequest(
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            failure_reason=failure_reason,
            customer_id=customer_id or "",
            metadata=metadata
        )
        
        # AI decision call
        try:
            recommendation = await ai_provider.analyze_payment_failure(ai_request)
        except Exception:
            # Fallback
            from app.models.agent_decision import RecoveryAction
            from app.ai.schemas import AIServiceResponse
            recommendation = AIServiceResponse(
                action=RecoveryAction.ESCALATE,
                confidence=1.0,
                reason="AI Failure simulation",
                root_cause="UNKNOWN",
                risk_factors=[]
            )

        if recommendation.action != "NO_ACTION":
            ai_recommendations += 1

        # 3. Policy Engine Guard
        from app.models.agent_decision import AgentDecision
        agent_decision = AgentDecision(
            action=recommendation.action,
            confidence=recommendation.confidence,
            reason=recommendation.reason,
            risk_factors=recommendation.risk_factors
        )
        
        # Inject fake retry count of 0 for clean simulation
        payment_obj.metadata = payment_obj.metadata or {}
        payment_obj.metadata["retry_count"] = 0
        
        policy_response = policy_engine.evaluate(payment_obj, agent_decision)

        if policy_response.decision == PolicyDecision.ALLOW:
            policy_allowed += 1
            
            # 4. Executor checks (excluding Policy Engine)
            # Amount limit check
            if amount > settings.MAX_RECOVERY_AMOUNT_MINOR:
                blocked_actions += 1
            else:
                # Execution attempt
                recovery_attempted += 1
                
                # Dynamic simulation based on root cause & failure reason
                reason_lower = failure_reason.lower()
                success_prob = 0.10  # default
                
                if "timeout" in reason_lower or "network" in reason_lower:
                    # Transient failures recover very well
                    success_prob = 0.70
                elif "balance" in reason_lower or "insufficient" in reason_lower:
                    # Balance reminder recovery is moderate
                    success_prob = 0.40
                    
                # Simulate outcome
                if random.random() < success_prob:
                    successful_recoveries += 1
                    revenue_recovered += amount
                else:
                    failed_recoveries += 1

        elif policy_response.decision == PolicyDecision.BLOCK:
            blocked_actions += 1
        elif policy_response.decision == PolicyDecision.ESCALATE:
            escalated_cases += 1

    recovery_rate = (successful_recoveries / eligible_cases) if eligible_cases > 0 else 0.0

    print("\n==================================================")
    print(" RecoverAI - Revenue Recovery Batch Evaluation")
    print("==================================================")
    print(f"Data Source Label:        SYNTHETIC")
    print(f"Cases Analyzed:           {total_cases}")
    print(f"Eligible Cases (At Risk): {eligible_cases}")
    print(f"AI Recommendations:       {ai_recommendations}")
    print(f"Policy Allowed:           {policy_allowed}")
    print(f"Recovery Attempted:       {recovery_attempted}")
    print(f"Successful Recoveries:    {successful_recoveries}")
    print(f"Failed Recoveries:        {failed_recoveries}")
    print(f"Blocked Actions:          {blocked_actions}")
    print(f"Escalated Cases:          {escalated_cases}")
    print("--------------------------------------------------")
    print(f"Revenue At Risk:          {format_rupees(revenue_at_risk)}")
    print(f"Revenue Recovered:        {format_rupees(revenue_recovered)}")
    print(f"Recovery Rate:            {recovery_rate * 100:.2f}%")
    print("==================================================")

    if client:
        client.close()

if __name__ == "__main__":
    asyncio.run(evaluate_batch())
