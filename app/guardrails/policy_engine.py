from abc import ABC, abstractmethod
from enum import Enum
from typing import List
from pydantic import BaseModel, Field
from app.models.payment import Payment
from app.models.agent_decision import AgentDecision, RecoveryAction


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class GuardrailResponse(BaseModel):
    """Result of deterministic policy engine evaluation."""
    decision: PolicyDecision = Field(..., description="Engine result: ALLOW, BLOCK, ESCALATE")
    reason: str = Field(..., description="Summary explanation of the decision")
    rules_checked: List[str] = Field(default_factory=list, description="List of all rule names evaluated")
    triggered_rules: List[str] = Field(default_factory=list, description="List of rule names triggered")


class PolicyRule(ABC):
    """Abstract base class for all deterministic policy rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def evaluate(self, payment: Payment, decision: AgentDecision) -> PolicyDecision:
        """
        Evaluate the rule. Returns a PolicyDecision.
        """
        pass


class MaxAmountRule(PolicyRule):
    """Escalate recovery actions if the payment amount exceeds a threshold."""

    def __init__(self, max_amount_paise: int = 10000000):  # Default ₹1,00,000 (10,000,000 paise)
        self.max_amount_paise = max_amount_paise

    @property
    def name(self) -> str:
        return "MAX_AMOUNT_LIMIT"

    def evaluate(self, payment: Payment, decision: AgentDecision) -> PolicyDecision:
        if payment.amount > self.max_amount_paise:
            # High risk financial transaction, escalate for human approval
            return PolicyDecision.ESCALATE
        return PolicyDecision.ALLOW


class MinConfidenceRule(PolicyRule):
    """Block or Escalate actions if the AI agent's confidence score is too low."""

    def __init__(self, min_confidence: float = 0.60, action: PolicyDecision = PolicyDecision.BLOCK):
        self.min_confidence = min_confidence
        self.action = action

    @property
    def name(self) -> str:
        return "MIN_CONFIDENCE_THRESHOLD"

    def evaluate(self, payment: Payment, decision: AgentDecision) -> PolicyDecision:
        if decision.confidence < self.min_confidence:
            return self.action
        return PolicyDecision.ALLOW


class PaymentStatusRule(PolicyRule):
    """Block actions if the payment status is successful or unknown."""

    @property
    def name(self) -> str:
        return "PAYMENT_STATUS_CHECK"

    def evaluate(self, payment: Payment, decision: AgentDecision) -> PolicyDecision:
        status = payment.status.lower() if payment.status else ""
        
        # Prevent actions on already successful payments
        if status in ["captured", "authorized", "successful", "success"]:
            if decision.action in [RecoveryAction.RETRY, RecoveryAction.REMIND]:
                return PolicyDecision.BLOCK
                
        # Prevent retry or remind if status is unknown/empty
        elif status in ["unknown", ""]:
            if decision.action in [RecoveryAction.RETRY, RecoveryAction.REMIND]:
                return PolicyDecision.BLOCK
                
        return PolicyDecision.ALLOW


class RetryLimitRule(PolicyRule):
    """Block retry actions if the retry count exceeds the limit."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    @property
    def name(self) -> str:
        return "RETRY_LIMIT_CHECK"

    def evaluate(self, payment: Payment, decision: AgentDecision) -> PolicyDecision:
        if decision.action == RecoveryAction.RETRY:
            retry_count = payment.metadata.get("retry_count", 0)
            if retry_count >= self.max_retries:
                return PolicyDecision.BLOCK
        return PolicyDecision.ALLOW


class EscalationRule(PolicyRule):
    """Escalate if the AI recommends ESCALATE."""

    @property
    def name(self) -> str:
        return "AI_RECOMMENDED_ESCALATION"

    def evaluate(self, payment: Payment, decision: AgentDecision) -> PolicyDecision:
        if decision.action == RecoveryAction.ESCALATE:
            return PolicyDecision.ESCALATE
        return PolicyDecision.ALLOW


class PolicyEngine:
    """
    Deterministic Guardrail Policy Engine.
    
    Verifies AI agent decisions against hard-coded business safety policies 
    before authorizing any payment system operations.
    """
    
    def __init__(self, rules: List[PolicyRule] = None):
        if rules is None:
            # Register default safety rules
            self.rules = [
                MaxAmountRule(),
                MinConfidenceRule(),
                PaymentStatusRule(),
                RetryLimitRule(),
                EscalationRule()
            ]
        else:
            self.rules = rules

    def evaluate(self, payment: Payment, decision: AgentDecision) -> GuardrailResponse:
        triggered = []
        checked = []
        final_decision = PolicyDecision.ALLOW

        for rule in self.rules:
            checked.append(rule.name)
            rule_decision = rule.evaluate(payment, decision)
            if rule_decision != PolicyDecision.ALLOW:
                triggered.append(rule.name)
                # Escalate overrides Block, Block overrides Allow
                if rule_decision == PolicyDecision.ESCALATE:
                    final_decision = PolicyDecision.ESCALATE
                elif rule_decision == PolicyDecision.BLOCK and final_decision != PolicyDecision.ESCALATE:
                    final_decision = PolicyDecision.BLOCK

        if final_decision == PolicyDecision.ESCALATE:
            reason = f"Decision escalated by guardrail rules: {', '.join(triggered)}"
        elif final_decision == PolicyDecision.BLOCK:
            reason = f"Decision blocked by guardrail rules: {', '.join(triggered)}"
        else:
            reason = "Decision allowed by all guardrail rules"

        return GuardrailResponse(
            decision=final_decision,
            reason=reason,
            rules_checked=checked,
            triggered_rules=triggered
        )

