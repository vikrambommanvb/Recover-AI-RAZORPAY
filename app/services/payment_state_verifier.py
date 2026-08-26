from enum import Enum


class PaymentState(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"


class PaymentStateVerifier:
    @staticmethod
    def get_recovery_eligibility(status: str) -> tuple[bool, str]:
        """
        Determines if a payment is eligible for recovery actions based on its state.
        Returns: (is_eligible, reason)
        """
        status_upper = status.upper()
        if status_upper == PaymentState.CAPTURED:
            return False, "Payment is already captured. No recovery action required."
        elif status_upper == PaymentState.FAILED:
            return True, "Payment has failed and is eligible for recovery."
        elif status_upper == PaymentState.PENDING:
            return False, "Payment is pending/processing. Do not immediately recover."
        elif status_upper == PaymentState.REFUNDED:
            return False, "Payment has been refunded. No recovery possible."
        elif status_upper == PaymentState.AUTHORIZED:
            return True, "Payment is authorized. Verify whether capture/recovery is appropriate."
        elif status_upper == PaymentState.UNKNOWN:
            return False, "Payment state is unknown. Bypassed to prevent double capture."
        else:
            return False, f"Unsupported payment state: {status_upper}."
