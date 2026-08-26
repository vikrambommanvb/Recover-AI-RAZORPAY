import httpx
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.config import settings

logger = logging.getLogger("recoverai.razorpay_client")


class NormalizedPayment(BaseModel):
    """Normalized internal representation of a Razorpay payment transaction."""
    payment_id: str
    order_id: Optional[str] = None
    amount_minor: int
    currency: str
    status: str  # AUTHORIZED, CAPTURED, FAILED, REFUNDED, PENDING, UNKNOWN
    method: Optional[str] = None
    created_at: datetime
    captured: bool
    failure_reason: Optional[str] = None


class RazorpayClient:
    """
    Dedicated integration client for Razorpay API.
    Enforces Test Mode credentials exclusively.
    """
    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None, base_url: str = "https://api.razorpay.com/v1"):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.base_url = base_url

        # Bounded key protection checks
        if self.key_id:
            if self.key_id.startswith("rzp_live_"):
                raise ValueError("Security constraint validation: Live Mode credentials (rzp_live_) are strictly forbidden!")
            if not self.key_id.startswith("rzp_test_"):
                raise ValueError("Configuration Error: Invalid Razorpay API Key prefix. Expected 'rzp_test_'.")

    def _get_auth(self) -> tuple[str, str]:
        if not self.key_id or not self.key_secret:
            raise ValueError("Configuration Error: Razorpay credentials are missing or unconfigured.")
        return (self.key_id, self.key_secret)

    def _normalize_status(self, raw_status: str) -> str:
        if not raw_status:
            return "UNKNOWN"
        s = raw_status.upper()
        if s == "CAPTURED":
            return "CAPTURED"
        elif s == "AUTHORIZED":
            return "AUTHORIZED"
        elif s == "FAILED":
            return "FAILED"
        elif s in ["REFUNDED", "REFUND"]:
            return "REFUNDED"
        elif s in ["CREATED", "PENDING", "PROCESSING"]:
            return "PENDING"
        else:
            return "UNKNOWN"

    async def get_payment(self, payment_id: str) -> NormalizedPayment:
        """Fetch and normalize a payment from the gateway."""
        auth = self._get_auth()
        url = f"{self.base_url}/payments/{payment_id}"
        logger.info(f"Razorpay Client Request: GET {url}")

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, auth=auth)

            if response.status_code != 200:
                logger.error(f"Razorpay Client GET payment failed ({response.status_code}): {response.text}")
                response.raise_for_status()

            data = response.json()
            created_epoch = data.get("created_at")
            created_dt = (
                datetime.fromtimestamp(created_epoch, timezone.utc)
                if created_epoch else datetime.now(timezone.utc)
            )

            return NormalizedPayment(
                payment_id=data.get("id"),
                order_id=data.get("order_id"),
                amount_minor=data.get("amount"),
                currency=data.get("currency", "INR"),
                status=self._normalize_status(data.get("status", "")),
                method=data.get("method"),
                created_at=created_dt,
                captured=data.get("captured", False),
                failure_reason=data.get("error_description") or data.get("error_reason")
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTPStatusError on payment retrieval: {e}")
            raise e
        except httpx.RequestError as e:
            logger.error(f"RequestError on payment retrieval: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error retrieving payment: {e}")
            raise e

    async def create_order(self, amount: int, currency: str, receipt: str) -> Dict[str, Any]:
        """Create a transaction order in Razorpay."""
        auth = self._get_auth()
        url = f"{self.base_url}/orders"
        logger.info(f"Razorpay Client Request: POST {url} (amount={amount})")

        payload = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload, auth=auth)

            if response.status_code != 200:
                logger.error(f"Razorpay Client POST order failed ({response.status_code}): {response.text}")
                response.raise_for_status()

            return response.json()
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise e

    async def capture_payment(self, payment_id: str, amount: int, currency: str) -> Dict[str, Any]:
        """Capture an authorized payment to complete recovery."""
        auth = self._get_auth()
        url = f"{self.base_url}/payments/{payment_id}/capture"
        logger.info(f"Razorpay Client Request: POST {url}")

        payload = {
            "amount": amount,
            "currency": currency
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload, auth=auth)

            if response.status_code != 200:
                logger.error(f"Razorpay Client POST capture failed ({response.status_code}): {response.text}")
                response.raise_for_status()

            return response.json()
        except Exception as e:
            logger.error(f"Error capturing payment: {e}")
            raise e


class MockRazorpayClient(RazorpayClient):
    """
    Mock integration client for offline execution and tests.
    """
    def __init__(self, key_id: Optional[str] = "rzp_test_mockkey", key_secret: Optional[str] = "mocksecret"):
        super().__init__(key_id, key_secret)
        self.simulated_behavior = "SUCCESS"  # SUCCESS, TIMEOUT, API_ERROR, ALREADY_CAPTURED, REFUNDED, UNKNOWN

    async def get_payment(self, payment_id: str) -> NormalizedPayment:
        if self.simulated_behavior == "TIMEOUT":
            import asyncio
            raise asyncio.TimeoutError("Simulated API request timeout.")
        elif self.simulated_behavior == "API_ERROR":
            response = httpx.Response(status_code=400, json={"error": {"description": "Simulated connection error."}})
            raise httpx.HTTPStatusError("Bad Request", request=httpx.Request("GET", "url"), response=response)

        # Map state based on mock criteria
        if payment_id.startswith("pay_captured") or self.simulated_behavior == "ALREADY_CAPTURED":
            status = "CAPTURED"
            captured = True
        elif payment_id.startswith("pay_refunded") or self.simulated_behavior == "REFUNDED":
            status = "REFUNDED"
            captured = False
        elif payment_id.startswith("pay_authorized"):
            status = "AUTHORIZED"
            captured = False
        elif payment_id.startswith("pay_unknown") or self.simulated_behavior == "UNKNOWN":
            status = "UNKNOWN"
            captured = False
        elif payment_id.startswith("pay_pending"):
            status = "PENDING"
            captured = False
        else:
            status = "FAILED"
            captured = False

        return NormalizedPayment(
            payment_id=payment_id,
            order_id="order_mock_123",
            amount_minor=50000,
            currency="INR",
            status=status,
            method="card",
            created_at=datetime.now(timezone.utc),
            captured=captured,
            failure_reason="Issuer bank decline" if status == "FAILED" else None
        )

    async def create_order(self, amount: int, currency: str, receipt: str) -> Dict[str, Any]:
        if self.simulated_behavior == "TIMEOUT":
            import asyncio
            raise asyncio.TimeoutError("Simulated API request timeout.")
        elif self.simulated_behavior == "API_ERROR":
            response = httpx.Response(status_code=500, json={"error": {"description": "Internal server error"}})
            raise httpx.HTTPStatusError("Server Error", request=httpx.Request("POST", "url"), response=response)

        return {
            "id": f"order_rec_{receipt[:8]}",
            "entity": "order",
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "status": "created"
        }

    async def capture_payment(self, payment_id: str, amount: int, currency: str) -> Dict[str, Any]:
        if self.simulated_behavior == "TIMEOUT":
            import asyncio
            raise asyncio.TimeoutError("Simulated API request timeout.")
        elif self.simulated_behavior == "API_ERROR":
            response = httpx.Response(status_code=400, json={"error": {"description": "Capture failed"}})
            raise httpx.HTTPStatusError("Bad Request", request=httpx.Request("POST", "url"), response=response)

        return {
            "id": payment_id,
            "entity": "payment",
            "amount": amount,
            "currency": currency,
            "status": "captured",
            "order_id": "order_mock_captured"
        }


def get_razorpay_client() -> RazorpayClient:
    """Dependency injection provider for Razorpay client."""
    if settings.APP_MODE.lower() == "demo" or settings.AI_PROVIDER.lower() == "mock" or not settings.RAZORPAY_KEY_ID:
        return MockRazorpayClient()
    return RazorpayClient()
