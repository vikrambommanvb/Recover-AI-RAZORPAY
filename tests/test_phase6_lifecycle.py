import pytest
import json
import httpx
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_db
from app.core.config import settings
from app.db.mock_db import MockDatabase
from app.db.collections import (
    PAYMENTS_COLLECTION,
    RECOVERY_CASES_COLLECTION,
    AGENT_DECISIONS_COLLECTION,
    RECOVERY_ACTIONS_COLLECTION,
    AUDIT_LOGS_COLLECTION,
    WEBHOOK_EVENTS_COLLECTION
)
from app.models.payment import Payment
from app.models.recovery import RecoveryCase
from app.integrations.razorpay_client import NormalizedPayment
from app.services.payment_state_verifier import PaymentStateVerifier
from app.services.root_cause_classifier import RootCauseClassifier
from app.services.risk_service import RevenueRiskDetector
from app.guardrails.policy_engine import PolicyEngine, PolicyDecision, MinConfidenceRule
from app.models.agent_decision import AgentDecision, RecoveryAction as RecAction

# Setup mock database and mock Razorpay service
mock_db = MockDatabase()
from app.services.razorpay_service import MockRazorpayService
mock_rzp = MockRazorpayService()


@pytest.fixture(autouse=True)
def clean_mock_db():
    """Clear all mock database collections before each test and force mock mode."""
    # Force Mock AI Provider during tests to ensure offline execution
    old_provider = settings.AI_PROVIDER
    settings.AI_PROVIDER = "mock"
    
    # Save old overrides
    old_db_override = app.dependency_overrides.get(get_db)
    from app.api.dependencies import get_razorpay_client, get_razorpay_service
    old_rzp_override = app.dependency_overrides.get(get_razorpay_client)
    old_rzp_service_override = app.dependency_overrides.get(get_razorpay_service)
    
    # Set to local mock overrides
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_razorpay_client] = lambda: mock_rzp
    app.dependency_overrides[get_razorpay_service] = lambda: mock_rzp
    
    mock_db.collections.clear()
    
    yield
    
    # Restore old overrides
    if old_db_override is not None:
        app.dependency_overrides[get_db] = old_db_override
    else:
        app.dependency_overrides.pop(get_db, None)
        
    if old_rzp_override is not None:
        app.dependency_overrides[get_razorpay_client] = old_rzp_override
    else:
        app.dependency_overrides.pop(get_razorpay_client, None)
        
    if old_rzp_service_override is not None:
        app.dependency_overrides[get_razorpay_service] = old_rzp_service_override
    else:
        app.dependency_overrides.pop(get_razorpay_service, None)
        
    settings.AI_PROVIDER = old_provider


def test_payment_state_verifier():
    # 1. CAPTURED -> no recovery
    eligible, reason = PaymentStateVerifier.get_recovery_eligibility("captured")
    assert not eligible
    assert "captured" in reason.lower()

    # 2. FAILED -> eligible
    eligible, reason = PaymentStateVerifier.get_recovery_eligibility("failed")
    assert eligible
    assert "eligible" in reason.lower()

    # 3. PENDING -> no immediate recovery
    eligible, reason = PaymentStateVerifier.get_recovery_eligibility("pending")
    assert not eligible
    assert "pending" in reason.lower()

    # 4. REFUNDED -> no recovery
    eligible, reason = PaymentStateVerifier.get_recovery_eligibility("refunded")
    assert not eligible
    assert "refunded" in reason.lower()

    # 5. UNKNOWN -> block
    eligible, reason = PaymentStateVerifier.get_recovery_eligibility("unknown")
    assert not eligible
    assert "unknown" in reason.lower()


def test_root_cause_classifier():
    # temporary failure (checked first)
    assert RootCauseClassifier.classify("temporary gateway down error") == "TEMPORARY_PROVIDER_FAILURE"
    # network timeout
    assert RootCauseClassifier.classify("gateway timeout during authorization") == "NETWORK_TIMEOUT"
    # bank decline
    assert RootCauseClassifier.classify("issuer bank card expired decline") == "BANK_DECLINE"
    # low balance
    assert RootCauseClassifier.classify("insufficient credit limit") == "INSUFFICIENT_FUNDS"
    # auth failure
    assert RootCauseClassifier.classify("OTP verification failed") == "AUTHENTICATION_FAILURE"
    # unknown
    assert RootCauseClassifier.classify("unrecognized code 999") == "UNKNOWN"


def test_revenue_risk_detector():
    payment = NormalizedPayment(
        payment_id="pay_test_01",
        amount_minor=150000,
        currency="INR",
        status="failed",
        created_at=datetime.now(timezone.utc),
        captured=False,
        failure_reason="gateway connection timeout"
    )
    case = RevenueRiskDetector.detect_risk(payment, retry_count=0)
    assert case.eligibility is True
    assert case.risk_type == "PAYMENT_TIMEOUT"
    assert case.root_cause == "NETWORK_TIMEOUT"
    assert case.amount_minor == 150000


def test_policy_engine_missing_fields():
    engine = PolicyEngine()
    
    # 1. Missing payment ID
    bad_payment_1 = Payment.model_construct(
        payment_id="",
        amount=1000,
        currency="INR",
        status="failed"
    )
    decision = AgentDecision(action=RecAction.RETRY, confidence=0.9, reason="test")
    res = engine.evaluate(bad_payment_1, decision)
    assert res.decision == PolicyDecision.BLOCK

    # 2. Negative amount (using model_construct to bypass gt=0 validator)
    bad_payment_2 = Payment.model_construct(
        payment_id="pay_ok",
        amount=-50,
        currency="INR",
        status="failed"
    )
    res = engine.evaluate(bad_payment_2, decision)
    assert res.decision == PolicyDecision.BLOCK

    # 3. Already successful payment
    captured_payment = Payment.model_construct(
        payment_id="pay_ok",
        amount=1000,
        currency="INR",
        status="captured"
    )
    res = engine.evaluate(captured_payment, decision)
    assert res.decision == PolicyDecision.BLOCK


def test_policy_engine_low_confidence():
    engine = PolicyEngine(rules=[MinConfidenceRule(min_confidence=0.60, action=PolicyDecision.ESCALATE)])
    payment = Payment.model_construct(
        payment_id="pay_ok",
        amount=1000,
        currency="INR",
        status="failed"
    )
    # Low confidence should trigger ESCALATE
    decision = AgentDecision(action=RecAction.RETRY, confidence=0.3, reason="low conf")
    res = engine.evaluate(payment, decision)
    assert res.decision == PolicyDecision.ESCALATE


def test_policy_engine_retry_limit():
    engine = PolicyEngine()
    payment = Payment.model_construct(
        payment_id="pay_ok",
        amount=1000,
        currency="INR",
        status="failed",
        metadata={"retry_count": 3}
    )
    decision = AgentDecision(action=RecAction.RETRY, confidence=0.9, reason="retry")
    res = engine.evaluate(payment, decision)
    assert res.decision == PolicyDecision.BLOCK


def test_recovery_lifecycle_end_to_end(clean_mock_db):
    client = TestClient(app)
    
    # Pre-populate failed payment in DB
    payment_data = {
        "payment_id": "pay_fail_lifecycle",
        "amount": 250000,
        "currency": "INR",
        "status": "failed",
        "failure_reason": "network timeout from gateway",
        "customer_id": "cust_123",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "metadata": {}
    }
    mock_db[PAYMENTS_COLLECTION].docs.append(payment_data)

    # 1. Create Case
    res_case = client.post("/api/recovery/cases", json={"payment_id": "pay_fail_lifecycle"})
    assert res_case.status_code == 200
    case_json = res_case.json()
    case_id = case_json["case_id"]
    assert case_json["eligibility"] is True
    assert case_json["risk_type"] == "PAYMENT_TIMEOUT"
    assert case_json["root_cause"] == "NETWORK_TIMEOUT"

    # 2. Recommend
    res_rec = client.post(f"/api/recovery/{case_id}/recommend")
    assert res_rec.status_code == 200
    rec_json = res_rec.json()
    assert rec_json["policy_decision"]["decision"] == "ALLOW"
    assert rec_json["ai_recommendation"]["action"] == "RETRY"

    # 3. Run E2E Lifecycle Flow (incorporating execute & verify)
    res_run = client.post(f"/api/recovery/{case_id}/run")
    assert res_run.status_code == 200
    run_json = res_run.json()
    
    assert run_json["case_id"] == case_id
    assert run_json["policy_decision"] == "ALLOW"
    assert run_json["execution_status"] == "VERIFICATION_REQUIRED"
    
    # Since simulated default mock client behavior returns FAILED for fallback verification check
    assert run_json["verification_status"] == "VERIFIED_FAILURE"
    assert run_json["recovered_amount_minor"] == 0

    # 4. Check MongoDB audit logs are generated and traceable
    audit_res = client.get(f"/api/recovery/{case_id}/audit")
    assert audit_res.status_code == 200
    audit_logs = audit_res.json()
    assert len(audit_logs) > 0
    # Must contain tracing details
    assert any(log["action"] == "RECOVERY_LIFECYCLE_COMPLETED" for log in audit_logs)
