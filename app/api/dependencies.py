from app.db.mongodb import get_database
from app.services.ai_service import get_ai_provider, AIProvider
from app.guardrails.policy_engine import PolicyEngine
from app.services.razorpay_service import RazorpayService

# Exporting dependencies for easy import
get_db = get_database


from fastapi import Request

def get_policy_engine() -> PolicyEngine:
    """Dependency injection provider for the deterministic PolicyEngine."""
    return PolicyEngine()


def get_razorpay_service() -> RazorpayService:
    """Dependency injection provider for the Razorpay service."""
    return RazorpayService()


def get_razorpay_client(request: Request = None):
    """Dependency injection provider for the Razorpay client."""
    if request and hasattr(request, "app") and request.app:
        overrides = request.app.dependency_overrides
        if get_razorpay_client in overrides:
            return overrides[get_razorpay_client]()
        if get_razorpay_service in overrides:
            return overrides[get_razorpay_service]()
    return get_razorpay_service()

