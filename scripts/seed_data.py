import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add root folder to python path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.db.collections import PAYMENTS_COLLECTION

# Synthetic payment records
SYNTHETIC_PAYMENTS = [
    {
        "payment_id": "pay_syn_001",
        "order_id": "order_syn_001",
        "amount": 249900,  # ₹2,499.00
        "currency": "INR",
        "status": "captured",
        "failure_reason": None,
        "customer_id": "cust_syn_101",
        "created_at": datetime.utcnow() - timedelta(days=2),
        "updated_at": datetime.utcnow() - timedelta(days=2),
        "metadata": {
            "is_synthetic": True,
            "category": "successful",
            "notes": "Test synthetic data representing a successful payment."
        }
    },
    {
        "payment_id": "pay_syn_002",
        "order_id": "order_syn_002",
        "amount": 59900,  # ₹599.00
        "currency": "INR",
        "status": "failed",
        "failure_reason": "Gateway response timeout / connection lost",
        "customer_id": "cust_syn_102",
        "created_at": datetime.utcnow() - timedelta(hours=6),
        "updated_at": datetime.utcnow() - timedelta(hours=6),
        "metadata": {
            "is_synthetic": True,
            "category": "bank_timeout",
            "notes": "Test synthetic data representing a transient gateway timeout."
        }
    },
    {
        "payment_id": "pay_syn_003",
        "order_id": "order_syn_003",
        "amount": 125000,  # ₹1,250.00
        "currency": "INR",
        "status": "failed",
        "failure_reason": "Insufficient balance in customer account",
        "customer_id": "cust_syn_103",
        "created_at": datetime.utcnow() - timedelta(hours=4),
        "updated_at": datetime.utcnow() - timedelta(hours=4),
        "metadata": {
            "is_synthetic": True,
            "category": "insufficient_funds",
            "notes": "Test synthetic data representing insufficient balance."
        }
    },
    {
        "payment_id": "pay_syn_004",
        "order_id": "order_syn_004",
        "amount": 499900,  # ₹4,999.00
        "currency": "INR",
        "status": "failed",
        "failure_reason": "Card was declined by issuing bank",
        "customer_id": "cust_syn_104",
        "created_at": datetime.utcnow() - timedelta(hours=2),
        "updated_at": datetime.utcnow() - timedelta(hours=2),
        "metadata": {
            "is_synthetic": True,
            "category": "declined",
            "notes": "Test synthetic data representing a declined transaction."
        }
    },
    {
        "payment_id": "pay_syn_005",
        "order_id": "order_syn_005",
        "amount": 15000,  # ₹150.00
        "currency": "INR",
        "status": "failed",
        "failure_reason": "Unknown payment gateway error response code 999",
        "customer_id": "cust_syn_105",
        "created_at": datetime.utcnow() - timedelta(minutes=30),
        "updated_at": datetime.utcnow() - timedelta(minutes=30),
        "metadata": {
            "is_synthetic": True,
            "category": "unknown_status",
            "notes": "Test synthetic data representing an unidentifiable error."
        }
    }
]

async def seed_data():
    """Seeds synthetic payments into the MongoDB collection."""
    if not settings.MONGODB_URI:
        print("Error: MONGODB_URI environment variable is missing. Cannot seed data.")
        sys.exit(1)

    print(f"Connecting to MongoDB at: {settings.MONGODB_URI}")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    collection = db[PAYMENTS_COLLECTION]

    print("Cleaning existing synthetic test records...")
    # Delete only synthetic records to avoid touching actual data
    result = await collection.delete_many({"metadata.is_synthetic": True})
    print(f"Deleted {result.deleted_count} existing synthetic records.")

    print(f"Inserting {len(SYNTHETIC_PAYMENTS)} synthetic records...")
    result = await collection.insert_many(SYNTHETIC_PAYMENTS)
    print(f"Successfully seeded database with IDs: {result.inserted_ids}")
    
    client.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--confirm":
        asyncio.run(seed_data())
    else:
        print("Dry run complete. Use 'python scripts/seed_data.py --confirm' to write to MongoDB.")
        print(f"Would write {len(SYNTHETIC_PAYMENTS)} records to collection '{PAYMENTS_COLLECTION}'.")
