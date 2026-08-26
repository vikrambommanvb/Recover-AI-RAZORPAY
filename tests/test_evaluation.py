import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_db
from app.db.collections import EVALUATION_RUNS_COLLECTION, EVALUATION_RESULTS_COLLECTION
from app.services.evaluation_service import EvaluationService
from app.db.mock_db import MockDatabase

# Set up mock database for tests
mock_db = MockDatabase()
app.dependency_overrides[get_db] = lambda: mock_db


def test_dataset_reproducibility():
    """
    Verify that generating datasets with the same seed results in identical data.
    """
    dataset_1 = EvaluationService.generate_demo_dataset(100, seed=42)
    dataset_2 = EvaluationService.generate_demo_dataset(100, seed=42)
    
    assert len(dataset_1) == 100
    assert len(dataset_2) == 100
    
    # Assert exact match of payment IDs and amounts
    for p1, p2 in zip(dataset_1, dataset_2):
        assert p1["payment_id"] == p2["payment_id"]
        assert p1["amount"] == p2["amount"]
        assert p1["status"] == p2["status"]
        assert p1["failure_reason"] == p2["failure_reason"]


@pytest.mark.anyio
async def test_evaluation_metrics_bounds():
    """
    Verify that:
    1. revenue_recovered <= revenue_at_risk.
    2. Failed attempts do not count towards recovered revenue.
    3. Blocked actions do not count.
    4. AI decisions do not count.
    """
    summary = await EvaluationService.run_evaluation(
        db=mock_db,
        dataset_size=100,
        seed=10,
        mode="MOCK",
        ai_provider_name="mock"
    )
    
    assert summary["dataset_size"] == 100
    assert summary["revenue_recovered"] <= summary["revenue_at_risk"]
    
    # Query case results to double check counts
    cases_cursor = mock_db[EVALUATION_RESULTS_COLLECTION].find({"evaluation_id": summary["evaluation_id"]})
    cases = []
    async for c in cases_cursor:
        cases.append(c)
        
    succeeded_cases = [c for c in cases if c["execution_status"] == "SUCCEEDED"]
    failed_cases = [c for c in cases if c["execution_status"] == "FAILED"]
    blocked_cases = [c for c in cases if c["execution_status"] == "BLOCKED"]
    
    # Compute manual revenue recovered
    manual_recovered = sum(c["amount"] for c in succeeded_cases)
    assert manual_recovered == summary["revenue_recovered"]
    
    # Verify that failed and blocked cases contributed ₹0
    failed_contrib = sum(c["amount_recovered"] for c in failed_cases)
    blocked_contrib = sum(c["amount_recovered"] for c in blocked_cases)
    assert failed_contrib == 0
    assert blocked_contrib == 0


def test_evaluations_api_flow():
    """
    Verify evaluations FastAPI endpoints (POST /evaluations, GET summary, metrics, and cases).
    """
    client = TestClient(app)
    
    # 1. Trigger evaluation run
    payload = {
        "dataset_size": 20,
        "seed": 42,
        "mode": "MOCK",
        "ai_provider": "mock"
    }
    response = client.post("/evaluations", json=payload)
    assert response.status_code == 200
    data = response.json()
    eval_id = data["evaluation_id"]
    assert eval_id is not None
    assert data["dataset_size"] == 20
    
    # 2. Get summary
    sum_resp = client.get(f"/evaluations/{eval_id}")
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()
    assert sum_data["evaluation_id"] == eval_id
    
    # 3. Get metrics
    met_resp = client.get(f"/evaluations/{eval_id}/metrics")
    assert met_resp.status_code == 200
    met_data = met_resp.json()
    assert "funnel" in met_data
    assert "outcomes" in met_data
    assert "ai_actions" in met_data
    assert "policy_decisions" in met_data
    assert met_data["evaluation_id"] == eval_id
    
    # 4. Get cases
    case_resp = client.get(f"/evaluations/{eval_id}/cases?limit=10&offset=0")
    assert case_resp.status_code == 200
    cases_list = case_resp.json()
    assert len(cases_list) <= 10
