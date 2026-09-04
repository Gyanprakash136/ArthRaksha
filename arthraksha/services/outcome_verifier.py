"""
ArthRaksha — Outcome Verifier
================================
Implements IOutcomeVerifier.
Independently verifies payment/action outcomes to confirm success/failure.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from interfaces import IOutcomeVerifier
from config.settings import settings

logger = logging.getLogger(__name__)

class OutcomeVerifier(IOutcomeVerifier):
    """
    Simulates outcome verification.
    In production, this would poll Razorpay API or listen for webhooks.
    """
    def __init__(self, mode: str = "simulation"):
        self.mode = mode

    def verify_payment(self, payment_id: str) -> dict:
        """
        Verify the status of a specific payment.
        For simulation, we just assume success if payment_id starts with 'pay_success'.
        """
        if self.mode == "simulation":
            is_success = "success" in payment_id or "retry_" in payment_id
            status = "captured" if is_success else "failed"
            logger.info(f"[VERIFIER] Payment {payment_id} verified as: {status}")
            return {
                "verified": True,
                "status": status,
                "amount": 500.0, # Dummy
                "currency": "INR"
            }
        
        # Production: call Razorpay API
        raise NotImplementedError("Live verification not implemented for hackathon.")

    def verify_subscription(self, subscription_id: str) -> dict:
        """
        Verify subscription state.
        """
        if self.mode == "simulation":
            is_active = "active" in subscription_id
            status = "active" if is_active else "halted"
            logger.info(f"[VERIFIER] Subscription {subscription_id} verified as: {status}")
            return {
                "verified": True,
                "status": status
            }
            
        raise NotImplementedError("Live verification not implemented for hackathon.")

# Global instance
outcome_verifier = OutcomeVerifier()
