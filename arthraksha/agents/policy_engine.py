"""
ArthRaksha — Policy Engine
=============================
Implements IPolicyEngine.
Agents propose, policy authorizes based on business rules.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from interfaces import IPolicyEngine, PolicyDecision

logger = logging.getLogger(__name__)

class PolicyEngine(IPolicyEngine):
    """
    Evaluates business rules to authorize or reject agent actions.
    """
    def __init__(self):
        # Configuration could be loaded from DB/JSON
        self.max_retries_per_event = 3
        self.max_links_per_event = 2
        self.max_contacts_per_day = 3
        self.min_ev_for_human = 50000

    def authorize(self, action: str, event: dict, context: dict) -> PolicyDecision:
        """
        Check if the proposed action is authorized.
        """
        violations = []
        
        # 1. Check idempotency/duplicate logic (simplified here, usually checked earlier)
        # 2. Check retry limits
        if action == "auto_retry":
            attempts = context.get("retry_count", 0)
            if attempts >= self.max_retries_per_event:
                violations.append(f"Max retries ({self.max_retries_per_event}) exceeded.")
                
        # 3. Check payment link limits
        if action == "payment_link":
            links = context.get("link_count", 0)
            if links >= self.max_links_per_event:
                violations.append(f"Max payment links ({self.max_links_per_event}) exceeded.")
                
        # 4. Amount thresholds
        ev = event.get("signals", {}).get("recovery_ev_rupees", 0)
        if action in ["auto_retry", "payment_link"] and ev > self.min_ev_for_human:
            violations.append(f"Amount (₹{ev}) exceeds automated threshold (₹{self.min_ev_for_human}). Requires human.")
            
        # 5. Customer dispute status
        if context.get("is_disputed", False):
            violations.append("Active customer dispute. Automated recovery halted.")

        if violations:
            logger.info(f"[POLICY] Rejected action '{action}' for event {event.get('event_id')}: {violations}")
            return PolicyDecision(
                authorized=False,
                reason="Policy violations detected.",
                violated_rules=violations,
                override_ev=ev if ev > 10000 else 0
            )

        logger.debug(f"[POLICY] Authorized action '{action}' for event {event.get('event_id')}")
        return PolicyDecision(authorized=True, reason="All checks passed.")

    def check_cooldown(self, event_id: str, action: str) -> bool:
        """Ensure we don't spam actions too quickly. (Mock implementation)"""
        return True

    def check_contact_frequency(self, customer_id: str) -> bool:
        """Ensure we don't contact the customer > 3 times/day. (Mock implementation)"""
        return True

# Global instance
policy_engine = PolicyEngine()
