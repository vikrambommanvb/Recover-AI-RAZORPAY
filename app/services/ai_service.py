from abc import ABC, abstractmethod
import json
from app.core.config import settings
from app.core.logging import logger
from app.ai.schemas import AIServiceRequest, AIServiceResponse
from app.models.agent_decision import RecoveryAction


class AIProvider(ABC):
    """Abstract Base Class defining the interface for all AI engines."""

    @abstractmethod
    async def analyze_payment_failure(self, request: AIServiceRequest) -> AIServiceResponse:
        """
        Analyze a failed payment and return a recovery recommendation.
        
        Raises ValueError if required configurations/credentials are missing.
        """
        pass


class GroqProvider(AIProvider):
    """Groq implementation of the AIProvider interface."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy initializer for AsyncGroq client to avoid startup dependency checks."""
        if not self._client:
            # This raises ValueError if GROQ_API_KEY is missing
            api_key = settings.check_groq_config()
            try:
                from groq import AsyncGroq
                self._client = AsyncGroq(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "The 'groq' package is not installed. Please install it using pip install groq."
                )
        return self._client

    async def analyze_payment_failure(self, request: AIServiceRequest) -> AIServiceResponse:
        client = self._get_client()
        
        system_prompt = (
            "You are RecoverAI, a backend AI specialist diagnosing failed transactions for Razorpay payments.\n"
            "Analyze the payment failure data and return a JSON object with the following fields:\n"
            "- action: Must be one of: RETRY, REMIND, ESCALATE, STOP, NO_ACTION\n"
            "- confidence: A float between 0.0 and 1.0 representing your confidence\n"
            "- reason: A concise explanation of your choice\n"
            "- root_cause: Concise root cause diagnosis of the failure\n"
            "- risk_factors: A list of strings identifying potential risks (e.g., 'repeated_timeout', 'high_amount')\n"
            "Do not include any markdown styling, conversational text, or wrapper, return ONLY valid raw JSON."
        )

        user_content = (
            f"Payment ID: {request.payment_id}\n"
            f"Amount at risk: {request.amount} paise\n"
            f"Currency: {request.currency}\n"
            f"Gateway Failure Reason: {request.failure_reason}\n"
            f"Customer ID: {request.customer_id}\n"
            f"Metadata: {json.dumps(request.metadata)}"
        )

        try:
            logger.info(f"Sending request to Groq using model: {settings.GROQ_MODEL}")
            chat_completion = await client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                model=settings.GROQ_MODEL,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            response_text = chat_completion.choices[0].message.content
            logger.debug(f"Groq Raw Response: {response_text}")
            
            data = json.loads(response_text)
            return AIServiceResponse(**data)
            
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            raise RuntimeError(f"AI Service Failure: {str(e)}")


class MockAIProvider(AIProvider):
    """Mock implementation of AIProvider for local development, testing, and offline mode."""

    async def analyze_payment_failure(self, request: AIServiceRequest) -> AIServiceResponse:
        reason = request.failure_reason.lower()
        
        if "timeout" in reason or "network" in reason:
            action = RecoveryAction.RETRY
            root_cause = "Transient bank network issue / gateway timeout"
            confidence = 0.85
            risk_factors = ["gateway_instability"]
        elif "balance" in reason or "insufficient" in reason:
            action = RecoveryAction.REMIND
            root_cause = "Insufficient customer account balance"
            confidence = 0.90
            risk_factors = ["low_funds"]
        elif "fraud" in reason or "stolen" in reason or "suspected" in reason:
            action = RecoveryAction.STOP
            root_cause = "High-risk fraud detection/security check failed"
            confidence = 0.95
            risk_factors = ["fraud_risk"]
        elif "expired" in reason:
            action = RecoveryAction.ESCALATE
            root_cause = "Expired card credentials"
            confidence = 0.80
            risk_factors = ["expired_instrument"]
        else:
            action = RecoveryAction.NO_ACTION
            root_cause = "Unidentifiable client/gateway error"
            confidence = 0.50
            risk_factors = ["unknown_origin"]

        return AIServiceResponse(
            action=action,
            confidence=confidence,
            reason=f"Mock diagnosis for failure reason: '{request.failure_reason}'",
            root_cause=root_cause,
            risk_factors=risk_factors
        )


def get_ai_provider() -> AIProvider:
    """Factory function to retrieve the configured AI provider."""
    provider_name = settings.AI_PROVIDER.lower()
    
    if provider_name == "groq":
        return GroqProvider()
    elif provider_name == "mock":
        return MockAIProvider()
    else:
        raise ValueError(
            f"Unsupported AI provider: {settings.AI_PROVIDER}. Supported options: groq, mock"
        )
