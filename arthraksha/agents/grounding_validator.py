"""
ArthRaksha — Grounding Validator
===================================
Implements IGroundingValidator.
Validates the semantic correctness of agent's proposed action against evidence.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from interfaces import IGroundingValidator, GroundingResult

logger = logging.getLogger(__name__)

class GroundingValidator(IGroundingValidator):
    """
    Ensures agent decisions are grounded in factual evidence.
    """
    def validate(
        self,
        proposed_action: str,
        evidence:        list[str],
        observations:    list[dict],
        policy_context:  dict,
    ) -> GroundingResult:
        """
        Check if the action is supported by evidence.
        """
        issues = []
        
        # 1. Action matches evidence?
        # e.g., if error is "insufficient_funds", auto_retry immediately is usually bad without backoff.
        # This can be expanded with LLM validation or regex checks.
        has_fraud_evidence = any("fraud" in e.lower() or "risk" in e.lower() for e in evidence)
        if has_fraud_evidence and proposed_action != "escalate_to_human":
            issues.append(f"Fraud evidence present, but proposed action is '{proposed_action}'. Must escalate.")

        # 2. Claim supported by observations?
        # Ensure we are not retrying a payment that was already verified as successful.
        has_success_obs = any(obs.get("status") == "captured" for obs in observations)
        if has_success_obs and proposed_action in ["auto_retry", "payment_link"]:
            issues.append("Observation indicates payment already captured. Cannot retry.")

        if issues:
            logger.warning(f"[GROUNDING] Validation failed for action '{proposed_action}': {issues}")
            # If multiple grounding failures, might trigger HITL later.
            return GroundingResult(
                is_grounded=False,
                issues=issues,
                evidence=evidence,
                action="reject"
            )

        logger.debug(f"[GROUNDING] Action '{proposed_action}' is grounded.")
        return GroundingResult(
            is_grounded=True,
            evidence=evidence,
            action="continue"
        )

# Global instance
grounding_validator = GroundingValidator()
