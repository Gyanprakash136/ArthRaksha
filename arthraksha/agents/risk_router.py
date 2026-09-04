"""
ArthRaksha — Risk Router
===========================
Implements IRouter.
Computes complexity/risk score to route events to T1, T2, T3, or HITL.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from interfaces import IRouter, RoutingDecision, RoutingTier

logger = logging.getLogger(__name__)

class RiskRouter(IRouter):
    """
    Routes events based on computed complexity score.
    """
    def __init__(self, max_amount_rupees: float = 100000.0):
        self.max_amount = max_amount_rupees

    def compute_score(self, event: dict) -> dict:
        """
        Compute components and total complexity score.
        """
        error_reason = event.get("error_reason", "")
        amount = float(event.get("amount_rupees", 0.0))
        signals = event.get("signals", {})
        context = event.get("context", {})
        
        # 1. Ambiguity (0.3 if ambiguous error)
        ambiguity = 0.3 if error_reason in ["unknown_error", "bank_timeout"] else 0.0
        
        # 2. Financial Risk (normalized amount)
        financial_risk = min(amount / self.max_amount, 1.0) * 0.4  # Weight 0.4
        
        # 3. Policy Complexity
        policy_complexity = 0.0
        if context.get("is_disputed", False):
            policy_complexity += 0.5
        if context.get("has_open_ticket", False):
            policy_complexity += 0.2
            
        # 4. Context Complexity
        context_complexity = 0.0
        if signals.get("churn_probability", 0.0) > 0.7:
            context_complexity += 0.2
            
        # 5. Historical Failure
        prior_failures = signals.get("prior_failures", 0)
        historical_failure = min(prior_failures * 0.1, 0.3)
        
        total_score = ambiguity + financial_risk + policy_complexity + context_complexity + historical_failure
        
        return {
            "total": total_score,
            "components": {
                "ambiguity": ambiguity,
                "financial_risk": financial_risk,
                "policy_complexity": policy_complexity,
                "context_complexity": context_complexity,
                "historical_failure": historical_failure
            }
        }

    def route(self, event: dict) -> RoutingDecision:
        score_data = self.compute_score(event)
        score = score_data["total"]
        comps = score_data["components"]
        
        if score > 0.85:
            tier = RoutingTier.HITL
            reason = "UNSAFE score (>0.85). Immediate human review."
        elif score > 0.65:
            tier = RoutingTier.T3_REACT
            reason = "HIGH score (0.65 - 0.85). Requires bounded ReAct."
        elif score > 0.35:
            tier = RoutingTier.T2_BOUNDED_LLM
            reason = "MEDIUM score (0.35 - 0.65). Requires bounded LLM selection."
        else:
            tier = RoutingTier.T1_DETERMINISTIC
            reason = "LOW score (<0.35). Deterministic rule execution."
            
        logger.info(f"[ROUTER] Event {event.get('event_id')} routed to {tier.value} (Score: {score:.2f})")
        
        return RoutingDecision(
            tier=tier,
            complexity_score=score,
            reason=reason,
            **comps
        )

# Global instance
risk_router = RiskRouter()
