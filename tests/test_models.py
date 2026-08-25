from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.models.payment import Payment
from app.models.recovery import RecoveryCase
from app.models.agent_decision import AgentDecision, RecoveryAction
from app.guardrails.policy_engine import PolicyEngine, PolicyDecision, MaxAmountRule, MinConfidenceRule


def test_payment_model_valid():
    """Verify standard valid Payment instantiation with minor unit (paise) checks."""
    payment = Payment(
        payment_id="pay_test_123",
        order_id="order_test_123",
        amount=250000,  # ₹2,500
        currency="inr",  # Should convert to uppercase via validator
        status="failed",
        failure_reason="insufficient_funds",
        customer_id="cust_test_1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    assert payment.payment_id == "pay_test_123"
    assert payment.amount == 250000
    assert payment.currency == "INR"  # Uppercase validation check


def test_payment_model_invalid_amount():
    """Verify validation fails if amount is negative or invalid."""
    with pytest.raises(ValidationError):
        Payment(
            payment_id="pay_test_123",
            amount=-50,  # Invalid negative amount
            status="failed"
        )


def test_recovery_case_model():
    """Verify RecoveryCase instantiation and default values."""
    case = RecoveryCase(
        case_id="case_test_123",
        payment_id="pay_test_123",
        amount_at_risk=250000
    )
    assert case.case_id == "case_test_123"
    assert case.risk_status == "at_risk"  # Default value
    assert case.guardrail_status == "pending"  # Default value
    assert case.final_status == "open"  # Default value


def test_agent_decision_model():
    """Verify AgentDecision and action choices."""
    decision = AgentDecision(
        action=RecoveryAction.RETRY,
        confidence=0.85,
        reason="Gateway timeout is transient.",
        risk_factors=["network_instability"]
    )
    assert decision.action == "RETRY"
    assert decision.confidence == 0.85


def test_agent_decision_model_invalid_confidence():
    """Verify AgentDecision bounds check on confidence."""
    with pytest.raises(ValidationError):
        AgentDecision(
            action=RecoveryAction.RETRY,
            confidence=1.2,  # Invalid confidence (> 1.0)
            reason="Invalid"
        )


def test_policy_engine_allow():
    """Verify that a standard transaction passes guardrail checks."""
    payment = Payment(
        payment_id="pay_1",
        amount=50000,  # ₹500
        currency="INR",
        status="failed"
    )
    decision = AgentDecision(
        action=RecoveryAction.RETRY,
        confidence=0.9,
        reason="Looks safe"
    )
    
    engine = PolicyEngine()
    response = engine.evaluate(payment, decision)
    
    assert response.decision == PolicyDecision.ALLOW
    assert len(response.triggered_rules) == 0


def test_policy_engine_max_amount_escalate():
    """Verify that high-amount transactions are escalated to humans."""
    payment = Payment(
        payment_id="pay_large",
        amount=15000000,  # ₹1,50,000 (exceeds ₹1,00,000 limit)
        currency="INR",
        status="failed"
    )
    decision = AgentDecision(
        action=RecoveryAction.RETRY,
        confidence=0.9,
        reason="Looks safe"
    )
    
    engine = PolicyEngine()
    response = engine.evaluate(payment, decision)
    
    assert response.decision == PolicyDecision.ESCALATE
    assert "MAX_AMOUNT_LIMIT" in response.triggered_rules


def test_policy_engine_low_confidence_block():
    """Verify that low confidence recommendations are blocked."""
    payment = Payment(
        payment_id="pay_1",
        amount=50000,
        currency="INR",
        status="failed"
    )
    decision = AgentDecision(
        action=RecoveryAction.RETRY,
        confidence=0.4,  # Below default 0.6 limit
        reason="Unsure"
    )
    
    engine = PolicyEngine()
    response = engine.evaluate(payment, decision)
    
    assert response.decision == PolicyDecision.BLOCK
    assert "MIN_CONFIDENCE_THRESHOLD" in response.triggered_rules
