from datetime import datetime
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.payment import Payment
from app.db.collections import PAYMENTS_COLLECTION

class PaymentService:
    @staticmethod
    async def get_payment_by_id(db: AsyncIOMotorDatabase, payment_id: str) -> Optional[Payment]:
        """Retrieve a payment record by its unique payment_id."""
        doc = await db[PAYMENTS_COLLECTION].find_one({"payment_id": payment_id})
        if doc:
            return Payment(**doc)
        return None

    @staticmethod
    async def list_payments(db: AsyncIOMotorDatabase, limit: int = 100, offset: int = 0) -> List[Payment]:
        """List stored payments with limit and offset paging."""
        cursor = db[PAYMENTS_COLLECTION].find().skip(offset).limit(limit)
        payments = []
        async for doc in cursor:
            payments.append(Payment(**doc))
        return payments

    @staticmethod
    async def save_payment(db: AsyncIOMotorDatabase, payment: Payment) -> Payment:
        """Upsert a payment record into MongoDB."""
        payment_dict = payment.model_dump()
        await db[PAYMENTS_COLLECTION].update_one(
            {"payment_id": payment.payment_id},
            {"$set": payment_dict},
            upsert=True
        )
        return payment

    @staticmethod
    async def get_customer_history(db: AsyncIOMotorDatabase, customer_id: Optional[str], before_date: datetime) -> dict:
        """
        Aggregate customer payment history prior to the given timestamp.
        Returns a dict containing previous_payment_count, successful_payment_count, previous_failure_count.
        """
        if not customer_id:
            return {
                "previous_payment_count": 0,
                "successful_payment_count": 0,
                "previous_failure_count": 0
            }
            
        query = {
            "customer_id": customer_id,
            "created_at": {"$lt": before_date}
        }
        
        cursor = db[PAYMENTS_COLLECTION].find(query)
        total_count = 0
        success_count = 0
        failure_count = 0
        
        async for doc in cursor:
            total_count += 1
            status = str(doc.get("status", "")).lower()
            if status in ["captured", "authorized", "successful", "success"]:
                success_count += 1
            elif status in ["failed"]:
                failure_count += 1
                
        return {
            "previous_payment_count": total_count,
            "successful_payment_count": success_count,
            "previous_failure_count": failure_count
        }
