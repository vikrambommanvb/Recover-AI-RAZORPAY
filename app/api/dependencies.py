from app.db.mongodb import get_database
from app.services.ai_service import get_ai_provider, AIProvider
from app.guardrails.policy_engine import PolicyEngine
from app.services.razorpay_service import RazorpayService

# Exporting dependencies for easy import
get_db = get_database


def get_policy_engine() -> PolicyEngine:
    """Dependency injection provider for the deterministic PolicyEngine."""
    return PolicyEngine()


def get_razorpay_service() -> RazorpayService:
    """Dependency injection provider for the Razorpay service."""
    return RazorpayService()

