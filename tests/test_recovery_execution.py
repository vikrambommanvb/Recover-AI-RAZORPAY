import pytest
import hmac
import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_db, get_razorpay_service, get_ai_provider
from app.services.razorpay_service import RazorpayService, MockRazorpayService
from app.services.ai_service import MockAIProvider
from app.models.payment import Payment
from app.models.recovery import RecoveryCase
from app.models.recovery_action import RecoveryAction, RecoveryActionStatus
from app.models.agent_decision import RecoveryAction as RecAction
from app.db.collections import (
    PAYMENTS_COLLECTION,
    RECOVERY_CASES_COLLECTION,
    AGENT_DECISIONS_COLLECTION,
    RECOVERY_ACTIONS_COLLECTION,
    WEBHOOK_EVENTS_COLLECTION,
    AUDIT_LOGS_COLLECTION
)
from tests.test_risk_engine import mock_db
from app.core.config import settings

# Override AI provider globally for testing execution
app.dependency_overrides[get_ai_provider] = lambda: MockAIProvider()


@pytest.fixture
def mock_rzp():
    """Fixture to inject MockRazorpayService and override FastAPI dependency injection."""
    service = MockRazorpayService()
    app.dependency_overrides[get_razorpay_service] = lambda: service
    yield service
    if get_razorpay_service in app.dependency_overrides:
        del app.dependency_overrides[get_razorpay_service]


@pytest.fixture(autouse=True)
def clean_mock_db():
    """Clear all collections in mock database before each test run."""
    mock_db.collections.clear()
    yield


@pytest.fixture
def test_client():
    return TestClient(app)


# ==============================================================================
# Phase 4 Recovery Execution Tests
# ==============================================================================

def test_razorpay_credential_validation():
    """
    Test: RazorpayService should reject live key prefixes (rzp_live_)
    and non-standard keys, but accept valid test keys (rzp_test_).
    """
    # Accept test mode keys
    service = RazorpayService(key_id="rzp_test_123", key_secret="secret")
    assert service.key_id == "rzp_test_123"

    # Reject live mode keys
    with pytest.raises(ValueError, match="LIVE mode key detected"):
        RazorpayService(key_id="rzp_live_123", key_secret="secret")

    # Reject keys missing standard prefix
    with pytest.raises(ValueError, match="Invalid Razorpay API Key prefix"):
        RazorpayService(key_id="invalid_prefix", key_secret="secret")


def test_execute_success(test_client, mock_rzp):
    """
    Test: Executing a recovery for an eligible case with an ALLOWED AI decision.
    Should create a Razorpay order and transition action status to VERIFICATION_REQUIRED.
    """
    payment = Payment(
        payment_id="pay_001",
        amount=250000,  # ₹2,500
        currency="INR",
        status="failed",
        failure_reason="Gateway timeout",
        customer_id="cust_1"
    )
    mock_db[PAYMENTS_COLLECTION].docs.append(payment.model_dump())

    case = RecoveryCase(
        case_id="case_001",
        payment_id="pay_001",
        amount_at_risk=250000,
        risk_status="AT_RISK",
        root_cause="TRANSIENT_FAILURE",
        status="PENDING"
    )
    mock_db[RECOVERY_CASES_COLLECTION].docs.append(case.model_dump())

    # Seed latest allowed AI decision
    decision = {
        "case_id": "case_001",
        "payment_id": "pay_001",
        "recommended_action": "RETRY",
        "confidence": 0.85,
        "is_latest": True,
        "policy_result": {
            "decision": "ALLOW",
            "reason": "Allowed by rules"
        }
    }
    mock_db[AGENT_DECISIONS_COLLECTION].docs.append(decision)

    response = test_client.post("/recovery/case_001/execute")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VERIFICATION_REQUIRED"
    assert data["decision"] == "ALLOW"
    assert data["action_id"].startswith("act_")

    # Verify action saved in DB
    action_doc = mock_db[RECOVERY_ACTIONS_COLLECTION].docs[0]
    assert action_doc["status"] == "VERIFICATION_REQUIRED"
    assert action_doc["razorpay_order_id"].startswith("order_rec_")
    assert action_doc["attempt_number"] == 1

    # Verify case status updated in DB
    case_doc = mock_db[RECOVERY_CASES_COLLECTION].docs[0]
    assert case_doc["status"] == "IN_PROGRESS"


def test_execute_amount_exceeded(test_client, mock_rzp):
    """
    Test: Enforcing maximum recovery amount limit boundary.
    If transaction amount exceeds settings limit (₹5,000 / 500000 paise),
    execution is blocked.
    """
    payment = Payment(
        payment_id="pay_large",
        amount=600000,  # ₹6,000 (exceeds default ₹5,000)
        currency="INR",
        status="failed",
        failure_reason="Gateway timeout",
        customer_id="cust_1"
    )
    mock_db[PAYMENTS_COLLECTION].docs.append(payment.model_dump())

    case = RecoveryCase(
        case_id="case_large",
        payment_id="pay_large",
        amount_at_risk=600000,
        risk_status="AT_RISK",
        root_cause="TRANSIENT_FAILURE",
        status="PENDING"
    )
    mock_db[RECOVERY_CASES_COLLECTION].docs.append(case.model_dump())

    decision = {
        "case_id": "case_large",
        "payment_id": "pay_large",
        "recommended_action": "RETRY",
        "confidence": 0.85,
        "is_latest": True,
        "policy_result": {
            "decision": "ALLOW",
            "reason": "Allowed by rules"
        }
    }
    mock_db[AGENT_DECISIONS_COLLECTION].docs.append(decision)

    response = test_client.post("/recovery/case_large/execute")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "BLOCKED"
    assert data["decision"] == "BLOCK"

    action_doc = mock_db[RECOVERY_ACTIONS_COLLECTION].docs[0]
    assert action_doc["status"] == "BLOCKED"
    assert "exceeds maximum recovery limit" in action_doc["reason"]


def test_execute_attempt_limit_escalated(test_client, mock_rzp):
    """
    Test: Recovery attempt count boundaries.
    If case exceeds 2 attempts, the executor blocks execution and escalates.
    """
    payment = Payment(
        payment_id="pay_retry",
        amount=200000,
        currency="INR",
        status="failed",
        failure_reason="Gateway timeout",
        customer_id="cust_1"
    )
    mock_db[PAYMENTS_COLLECTION].docs.append(payment.model_dump())

    case = RecoveryCase(
        case_id="case_retry",
        payment_id="pay_retry",
        amount_at_risk=200000,
        risk_status="AT_RISK",
        root_cause="TRANSIENT_FAILURE",
        status="PENDING"
    )
    mock_db[RECOVERY_CASES_COLLECTION].docs.append(case.model_dump())

    decision = {
        "case_id": "case_retry",
        "payment_id": "pay_retry",
        "recommended_action": "RETRY",
        "confidence": 0.85,
        "is_latest": True,
        "policy_result": {
            "decision": "ALLOW",
            "reason": "Allowed by rules"
        }
    }
    mock_db[AGENT_DECISIONS_COLLECTION].docs.append(decision)

    # Seed 2 prior triggered attempts
    for i in range(2):
        action = RecoveryAction(
            action_id=f"act_prev_{i}",
            case_id="case_retry",
            payment_id="pay_retry",
            action_type="RETRY",
            amount=200000,
            currency="INR",
            status=RecoveryActionStatus.FAILED,
            attempt_number=i+1,
            policy_decision="ALLOW"
        )
        mock_db[RECOVERY_ACTIONS_COLLECTION].docs.append(action.model_dump())

    response = test_client.post("/recovery/case_retry/execute")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ESCALATED"
    assert data["decision"] == "ESCALATE"

    # Verify action escalated in DB
    action_doc = mock_db[RECOVERY_ACTIONS_COLLECTION].docs[-1]
    assert action_doc["status"] == "ESCALATED"
    assert "limit reached" in action_doc["reason"]

    # Verify case was updated to escalated
    case_doc = mock_db[RECOVERY_CASES_COLLECTION].docs[0]
    assert case_doc["guardrail_status"] == "escalated"


def test_execute_cooldown_blocked(test_client, mock_rzp):
    """
    Test: Recovery attempt cooldown boundaries.
    If another recovery action was attempted less than 300s ago, block execution.
    """
    payment = Payment(
        payment_id="pay_cooldown",
        amount=200000,
        currency="INR",
        status="failed",
        customer_id="cust_1"
    )
    mock_db[PAYMENTS_COLLECTION].docs.append(payment.model_dump())

    case = RecoveryCase(
        case_id="case_cooldown",
        payment_id="pay_cooldown",
        amount_at_risk=200000,
        risk_status="AT_RISK",
        status="PENDING"
    )
    mock_db[RECOVERY_CASES_COLLECTION].docs.append(case.model_dump())

    decision = {
        "case_id": "case_cooldown",
        "payment_id": "pay_cooldown",
        "recommended_action": "RETRY",
        "confidence": 0.85,
        "is_latest": True,
        "policy_result": {"decision": "ALLOW", "reason": "Allowed"}
    }
    mock_db[AGENT_DECISIONS_COLLECTION].docs.append(decision)

    # Seed prior action created 10 seconds ago
    prior_action = RecoveryAction(
        action_id="act_prior",
        case_id="case_cooldown",
        payment_id="pay_cooldown",
        action_type="RETRY",
        amount=200000,
        currency="INR",
        status=RecoveryActionStatus.FAILED,
        attempt_number=1,
        policy_decision="ALLOW",
        created_at=datetime.now(timezone.utc) - timedelta(seconds=10)
    )
    mock_db[RECOVERY_ACTIONS_COLLECTION].docs.append(prior_action.model_dump())

    response = test_client.post("/recovery/case_cooldown/execute")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "BLOCKED"
    assert data["decision"] == "BLOCK"

    action_doc = mock_db[RECOVERY_ACTIONS_COLLECTION].docs[-1]
    assert action_doc["status"] == "BLOCKED"
    assert "Cooldown active" in action_doc["reason"]


def test_execute_idempotency(test_client, mock_rzp):
    """
    Test: Request idempotency.
    Two consecutive identical requests must return the same action and not spawn duplicates.
    """
    payment = Payment(
        payment_id="pay_idemp",
        amount=200000,
        currency="INR",
        status="failed",
        customer_id="cust_1"
    )
    mock_db[PAYMENTS_COLLECTION].docs.append(payment.model_dump())

    case = RecoveryCase(
        case_id="case_idemp",
        payment_id="pay_idemp",
        amount_at_risk=200000,
        risk_status="AT_RISK",
        status="PENDING"
    )
    mock_db[RECOVERY_CASES_COLLECTION].docs.append(case.model_dump())

    decision = {
        "case_id": "case_idemp",
        "payment_id": "pay_idemp",
        "recommended_action": "RETRY",
        "confidence": 0.85,
        "is_latest": True,
        "policy_result": {"decision": "ALLOW", "reason": "Allowed"}
    }
    mock_db[AGENT_DECISIONS_COLLECTION].docs.append(decision)

    # First request
    resp1 = test_client.post("/recovery/case_idemp/execute")
    assert resp1.status_code == 200
    data1 = resp1.json()

    # Second request
    resp2 = test_client.post("/recovery/case_idemp/execute")
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Verify same action ID is returned and only 1 action exists in database
    assert data1["action_id"] == data2["action_id"]
    assert len(mock_db[RECOVERY_ACTIONS_COLLECTION].docs) == 1


def test_execute_already_captured_check(test_client, mock_rzp):
    """
    Test: Gateway state protection check.
    If the payment is already captured on the gateway, local database is updated,
    and action is blocked.
    """
    # Force Mock to return status = captured
    mock_rzp.simulated_behavior = "ALREADY_CAPTURED"

    payment = Payment(
        payment_id="pay_captured_123",
        amount=200000,
        currency="INR",
        status="failed",
        customer_id="cust_1"
    )
    mock_db[PAYMENTS_COLLECTION].docs.append(payment.model_dump())

    case = RecoveryCase(
        case_id="case_captured",
        payment_id="pay_captured_123",
        amount_at_risk=200000,
        risk_status="AT_RISK",
        status="PENDING"
    )
    mock_db[RECOVERY_CASES_COLLECTION].docs.append(case.model_dump())

    decision = {
        "case_id": "case_captured",
        "payment_id": "pay_captured_123",
        "recommended_action": "RETRY",
        "confidence": 0.85,
        "is_latest": True,
        "policy_result": {"decision": "ALLOW", "reason": "Allowed"}
    }
    mock_db[AGENT_DECISIONS_COLLECTION].docs.append(decision)

    response = test_client.post("/recovery/case_captured/execute")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "BLOCKED"
    assert data["decision"] == "BLOCK"

    # Verify local Payment updated to captured
    payment_doc = mock_db[PAYMENTS_COLLECTION].docs[0]
    assert payment_doc["status"] == "captured"

    # Verify case closed
    case_doc = mock_db[RECOVERY_CASES_COLLECTION].docs[0]
    assert case_doc["status"] == "CLOSED"
    assert case_doc["guardrail_status"] == "allowed"


def test_execute_ai_gate_rejection(test_client, mock_rzp):
    """
    Test: Rejection gate check.
    If PolicyEngine evaluated to BLOCK/ESCALATE, execute endpoint refuses execution (400 Bad Request).
    """
    payment = Payment(
        payment_id="pay_gate",
        amount=200000,
        status="failed",
        customer_id="cust_1"
    )
    mock_db[PAYMENTS_COLLECTION].docs.append(payment.model_dump())

    case = RecoveryCase(
        case_id="case_gate",
        payment_id="pay_gate",
        amount_at_risk=200000,
        status="PENDING"
    )
    mock_db[RECOVERY_CASES_COLLECTION].docs.append(case.model_dump())

    decision = {
        "case_id": "case_gate",
        "payment_id": "pay_gate",
        "recommended_action": "RETRY",
        "confidence": 0.85,
        "is_latest": True,
        "policy_result": {"decision": "BLOCK", "reason": "Risk status or retry limit violation"}
    }
    mock_db[AGENT_DECISIONS_COLLECTION].docs.append(decision)

    response = test_client.post("/recovery/case_gate/execute")
    assert response.status_code == 400
    assert "Safety Gate Rejection" in response.json()["detail"]


def test_execute_graceful_timeout_handling(test_client, mock_rzp):
    """
    Test: Graceful failure handling.
    If Razorpay API call times out, execution is marked as FAILED with error audit saved.
    """
    mock_rzp.simulated_behavior = "TIMEOUT"

    payment = Payment(
        payment_id="pay_timeout",
        amount=200000,
        status="failed",
        customer_id="cust_1"
    )
    mock_db[PAYMENTS_COLLECTION].docs.append(payment.model_dump())

    case = RecoveryCase(
        case_id="case_timeout",
        payment_id="pay_timeout",
        amount_at_risk=200000,
        status="PENDING"
    )
    mock_db[RECOVERY_CASES_COLLECTION].docs.append(case.model_dump())

    decision = {
        "case_id": "case_timeout",
        "payment_id": "pay_timeout",
        "recommended_action": "RETRY",
        "confidence": 0.85,
        "is_latest": True,
        "policy_result": {"decision": "ALLOW", "reason": "Allowed"}
    }
    mock_db[AGENT_DECISIONS_COLLECTION].docs.append(decision)

    response = test_client.post("/recovery/case_timeout/execute")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "FAILED"

    # Verify action saved as FAILED
    action_doc = mock_db[RECOVERY_ACTIONS_COLLECTION].docs[0]
    assert action_doc["status"] == "FAILED"
    assert "API request timeout" in action_doc["reason"]

    # Verify audit log saved
    audit_doc = mock_db[AUDIT_LOGS_COLLECTION].docs[0]
    assert audit_doc["action"] == "RECOVERY_ATTEMPT_FAILED"
    assert audit_doc["entity_id"] == "case_timeout"


# ==============================================================================
# Webhook Signature Validation & Processing Tests
# ==============================================================================

def test_webhook_payment_captured_success(test_client):
    """
    Test: Webhook signature verification and state update.
    Receiving valid payment.captured webhook transitions RecoveryAction to SUCCEEDED and case to CLOSED.
    """
    # Setup test webhook secret
    settings.RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret"

    # Seed execution action awaiting verification
    action = RecoveryAction(
        action_id="act_web_1",
        case_id="case_web_1",
        payment_id="pay_web_1",
        action_type="RETRY",
        amount=100000,
        currency="INR",
        status=RecoveryActionStatus.VERIFICATION_REQUIRED,
        razorpay_order_id="order_web_1",
        attempt_number=1,
        policy_decision="ALLOW"
    )
    mock_db[RECOVERY_ACTIONS_COLLECTION].docs.append(action.model_dump())

    case = RecoveryCase(
        case_id="case_web_1",
        payment_id="pay_web_1",
        amount_at_risk=100000,
        risk_status="AT_RISK",
        status="IN_PROGRESS"
    )
    mock_db[RECOVERY_CASES_COLLECTION].docs.append(case.model_dump())

    payment = Payment(
        payment_id="pay_web_1",
        amount=100000,
        currency="INR",
        status="failed",
        customer_id="cust_1"
    )
    mock_db[PAYMENTS_COLLECTION].docs.append(payment.model_dump())

    payload = {
        "id": "evt_test_captured_123",
        "entity": "event",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_gateway_recovered",
                    "amount": 100000,
                    "currency": "INR",
                    "status": "captured",
                    "order_id": "order_web_1"
                }
            }
        }
    }
    body = json.dumps(payload).encode("utf-8")

    # Generate HMAC SHA256 signature
    signature = hmac.new(
        b"test_webhook_secret",
        body,
        hashlib.sha256
    ).hexdigest()

    response = test_client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": signature}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Webhook processed successfully."

    # Check that Action is now SUCCEEDED
    action_doc = mock_db[RECOVERY_ACTIONS_COLLECTION].docs[0]
    assert action_doc["status"] == "SUCCEEDED"
    assert action_doc["razorpay_payment_id"] == "pay_gateway_recovered"

    # Check Case CLOSED
    case_doc = mock_db[RECOVERY_CASES_COLLECTION].docs[0]
    assert case_doc["status"] == "CLOSED"
    assert case_doc["final_status"] == "closed"
    assert case_doc["amount_at_risk"] == 0

    # Check local payment synchronized to captured
    payment_doc = mock_db[PAYMENTS_COLLECTION].docs[0]
    assert payment_doc["status"] == "captured"


def test_webhook_invalid_signature(test_client):
    """
    Test: Security check.
    Webhook with invalid signature header must be rejected with 401.
    """
    payload = {"id": "evt_test", "event": "payment.captured"}
    body = json.dumps(payload).encode("utf-8")

    response = test_client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": "invalid_signature"}
    )
    assert response.status_code == 401
    assert "validation failed" in response.json()["detail"]


def test_webhook_duplicate_idempotency(test_client):
    """
    Test: Webhook idempotency.
    Repeating same event webhook twice returns 200 OK immediately with "processed" message.
    """
    settings.RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret"

    payload = {
        "id": "evt_duplicate_999",
        "entity": "event",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_xxx",
                    "status": "captured",
                    "order_id": "order_xxx"
                }
            }
        }
    }
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(b"test_webhook_secret", body, hashlib.sha256).hexdigest()

    # First delivery
    resp1 = test_client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": signature}
    )
    assert resp1.status_code == 200

    # Second duplicate delivery
    resp2 = test_client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": signature}
    )
    assert resp2.status_code == 200
    assert "already processed" in resp2.json()["message"]

    # Verify only 1 webhook event record created in DB
    assert len(mock_db[WEBHOOK_EVENTS_COLLECTION].docs) == 1
