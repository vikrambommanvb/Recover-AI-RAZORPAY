import argparse
import asyncio
import os
import sys
import random
from datetime import datetime, timedelta, timezone

# Add root folder to python path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.db.collections import PAYMENTS_COLLECTION

def generate_synthetic_payments(count: int, seed: int):
    """Generate deterministic synthetic payments with realistic history context."""
    random.seed(seed)
    
    # 20 distinct synthetic customer IDs
    customers = [f"cust_syn_{100 + i}" for i in range(1, 21)]
    
    # Category definition
    statuses_and_reasons = [
        ("captured", None, "SUCCESS"),
        ("failed", "Gateway response timeout / connection lost", "BANK_TIMEOUT"),
        ("failed", "Insufficient balance in customer account", "INSUFFICIENT_FUNDS"),
        ("failed", "Card was declined by issuing bank", "DECLINED"),
        ("failed", "Unknown payment gateway error response code 999", "UNKNOWN")
    ]
    
    # Target distribution:
    # SUCCESS: 60%
    # BANK_TIMEOUT: 10%
    # INSUFFICIENT_FUNDS: 15%
    # DECLINED: 10%
    # UNKNOWN: 5%
    weights = [0.60, 0.10, 0.15, 0.10, 0.05]
    
    typical_amounts = [
        9900,      # ₹99.00
        19900,     # ₹199.00
        249900,    # ₹2,499.00
        499900,    # ₹4,999.00
        125000,    # ₹1,250.00
        59900,     # ₹599.00
        15000,     # ₹150.00
        1000000,   # ₹10,000.00
        15000000,  # ₹1,50,000.00
    ]
    typical_weights = [0.15, 0.20, 0.25, 0.10, 0.10, 0.10, 0.05, 0.04, 0.01]

    payments = []
    # Spreading over the last 30 days
    base_time = datetime.now(timezone.utc) - timedelta(days=30)
    
    for i in range(count):
        customer_id = random.choice(customers)
        status, failure_reason, category = random.choices(statuses_and_reasons, weights=weights, k=1)[0]
        amount = random.choices(typical_amounts, weights=typical_weights, k=1)[0]
        
        # Time spread
        created_at = base_time + timedelta(
            seconds=random.randint(0, 30 * 24 * 3600)
        )
        # Ensure updated_at is slightly after created_at
        updated_at = created_at + timedelta(seconds=random.randint(5, 60))
        
        payment = {
            "amount": amount,
            "currency": "INR",
            "status": status,
            "failure_reason": failure_reason,
            "customer_id": customer_id,
            "created_at": created_at,
            "updated_at": updated_at,
            "metadata": {
                "is_synthetic": True,
                "category": category,
                "notes": f"Generated test synthetic payment for category {category}."
            }
        }
        payments.append(payment)
        
    # Sort payments by created_at to preserve chronologically ordered history
    payments.sort(key=lambda p: p["created_at"])
    
    # Assign chronological IDs
    for index, payment in enumerate(payments):
        payment["payment_id"] = f"pay_syn_{index+1:03d}"
        payment["order_id"] = f"order_syn_{index+1:03d}"
        
    return payments

async def seed_data(count: int, seed: int, confirm: bool):
    """Seeds synthetic payments into the MongoDB collection."""
    if not settings.MONGODB_URI:
        print("Error: MONGODB_URI environment variable is missing. Cannot seed data.")
        sys.exit(1)

    payments = generate_synthetic_payments(count, seed)

    if not confirm:
        print(f"Dry run complete. Use 'python scripts/seed_data.py --confirm' to write to MongoDB.")
        print(f"Would write {len(payments)} records with seed={seed} to collection '{PAYMENTS_COLLECTION}'.")
        # Print a small breakdown
        categories = {}
        for p in payments:
            cat = p["metadata"]["category"]
            categories[cat] = categories.get(cat, 0) + 1
        print("Distribution breakdown:")
        for cat, cnt in categories.items():
            print(f"  {cat}: {cnt} ({cnt/len(payments)*100:.1f}%)")
        return

    print(f"Connecting to MongoDB at: {settings.MONGODB_URI}")
    client_kwargs = {}
    try:
        import certifi
        client_kwargs["tlsCAFile"] = certifi.where()
    except ImportError:
        client_kwargs["tlsAllowInvalidCertificates"] = True

    client = AsyncIOMotorClient(settings.MONGODB_URI, **client_kwargs)
    db = client[settings.MONGODB_DATABASE]
    collection = db[PAYMENTS_COLLECTION]

    print("Cleaning existing synthetic test records...")
    result = await collection.delete_many({"metadata.is_synthetic": True})
    print(f"Deleted {result.deleted_count} existing synthetic records.")

    print(f"Inserting {len(payments)} synthetic records...")
    result = await collection.insert_many(payments)
    print(f"Successfully seeded database with {len(result.inserted_ids)} records.")
    
    client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed database with synthetic payment records.")
    parser.add_argument("--confirm", action="store_true", help="Confirm write to MongoDB")
    parser.add_argument("--seed", type=int, default=42, help="Seed value for reproducible random generation")
    parser.add_argument("--count", type=int, default=500, help="Number of synthetic payment records to generate")
    args = parser.parse_args()

    asyncio.run(seed_data(args.count, args.seed, args.confirm))
