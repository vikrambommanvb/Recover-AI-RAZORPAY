from datetime import datetime, timezone
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator


class Payment(BaseModel):
    """
    Payment Model.
    
    Design Decision: Financial amounts (amount) are represented as integers 
    in minor units (paise for INR) to prevent floating-point calculation errors.
    Example: ₹2,499.50 is represented as 249950 paise.
    """
    payment_id: str = Field(..., description="Unique identifier for the payment, e.g. pay_XYZ")
    order_id: Optional[str] = Field(None, description="Optional unique identifier for the order, e.g. order_XYZ")
    amount: int = Field(..., gt=0, description="Amount in minor units (e.g. paise for INR). Must be positive.")
    currency: str = Field("INR", min_length=3, max_length=3, description="3-letter ISO currency code")
    status: str = Field(..., description="Status of the payment, e.g. successful, failed, processing")
    failure_reason: Optional[str] = Field(None, description="Reason for the failure if status is failed")
    customer_id: Optional[str] = Field(None, description="Identifier for the customer")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of payment creation")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of last update")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary for additional payload details")

    @field_validator("currency")
    @classmethod
    def validate_currency_uppercase(cls, value: str) -> str:
        return value.upper()
