import httpx
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.logging import logger


class RazorpayService:
    """
    Razorpay integration service for executing transactions in TEST MODE only.
    All communication is isolated via HTTP Basic Auth.
    """
    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.base_url = "https://api.razorpay.com/v1"
        
        # Enforce TEST MODE credentials exclusively
        if self.key_id:
            # Rejects live credentials
            if self.key_id.startswith("rzp_live_"):
                raise ValueError(
                    "Security Exception: Razorpay LIVE mode key detected. "
                    "Only TEST mode keys (rzp_test_...) are allowed."
                )
            if not self.key_id.startswith("rzp_test_"):
                raise ValueError(
                    "Configuration Error: Invalid Razorpay API Key prefix. "
                    "Expected 'rzp_test_'."
                )

    def _get_auth(self) -> tuple[str, str]:
        if not self.key_id or not self.key_secret:
            raise ValueError("Configuration Error: Razorpay credentials are missing or unconfigured.")
        return (self.key_id, self.key_secret)

    async def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        """Fetch payment details from Razorpay Payments API."""
        auth = self._get_auth()
        async with httpx.AsyncClient(timeout=5.0) as client:
            logger.info(f"Razorpay API Call: GET /payments/{payment_id}")
            response = await client.get(
                f"{self.base_url}/payments/{payment_id}",
                auth=auth
            )
            if response.status_code != 200:
                logger.error(f"Razorpay GET payment failed: {response.text}")
                response.raise_for_status()
            return response.json()

    async def fetch_order(self, order_id: str) -> Dict[str, Any]:
        """Fetch order details from Razorpay Orders API."""
        auth = self._get_auth()
        async with httpx.AsyncClient(timeout=5.0) as client:
            logger.info(f"Razorpay API Call: GET /orders/{order_id}")
            response = await client.get(
                f"{self.base_url}/orders/{order_id}",
                auth=auth
            )
            if response.status_code != 200:
                logger.error(f"Razorpay GET order failed: {response.text}")
                response.raise_for_status()
            return response.json()

    async def create_order(self, amount: int, currency: str, receipt: str) -> Dict[str, Any]:
        """Create a recovery transaction order in Razorpay."""
        auth = self._get_auth()
        async with httpx.AsyncClient(timeout=5.0) as client:
            logger.info(f"Razorpay API Call: POST /orders (amount={amount}, receipt={receipt})")
            payload = {
                "amount": amount,
                "currency": currency,
                "receipt": receipt
            }
            response = await client.post(
                f"{self.base_url}/orders",
                json=payload,
                auth=auth
            )
            if response.status_code != 200:
                logger.error(f"Razorpay POST order failed: {response.text}")
                response.raise_for_status()
            return response.json()

    async def capture_payment(self, payment_id: str, amount: int, currency: str) -> Dict[str, Any]:
        """Capture an authorized payment to complete recovery."""
        auth = self._get_auth()
        async with httpx.AsyncClient(timeout=5.0) as client:
            logger.info(f"Razorpay API Call: POST /payments/{payment_id}/capture (amount={amount})")
            payload = {
                "amount": amount,
                "currency": currency
            }
            response = await client.post(
                f"{self.base_url}/payments/{payment_id}/capture",
                json=payload,
                auth=auth
            )
            if response.status_code != 200:
                logger.error(f"Razorpay POST capture failed: {response.text}")
                response.raise_for_status()
            return response.json()


class MockRazorpayService(RazorpayService):
    """
    Mock implementation of RazorpayService for offline and automated tests.
    Does not initiate actual network traffic.
    """
    def __init__(self, key_id: Optional[str] = "rzp_test_mockkey", key_secret: Optional[str] = "mocksecret"):
        # Explicitly pass mock test mode key so validation passes
        super().__init__(key_id, key_secret)
        self.simulated_behavior = "SUCCESS"  # SUCCESS, TIMEOUT, API_ERROR, ALREADY_CAPTURED, INVALID_RESPONSE

    async def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        if self.simulated_behavior == "TIMEOUT":
            import asyncio
            raise asyncio.TimeoutError("Simulated API request timeout.")
        elif self.simulated_behavior == "API_ERROR":
            response = httpx.Response(status_code=400, json={"error": {"description": "Simulated Gateway Error"}})
            raise httpx.HTTPStatusError("Bad Request", request=httpx.Request("GET", "url"), response=response)
        elif self.simulated_behavior == "ALREADY_CAPTURED" or payment_id == "pay_captured_123":
            return {
                "id": payment_id,
                "entity": "payment",
                "amount": 50000,
                "currency": "INR",
                "status": "captured",
                "order_id": "order_mock_captured"
            }
        elif payment_id == "pay_authorized_123":
            return {
                "id": payment_id,
                "entity": "payment",
                "amount": 50000,
                "currency": "INR",
                "status": "authorized",
                "order_id": "order_mock_auth"
            }
        
        # Default mock returns a failed payment state
        return {
            "id": payment_id,
            "entity": "payment",
            "amount": 50000,
            "currency": "INR",
            "status": "failed",
            "order_id": "order_mock_failed",
            "error_description": "Payment was declined by issuer bank."
        }

    async def fetch_order(self, order_id: str) -> Dict[str, Any]:
        if self.simulated_behavior == "TIMEOUT":
            import asyncio
            raise asyncio.TimeoutError("Simulated API request timeout.")
        return {
            "id": order_id,
            "entity": "order",
            "amount": 50000,
            "currency": "INR",
            "receipt": "receipt_mock",
            "status": "created"
        }

    async def create_order(self, amount: int, currency: str, receipt: str) -> Dict[str, Any]:
        if self.simulated_behavior == "TIMEOUT":
            import asyncio
            raise asyncio.TimeoutError("Simulated API request timeout.")
        elif self.simulated_behavior == "API_ERROR":
            response = httpx.Response(status_code=400, json={"error": {"description": "Simulated Order Error"}})
            raise httpx.HTTPStatusError("Bad Request", request=httpx.Request("POST", "url"), response=response)
            
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
            response = httpx.Response(status_code=400, json={"error": {"description": "Capture declined"}})
            raise httpx.HTTPStatusError("Bad Request", request=httpx.Request("POST", "url"), response=response)
            
        return {
            "id": payment_id,
            "entity": "payment",
            "amount": amount,
            "currency": currency,
            "status": "captured",
            "order_id": "order_mock_captured"
        }
