import asyncio
import os
import sys

# Add root folder to python path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.mongodb import db
from app.services.evaluation_service import EvaluationService


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


async def run_demo():
    print("==================================================")
    print(" RecoverAI - Judge Demo Simulation Runner")
    print("==================================================")
    
    # 1. Verify Configuration & Database Connect
    print("Connecting to database...")
    try:
        await db.connect()
        print("MongoDB connection: SUCCESSFUL.")
    except Exception as e:
        print(f"MongoDB connection: FAILED ({e}).")
        print("Please check your MONGODB_URI in .env.")
        sys.exit(1)

    # 2. Trigger Evaluation Run
    print("Executing 500-payment batch simulation in MOCK mode...")
    try:
        summary = await EvaluationService.run_evaluation(
            db=db.db,
            dataset_size=500,
            seed=42,
            mode="MOCK",
            ai_provider_name="mock"
        )
        
        # 3. Print Results Summary
        print("\n==================================================")
        print("           RECOVERAI DEMO RUN SUMMARY")
        print("==================================================")
        print(f"Evaluation ID:          {summary['evaluation_id']}")
        print(f"Mode:                   {summary['evaluation_mode']}")
        print(f"Dataset Size:           {summary['dataset_size']} payments")
        print(f"Eligible At-Risk:       {summary['eligible_cases']}")
        print(f"AI Decisions:           {summary['ai_decisions']}")
        print(f"Policy Allowed:         {summary['policy_allowed_count']}")
        print(f"Recovery Attempts:      {summary['recovery_attempts']}")
        print(f"Successful Recoveries:  {summary['successful_recoveries']}")
        print(f"Failed Recovery Attempts:{summary['failed_recoveries']}")
        print(f"Policy Overrides:       {summary['policy_overrides']}")
        print(f"Blocked Actions:        {summary['blocked_actions']}")
        print(f"Escalated Cases:        {summary['escalated_cases']}")
        print("--------------------------------------------------")
        print(f"Revenue At Risk:        {format_rupees(summary['revenue_at_risk'])}")
        print(f"Revenue Recovered:      {format_rupees(summary['revenue_recovered'])}")
        print(f"Revenue Recovery Rate:  {summary['recovery_rate'] * 100:.2f}%")
        print(f"Case Recovery Rate:     {summary['case_recovery_rate'] * 100:.2f}%")
        print("==================================================")
        
        # 4. Show dashboard access details
        print("\nTo launch the interactive Judge Dashboard:")
        print("1. Start FastAPI backend:   uvicorn app.main:app --reload")
        print("2. Start React dashboard:   cd frontend && npm run dev")
        print("3. Open in your browser:    http://localhost:5173")
        print("==================================================")
        
    except Exception as e:
        print(f"Demo simulation run failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(run_demo())
