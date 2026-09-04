"""
Unit tests — Stopping Rules Engine
Tests all 6 stopping rules declared in algorithms/stopping_rules.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../arthraksha"))

import pytest
import json
from agents.base import AgentState
from algorithms.stopping_rules import StoppingRulesEngine


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def taxonomy():
    path = os.path.join(os.path.dirname(__file__), "../../arthraksha/data/error_taxonomy.json")
    with open(path) as f:
        return json.load(f)


def _state(error_code="gateway_technical_error", amount=5000, attempt=0,
           opted_out=False, actions=None, outcome="pending"):
    return AgentState(
        event={
            "event_id": "evt_sr_001",
            "payment_id": "pay_sr_001",
            "amount": amount,
            "error_code": error_code,
            "customer": {
                "contact": "+91999",
                "opted_out_of_comms": opted_out,
            },
        },
        attempt_number=attempt,
        actions_taken=actions or [],
        outcome=outcome,
    )


# ── rule 1: max attempts ──────────────────────────────────────────────────────

class TestStoppingRuleMaxAttempts:
    def test_at_limit_triggers(self, taxonomy):
        # default max_attempts_default = 3
        state = _state(attempt=3)
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        assert result.stopping_rule_triggered
        assert result.outcome == "escalated"

    def test_below_limit_continues(self, taxonomy):
        state = _state(attempt=1)
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        assert not result.stopping_rule_triggered


# ── rule 2: fraud flag ────────────────────────────────────────────────────────

class TestStoppingRuleFraud:
    def test_fraud_error_code_written_off(self, taxonomy):
        state = _state(error_code="payment_risk_check_failed")
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        assert result.stopping_rule_triggered
        assert result.outcome == "written_off"

    def test_normal_error_code_not_written_off(self, taxonomy):
        state = _state(error_code="gateway_technical_error")
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        assert not result.stopping_rule_triggered


# ── rule 3: cancellation intent ───────────────────────────────────────────────

class TestStoppingRuleCancellation:
    def test_cancelled_after_first_attempt_written_off(self, taxonomy):
        state = _state(error_code="payment_cancelled", attempt=2)
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        assert result.stopping_rule_triggered
        assert result.outcome == "written_off"

    def test_cancelled_on_first_attempt_continues(self, taxonomy):
        state = _state(error_code="payment_cancelled", attempt=1)
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        # attempt <= 1, rule 3 does NOT fire (condition: attempt_number > 1)
        assert not result.stopping_rule_triggered


# ── rule 4: opted out ────────────────────────────────────────────────────────

class TestStoppingRuleOptedOut:
    def test_opted_out_customer_written_off(self, taxonomy):
        state = _state(opted_out=True)
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        assert result.stopping_rule_triggered
        assert result.outcome == "written_off"

    def test_opted_in_customer_continues(self, taxonomy):
        state = _state(opted_out=False)
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        assert not result.stopping_rule_triggered


# ── rule 5: low value ────────────────────────────────────────────────────────

class TestStoppingRuleLowValue:
    def test_tiny_amount_second_attempt_written_off(self, taxonomy):
        state = _state(amount=50, attempt=2)
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        assert result.stopping_rule_triggered
        assert result.outcome == "written_off"

    def test_tiny_amount_first_attempt_continues(self, taxonomy):
        state = _state(amount=50, attempt=1)
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        assert not result.stopping_rule_triggered

    def test_normal_amount_not_written_off(self, taxonomy):
        state = _state(amount=5000, attempt=2)
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        assert not result.stopping_rule_triggered


# ── rule 6: path exhausted ───────────────────────────────────────────────────

class TestStoppingRulePathExhausted:
    def test_three_identical_actions_escalated(self, taxonomy):
        state = _state(actions=["payment_link", "payment_link", "payment_link"], outcome="pending")
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        assert result.stopping_rule_triggered
        assert result.outcome == "escalated"

    def test_mixed_actions_continues(self, taxonomy):
        state = _state(actions=["auto_retry", "payment_link", "email_reminder"], outcome="pending")
        result = StoppingRulesEngine.evaluate(state, taxonomy)
        assert not result.stopping_rule_triggered
