import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_db
from app.models.payment import Payment
from app.models.recovery import RecoveryCase
from app.services.payment_service import PaymentService
from app.services.risk_service import RiskService
from app.db.collections import PAYMENTS_COLLECTION, RECOVERY_CASES_COLLECTION

# ==============================================================================
# Mock MongoDB Implementation for Offline/CI Testing
# ==============================================================================

class MockCursor:
    def __init__(self, data):
        self.data = data
        self.index = 0
        
    def skip(self, n):
        self.data = self.data[n:]
        return self
        
    def limit(self, n):
        self.data = self.data[:n]
        return self

    def sort(self, key_or_list, direction=None):
        if isinstance(key_or_list, list):
            sort_key = key_or_list[0][0]
            reverse = key_or_list[0][1] == -1
        else:
            sort_key = key_or_list
            reverse = direction == -1
            
        def get_sort_val(x):
            val = x.get(sort_key)
            if val is None:
                return ""
            return val

        self.data.sort(key=get_sort_val, reverse=reverse)
        return self
        
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        if self.index < len(self.data):
            res = self.data[self.index]
            self.index += 1
            return res
        else:
            raise StopAsyncIteration


class MockCollection:
    def __init__(self):
        self.docs = []
        
    def _matches_filter(self, doc, filter):
        for k, v in filter.items():
            if "." in k:
                parts = k.split(".")
                val = doc
                for part in parts:
                    if isinstance(val, dict):
                        val = val.get(part)
                    else:
                        val = None
            else:
                val = doc.get(k)

            if isinstance(v, dict):
                if "$in" in v:
                    if val not in v["$in"]:
                        return False
                elif "$lt" in v:
                    if val is None or val >= v["$lt"]:
                        return False
                elif "$gt" in v:
                    if val is None or val <= v["$gt"]:
                        return False
                else:
                    if val != v:
                        return False
            else:
                if val != v:
                    return False
        return True

    async def find_one(self, filter):
        for doc in self.docs:
            if self._matches_filter(doc, filter):
                return doc
        return None
        
    def find(self, filter=None):
        filter = filter or {}
        matched = []
        for doc in self.docs:
            if self._matches_filter(doc, filter):
                matched.append(doc)
        return MockCursor(matched)
        
    async def update_one(self, filter, update, upsert=False):
        doc = await self.find_one(filter)
        set_dict = update.get("$set", {})
        if doc:
            doc.update(set_dict)
        elif upsert:
            new_doc = {**filter, **set_dict}
            self.docs.append(new_doc)
        return None
        
    async def insert_many(self, docs):
        self.docs.extend(docs)
        class InsertResult:
            inserted_ids = [doc.get("payment_id") for doc in docs]
        return InsertResult()

    async def insert_one(self, doc):
        self.docs.append(doc)
        return None

    async def update_many(self, filter, update):
        set_dict = update.get("$set", {})
        count = 0
        for doc in self.docs:
            if self._matches_filter(doc, filter):
                doc.update(set_dict)
                count += 1
        return count

    async def count_documents(self, filter):
        count = 0
        for doc in self.docs:
            if self._matches_filter(doc, filter):
                count += 1
        return count



class MockDatabase:
    def __init__(self):
        self.collections = {}
        
    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection()
        return self.collections[name]

# Setup mock database
mock_db = MockDatabase()

# Override dependency in app for API route tests
app.dependency_overrides[get_db] = lambda: mock_db


# ==============================================================================
# Pytest Fixtures
# ==============================================================================

@pytest.fixture(autouse=True)
def clean_mock_db():
    """Clear all collections in the mock database before each test run."""
    mock_db.collections.clear()
    yield

@pytest.fixture
def test_client():
    return TestClient(app)


# ==============================================================================
# Classification Tests
# ==============================================================================

def test_classify_success_payment():
    """SUCCESS payment classification should map to NOT_AT_RISK and 0 amount at risk."""
    payment = Payment(
        payment_id="pay_001",
        amount=100000,
        currency="INR",
        status="captured",
        customer_id="cust_1"
    )
    risk_status, root_cause, amount_at_risk = RiskService.classify_payment(payment)
    assert risk_status == "NOT_AT_RISK"
    assert root_cause is None
    assert amount_at_risk == 0

def test_classify_bank_timeout():
    """BANK_TIMEOUT should map to AT_RISK and TRANSIENT_FAILURE."""
    payment = Payment(
        payment_id="pay_002",
        amount=250000,
        currency="INR",
        status="failed",
        failure_reason="Gateway response timeout / connection lost",
        customer_id="cust_1"
    )
    risk_status, root_cause, amount_at_risk = RiskService.classify_payment(payment)
    assert risk_status == "AT_RISK"
    assert root_cause == "TRANSIENT_FAILURE"
    assert amount_at_risk == 250000

def test_classify_insufficient_funds():
    """INSUFFICIENT_FUNDS should map to AT_RISK and CUSTOMER_FUNDS."""
    payment = Payment(
        payment_id="pay_003",
        amount=59900,
        currency="INR",
        status="failed",
        failure_reason="Insufficient balance in customer account",
        customer_id="cust_1"
    )
    risk_status, root_cause, amount_at_risk = RiskService.classify_payment(payment)
    assert risk_status == "AT_RISK"
    assert root_cause == "CUSTOMER_FUNDS"
    assert amount_at_risk == 59900

def test_classify_declined():
    """DECLINED should map to AT_RISK and PAYMENT_DECLINED."""
    payment = Payment(
        payment_id="pay_004",
        amount=499900,
        currency="INR",
        status="failed",
        failure_reason="Card was declined by issuing bank",
        customer_id="cust_1"
    )
    risk_status, root_cause, amount_at_risk = RiskService.classify_payment(payment)
    assert risk_status == "AT_RISK"
    assert root_cause == "PAYMENT_DECLINED"
    assert amount_at_risk == 499900

def test_classify_unknown():
    """UNKNOWN reason or unrecognized status should map to UNKNOWN risk and UNKNOWN root cause."""
    payment = Payment(
        payment_id="pay_005",
        amount=15000,
        currency="INR",
        status="failed",
        failure_reason="Unknown payment gateway error response code 999",
        customer_id="cust_1"
    )
    risk_status, root_cause, amount_at_risk = RiskService.classify_payment(payment)
    assert risk_status == "UNKNOWN"
    assert root_cause == "UNKNOWN"
    assert amount_at_risk == 15000

    # Test unknown overall payment status
    payment_unknown_status = Payment(
        payment_id="pay_006",
        amount=15000,
        currency="INR",
        status="processing",
        customer_id="cust_1"
    )
    risk_status, root_cause, amount_at_risk = RiskService.classify_payment(payment_unknown_status)
    assert risk_status == "UNKNOWN"
    assert root_cause == "UNKNOWN"
    assert amount_at_risk == 15000


# ==============================================================================
# Financial Precision Tests
# ==============================================================================

def test_financial_precision_paise():
    """Verify that integer minor units are preserved without floating-point conversion errors."""
    amount_rupees = 2499
    amount_paise = amount_rupees * 100 # ₹2,499 -> 249900 paise
    
    payment = Payment(
        payment_id="pay_precision",
        amount=amount_paise,
        currency="INR",
        status="failed",
        failure_reason="Gateway response timeout / connection lost",
        customer_id="cust_1"
    )
    
    risk_status, root_cause, amount_at_risk = RiskService.classify_payment(payment)
    assert isinstance(amount_at_risk, int)
    assert amount_at_risk == 249900
    # Proof of zero floating-point conversion errors
    assert amount_at_risk % 100 == 0


# ==============================================================================
# Customer History and Idempotency Tests
# ==============================================================================

@pytest.mark.anyio
async def test_customer_payment_history():
    """Verify that customer history accurately aggregates payments prior to the target payment's creation date."""
    base_time = datetime.now(timezone.utc)
    
    # Pre-populate history
    p1 = Payment(
        payment_id="pay_hist_001",
        amount=10000,
        status="captured",
        customer_id="cust_hist_1",
        created_at=base_time - timedelta(days=5)
    )
    p2 = Payment(
        payment_id="pay_hist_002",
        amount=20000,
        status="failed",
        failure_reason="insufficient balance",
        customer_id="cust_hist_1",
        created_at=base_time - timedelta(days=3)
    )
    p3 = Payment(
        payment_id="pay_hist_003",
        amount=30000,
        status="captured",
        customer_id="cust_hist_1",
        created_at=base_time - timedelta(days=1)
    )
    
    await PaymentService.save_payment(mock_db, p1)
    await PaymentService.save_payment(mock_db, p2)
    await PaymentService.save_payment(mock_db, p3)
    
    # Target payment created 2 days ago
    target_time = base_time - timedelta(days=2)
    history = await PaymentService.get_customer_history(mock_db, "cust_hist_1", target_time)
    
    # p1 (5 days ago) and p2 (3 days ago) are before target_time. p3 (1 day ago) is after.
    # Therefore, 2 previous payments: 1 success (p1), 1 failed (p2).
    assert history["previous_payment_count"] == 2
    assert history["successful_payment_count"] == 1
    assert history["previous_failure_count"] == 1

@pytest.mark.anyio
async def test_idempotent_recovery_case_creation():
    """Verify that multiple analysis calls return the same case and do not duplicate MongoDB case records."""
    payment = Payment(
        payment_id="pay_idem_001",
        amount=499900,
        status="failed",
        failure_reason="Gateway response timeout / connection lost",
        customer_id="cust_idem_1",
        created_at=datetime.now(timezone.utc)
    )
    await PaymentService.save_payment(mock_db, payment)
    
    # First analysis
    case1 = await RiskService.analyze_payment(mock_db, "pay_idem_001")
    assert case1.case_id == "case_pay_idem_001"
    assert case1.risk_status == "AT_RISK"
    assert case1.root_cause == "TRANSIENT_FAILURE"
    assert case1.status == "PENDING"
    
    # Verify saved in mock database
    cases_in_db = mock_db[RECOVERY_CASES_COLLECTION].docs
    assert len(cases_in_db) == 1
    assert cases_in_db[0]["case_id"] == "case_pay_idem_001"
    
    # Second analysis of the same payment
    case2 = await RiskService.analyze_payment(mock_db, "pay_idem_001")
    assert case2.case_id == "case_pay_idem_001"
    
    # Verify no duplicate case was created in MongoDB
    assert len(mock_db[RECOVERY_CASES_COLLECTION].docs) == 1


# ==============================================================================
# API Routes Tests
# ==============================================================================

def test_api_list_and_get_payments(test_client):
    """Test standard GET /payments and GET /payments/{payment_id} API behavior."""
    # Pre-populate payments
    p1 = {
        "payment_id": "pay_api_001",
        "amount": 9900,
        "currency": "INR",
        "status": "captured",
        "customer_id": "cust_api_1",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "metadata": {}
    }
    mock_db[PAYMENTS_COLLECTION].docs.append(p1)
    
    # Test List
    response = test_client.get("/payments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["payment_id"] == "pay_api_001"
    assert data[0]["amount"] == 9900
    
    # Test Get
    response_get = test_client.get("/payments/pay_api_001")
    assert response_get.status_code == 200
    assert response_get.json()["payment_id"] == "pay_api_001"
    
    # Test Get Not Found
    response_missing = test_client.get("/payments/pay_api_missing")
    assert response_missing.status_code == 404
    assert "not found" in response_missing.json()["detail"].lower()

def test_api_risk_analyze_and_cases(test_client):
    """Test POST /risk/analyze/{payment_id} and GET /risk/cases APIs."""
    p_fail = {
        "payment_id": "pay_api_fail",
        "amount": 150000,
        "currency": "INR",
        "status": "failed",
        "failure_reason": "Insufficient balance in customer account",
        "customer_id": "cust_api_2",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "metadata": {}
    }
    mock_db[PAYMENTS_COLLECTION].docs.append(p_fail)
    
    # Run Analyze via API
    response = test_client.post("/risk/analyze/pay_api_fail")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["payment_id"] == "pay_api_fail"
    assert res_data["risk_status"] == "AT_RISK"
    assert res_data["amount_at_risk"] == 150000
    assert res_data["root_cause"] == "CUSTOMER_FUNDS"
    assert res_data["recovery_case_id"] == "case_pay_api_fail"
    
    # Verify Case List
    cases_response = test_client.get("/risk/cases")
    assert cases_response.status_code == 200
    cases_data = cases_response.json()
    assert len(cases_data) == 1
    assert cases_data[0]["case_id"] == "case_pay_api_fail"
    assert cases_data[0]["status"] == "PENDING"
    
    # Get specific Case
    case_response = test_client.get("/risk/cases/case_pay_api_fail")
    assert case_response.status_code == 200
    assert case_response.json()["case_id"] == "case_pay_api_fail"
    
    # Case not found
    case_missing = test_client.get("/risk/cases/case_missing")
    assert case_missing.status_code == 404
