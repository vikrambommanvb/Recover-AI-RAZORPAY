from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.api.dependencies import get_db
from app.services.evaluation_service import EvaluationService
from app.db.collections import EVALUATION_RUNS_COLLECTION, EVALUATION_RESULTS_COLLECTION
from app.models.evaluation import EvaluationRun, CaseEvaluationResult

router = APIRouter()


class StartEvaluationRequest(BaseModel):
    dataset_size: int = Field(500, ge=10, le=1000, description="Size of simulation dataset")
    seed: int = Field(42, description="Random seed for deterministic data generation")
    mode: str = Field("MOCK", description="Evaluation mode: DEMO, MOCK, or LIVE_TEST")
    ai_provider: str = Field("mock", description="AI Provider: mock or groq")


@router.post("", response_model=EvaluationRun)
async def start_evaluation(
    request: StartEvaluationRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Triggers a batch evaluation run using the specified dataset size and seed.
    Returns a summary of the simulated recovery metrics.
    """
    try:
        summary = await EvaluationService.run_evaluation(
            db=db,
            dataset_size=request.dataset_size,
            seed=request.seed,
            mode=request.mode,
            ai_provider_name=request.ai_provider
        )
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation simulation failed: {str(e)}"
        )


@router.get("/{evaluation_id}", response_model=EvaluationRun)
async def get_evaluation_summary(
    evaluation_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieve the aggregated metrics and metadata summary for a specific evaluation run.
    """
    run_doc = await db[EVALUATION_RUNS_COLLECTION].find_one({"evaluation_id": evaluation_id})
    if not run_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{evaluation_id}' not found."
        )
    return EvaluationRun(**run_doc)


@router.get("/{evaluation_id}/metrics")
async def get_evaluation_metrics(
    evaluation_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieve detailed charts data (funnel stages, outcome distributions, and policy overrides)
    for dashboard visualizations.
    """
    run_doc = await db[EVALUATION_RUNS_COLLECTION].find_one({"evaluation_id": evaluation_id})
    if not run_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{evaluation_id}' not found."
        )
    
    run = EvaluationRun(**run_doc)
    
    # Construct Funnel Stages
    # funnel: TOTAL -> AT-RISK -> ELIGIBLE -> AI DECISIONS -> POLICY ALLOWED -> ATTEMPTS -> RECOVERED
    funnel = [
        {"stage": "Total Payments", "count": run.dataset_size},
        {"stage": "At-Risk Payments", "count": run.eligible_cases},
        {"stage": "Eligible Cases", "count": run.eligible_cases},
        {"stage": "AI Recommendations", "count": run.ai_decisions - run.ai_no_action_count},
        {"stage": "Policy Allowed", "count": run.policy_allowed_count},
        {"stage": "Recovery Attempts", "count": run.recovery_attempts},
        {"stage": "Verified Success", "count": run.successful_recoveries}
    ]
    
    # Construct Outcome Distribution counts
    # Outcomes: RECOVERED, FAILED, BLOCKED, ESCALATED, STOPPED
    outcomes = [
        {"outcome": "Recovered", "count": run.successful_recoveries},
        {"outcome": "Failed", "count": run.failed_recoveries},
        {"outcome": "Blocked", "count": run.blocked_actions},
        {"outcome": "Escalated", "count": run.escalated_cases},
        {"outcome": "Stopped", "count": run.stopped_cases},
        {"outcome": "No Action", "count": run.dataset_size - run.eligible_cases}
    ]
    
    # AI Decisions Breakdown
    ai_actions = [
        {"action": "RETRY", "count": run.ai_retry_count},
        {"action": "REMIND", "count": run.ai_remind_count},
        {"action": "STOP", "count": run.ai_stop_count},
        {"action": "ESCALATE", "count": run.ai_escalate_count},
        {"action": "NO_ACTION", "count": run.ai_no_action_count}
    ]
    
    # Policy Decisions Breakdown
    policy_decisions = [
        {"decision": "ALLOW", "count": run.policy_allowed_count},
        {"decision": "BLOCK", "count": run.policy_blocked_count},
        {"decision": "ESCALATE", "count": run.policy_escalated_count}
    ]
    
    return {
        "evaluation_id": evaluation_id,
        "summary": run.model_dump(),
        "funnel": funnel,
        "outcomes": outcomes,
        "ai_actions": ai_actions,
        "policy_decisions": policy_decisions
    }


@router.get("/{evaluation_id}/cases", response_model=List[CaseEvaluationResult])
async def get_evaluation_cases(
    evaluation_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieve paginated per-case evaluation results for tabular list views.
    """
    cursor = db[EVALUATION_RESULTS_COLLECTION].find({"evaluation_id": evaluation_id}).skip(offset).limit(limit)
    results = []
    async for doc in cursor:
        results.append(CaseEvaluationResult(**doc))
    return results
