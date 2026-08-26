class RootCauseClassifier:
    """
    Classifies payment failures into deterministic root cause categories
    based on failure reasons and metadata.
    """
    @staticmethod
    def classify(failure_reason: str) -> str:
        reason = (failure_reason or "").upper()
        
        if any(kw in reason for kw in ["TEMPORARY", "PROVIDER", "THROTTLE", "GATEWAY_DOWN"]):
            return "TEMPORARY_PROVIDER_FAILURE"
        elif any(kw in reason for kw in ["TIMEOUT", "CONNECTION", "NETWORK", "GATEWAY"]):
            return "NETWORK_TIMEOUT"
        elif any(kw in reason for kw in ["DECLINE", "EXPIRED", "CARD", "ISSUER", "BLOCKED"]):
            return "BANK_DECLINE"
        elif any(kw in reason for kw in ["INSUFFICIENT", "BALANCE", "FUNDS", "LIMIT"]):
            return "INSUFFICIENT_FUNDS"
        elif any(kw in reason for kw in ["AUTH", "OTP", "VERIFICATION", "SIGNATURE", "PASSWORD"]):
            return "AUTHENTICATION_FAILURE"
        elif any(kw in reason for kw in ["ABANDON", "CANCEL", "CLOSE"]):
            return "CUSTOMER_ABANDONMENT"
        else:
            return "UNKNOWN"
