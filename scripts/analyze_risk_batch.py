import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Add root folder to python path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.collections import PAYMENTS_COLLECTION, RECOVERY_CASES_COLLECTION
from app.services.risk_service import RiskService

def format_rupees(paise: int) -> str:
    """Format minor unit paise value to human-readable Indian Rupee (₹) format."""
    rupees = paise // 100
    # Use standard Indian comma grouping: e.g. 18,42,500
    s = str(rupees)
    if len(s) <= 3:
        return f"₹{s}"
    
    last_three = s[-3:]
    remaining = s[:-3]
    
    # Group the remaining numbers in pairs of two
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

async def analyze_batch():
    if not settings.MONGODB_URI:
        print("Error: MONGODB_URI environment variable is missing. Cannot run batch analysis.")
        sys.exit(1)

    print("Connecting to MongoDB...")
    client_kwargs = {}
    try:
        import certifi
        client_kwargs["tlsCAFile"] = certifi.where()
    except ImportError:
        client_kwargs["tlsAllowInvalidCertificates"] = True

    client = AsyncIOMotorClient(settings.MONGODB_URI, **client_kwargs)
    db = client[settings.MONGODB_DATABASE]
    
    # Fetch all synthetic payment records
    cursor = db[PAYMENTS_COLLECTION].find({"metadata.is_synthetic": True})
    payments = []
    async for doc in cursor:
        payments.append(doc)
        
    if not payments:
        # Fallback to all payments if no synthetic payments are present
        cursor = db[PAYMENTS_COLLECTION].find()
        async for doc in cursor:
            payments.append(doc)
            
    if not payments:
        print("No payments found in database. Please run the seeding script first.")
        client.close()
        sys.exit(0)

    total_payments = len(payments)
    successful_count = 0
    failed_count = 0
    unknown_count = 0
    payments_at_risk = 0
    total_payment_value = 0
    total_revenue_at_risk = 0
    cases_created = 0

    print(f"Analyzing {total_payments} payments...")
    
    # Process each payment idempotently
    for payment_doc in payments:
        payment_id = payment_doc["payment_id"]
        status = str(payment_doc.get("status", "")).lower()
        amount = int(payment_doc.get("amount", 0))
        
        total_payment_value += amount
        
        # Count statuses
        if status in ["captured", "authorized", "successful", "success"]:
            successful_count += 1
        elif status in ["failed"]:
            failed_count += 1
        else:
            unknown_count += 1
            
        try:
            # Perform analysis
            case = await RiskService.analyze_payment(db, payment_id)
            if case.risk_status == "AT_RISK":
                payments_at_risk += 1
                total_revenue_at_risk += case.amount_at_risk
                cases_created += 1
        except Exception as e:
            print(f"Error analyzing payment {payment_id}: {e}")

    print("\n==================================================")
    print(" RecoverAI - Revenue Risk Analysis Summary")
    print("==================================================")
    print(f"Payments analyzed:        {total_payments}")
    print(f"Successful:               {successful_count}")
    print(f"Failed:                   {failed_count}")
    print(f"Unknown:                   {unknown_count}")
    print(f"Payments at risk:         {payments_at_risk}")
    print(f"Total payment value:      {format_rupees(total_payment_value)}")
    print(f"Revenue at risk:          {format_rupees(total_revenue_at_risk)}")
    print(f"Recovery cases created:   {cases_created}")
    print("==================================================")

    client.close()

if __name__ == "__main__":
    asyncio.run(analyze_batch())
