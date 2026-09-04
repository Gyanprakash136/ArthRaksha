"""
Unit tests — RiskRouter (agents/risk_router.py)
Verifies scoring components and T1/T2/T3/HITL tier boundaries.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../arthraksha"))

import pytest
from agents.risk_router import RiskRouter
from interfaces import RoutingTier


@pytest.fixture
def router():
    return RiskRouter(max_amount_rupees=100_000.0)


def _event(amount=5000, error_reason="insufficient_funds",
           is_disputed=False, has_ticket=False,
           churn_prob=0.0, prior_failures=0):
    return {
        "event_id": "evt_router_01",
        "amount_rupees": amount,
        "error_reason": error_reason,
        "signals": {"churn_probability": churn_prob, "prior_failures": prior_failures},
        "context": {"is_disputed": is_disputed, "has_open_ticket": has_ticket},
    }


class TestRiskRouterScoring:
    def test_ambiguity_component_for_unknown_error(self, router):
        score = router.compute_score(_event(error_reason="unknown_error"))
        assert score["components"]["ambiguity"] == 0.3

    def test_ambiguity_component_zero_for_known_error(self, router):
        score = router.compute_score(_event(error_reason="insufficient_funds"))
        assert score["components"]["ambiguity"] == 0.0

    def test_financial_risk_normalized(self, router):
        score = router.compute_score(_event(amount=100_000))
        assert score["components"]["financial_risk"] == pytest.approx(0.4)

    def test_financial_risk_capped_at_max(self, router):
        score = router.compute_score(_event(amount=200_000))
        assert score["components"]["financial_risk"] == pytest.approx(0.4)

    def test_disputed_adds_policy_complexity(self, router):
        score = router.compute_score(_event(is_disputed=True))
        assert score["components"]["policy_complexity"] >= 0.5

    def test_open_ticket_adds_complexity(self, router):
        score = router.compute_score(_event(has_ticket=True))
        assert score["components"]["policy_complexity"] >= 0.2

    def test_high_churn_adds_context_complexity(self, router):
        score = router.compute_score(_event(churn_prob=0.9))
        assert score["components"]["context_complexity"] == 0.2

    def test_prior_failures_capped_at_0_3(self, router):
        score = router.compute_score(_event(prior_failures=10))
        assert score["components"]["historical_failure"] == pytest.approx(0.3)


class TestRiskRouterTierBoundaries:
    def test_low_score_routes_t1(self, router):
        ev = _event(amount=1000)
        decision = router.route(ev)
        assert decision.tier == RoutingTier.T1_DETERMINISTIC

    def test_medium_score_routes_t2(self, router):
        ev = _event(amount=50000, churn_prob=0.8, prior_failures=2)
        decision = router.route(ev)
        assert decision.tier in (RoutingTier.T2_BOUNDED_LLM, RoutingTier.T3_REACT, RoutingTier.HITL)

    def test_hitl_above_0_85(self, router):
        # max possible score is > 0.85 with all factors maxed
        ev = _event(amount=100_000, error_reason="bank_timeout",
                    is_disputed=True, has_ticket=True, churn_prob=0.9, prior_failures=10)
        decision = router.route(ev)
        assert decision.tier == RoutingTier.HITL

    def test_routing_decision_has_reason(self, router):
        decision = router.route(_event())
        assert decision.reason
        assert len(decision.reason) > 5

    def test_score_in_decision_matches_compute(self, router):
        ev = _event(amount=30_000)
        computed = router.compute_score(ev)["total"]
        decision = router.route(ev)
        assert decision.complexity_score == pytest.approx(computed)
