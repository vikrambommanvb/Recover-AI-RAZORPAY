from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from app.api.dependencies import get_db
from app.models.payment import Payment
from app.services.payment_service import PaymentService

router = APIRouter()

@router.get("/", response_model=List[Payment])
async def list_payments(
    limit: int = 100,
    offset: int = 0,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get a list of stored payment records.
    Monetary amounts are represented in minor units (paise).
    """
    try:
        return await PaymentService.list_payments(db, limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )

@router.get("/{payment_id}", response_model=Payment)
async def get_payment(
    payment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get a specific payment record by its unique identifier.
    Monetary amounts are represented in minor units (paise).
    """
    try:
        payment = await PaymentService.get_payment_by_id(db, payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment with ID '{payment_id}' not found."
            )
        return payment
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )
