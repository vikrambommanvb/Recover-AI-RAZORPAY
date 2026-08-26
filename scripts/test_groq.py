import asyncio
import json
from app.core.config import settings
from app.services.ai_service import GroqProvider
from app.services.recovery_agent import RecoveryAgentService
from app.models.payment import Payment
from app.models.recovery import RecoveryCase
from app.db.collections import PAYMENTS_COLLECTION, RECOVERY_CASES_COLLECTION
from tests.test_risk_engine import mock_db

async def main():
    print("Starting Groq integration test...")
    
    # Verify Groq config
    try:
        api_key = settings.check_groq_config()
        # Cleanly print confirmation without exposing key
        masked_key = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "..."
        print(f"Groq API Key found ({masked_key}). Model configured: {settings.GROQ_MODEL}")
    except ValueError as e:
        print(f"Error: {e}")
        print("Please configure GROQ_API_KEY in your .env file to run this test.")
        return

    # Seed mock database with synthetic test case
    payment = Payment(
        payment_id="pay_groq_test_123",
        amount=249900,  # ₹2,499.00
        currency="INR",
        status="failed",
        failure_reason="Bank timeout during network handshake",
        customer_id="cust_groq_test"
    )
    # Ensure any existing is cleared
    mock_db.collections.clear()
    mock_db[PAYMENTS_COLLECTION].docs.append(payment.model_dump())

    case = RecoveryCase(
        case_id="case_pay_groq_test_123",
        payment_id="pay_groq_test_123",
        amount_at_risk=249900,
        risk_status="AT_RISK",
        root_cause="TRANSIENT_FAILURE",
        status="PENDING",
        previous_payment_count=6,
        successful_payment_count=6,
        previous_failure_count=0
    )
    mock_db[RECOVERY_CASES_COLLECTION].docs.append(case.model_dump())

    print("Executing recovery decision service with real GroqProvider...")
    try:
        # Pass real GroqProvider to decision service
        result = await RecoveryAgentService.decide_recovery_action(
            db=mock_db,
            case_id="case_pay_groq_test_123",
            ai_provider=GroqProvider()
        )
        print("\n--- DECISION RESULT ---")
        print(json.dumps(result, indent=2))
        print("-----------------------")
        print("\nSuccess! Groq API integration verified.")
    except Exception as e:
        print(f"Groq integration failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
