from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class WebhookEvent(BaseModel):
    """
    WebhookEvent Model.
    Tracks received webhook events to prevent duplicate processing.
    """
    event_id: str = Field(..., description="Unique event identifier from Razorpay, e.g. evt_XYZ")
    event_type: str = Field(..., description="Razorpay webhook event type, e.g. payment.captured")
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = Field(None, description="Timestamp of when the event finished processing")
    processing_status: str = Field("PENDING", description="Status of webhook processing: PENDING, PROCESSED, FAILED")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Raw JSON payload received")
