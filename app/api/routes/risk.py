from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from pydantic import BaseModel, Field
from app.api.dependencies import get_db
from app.models.recovery import RecoveryCase
from app.services.risk_service import RiskService

router = APIRouter()

class RiskAnalysisResponse(BaseModel):
    payment_id: str = Field(..., description="Reference to the analyzed payment")
    risk_status: str = Field(..., description="Determined risk status (e.g. AT_RISK, NOT_AT_RISK, UNKNOWN)")
    amount_at_risk: int = Field(..., description="Amount at risk in minor units (paise)")
    root_cause: Optional[str] = Field(None, description="Classified root cause for payment failure")
    recovery_case_id: str = Field(..., description="Unique case identifier generated for recovery tracking")

@router.post("/analyze/{payment_id}", response_model=RiskAnalysisResponse)
async def analyze_payment_risk(
    payment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Analyzes a specific payment, calculates revenue risk, classifies root cause,
    and creates/returns an idempotent recovery case.
    Monetary amounts are represented in minor units (paise).
    """
    try:
        case = await RiskService.analyze_payment(db, payment_id)
        return RiskAnalysisResponse(
            payment_id=case.payment_id,
            risk_status=case.risk_status,
            amount_at_risk=case.amount_at_risk,
            root_cause=case.root_cause,
            recovery_case_id=case.case_id
        )
    except ValueError as e:
        # Payment not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk analysis failed: {str(e)}"
        )

@router.get("/cases", response_model=List[RecoveryCase])
async def list_cases(
    limit: int = 100,
    offset: int = 0,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    List all generated recovery cases.
    Monetary amounts are represented in minor units (paise).
    """
    try:
        return await RiskService.list_recovery_cases(db, limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )

@router.get("/cases/{case_id}", response_model=RecoveryCase)
async def get_case(
    case_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get details of a specific recovery case by its case_id.
    Monetary amounts are represented in minor units (paise).
    """
    try:
        case = await RiskService.get_recovery_case_by_id(db, case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recovery case with ID '{case_id}' not found."
            )
        return case
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )
