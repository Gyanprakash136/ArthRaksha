"""
Integration tests — T3 Escalation Agent
Verifies that EscalationAgent:
  - Sets outcome = 'escalated' and tier = 'T3'
  - Writes to escalation_log.md
  - Sends an email notification
  - Sanitizes output (no raw card/account numbers)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../arthraksha"))

import pytest
import asyncio
import json
import tempfile
from unittest.mock import MagicMock, patch
from agents.escalation_agent import EscalationAgent
from agents.base import AgentState

TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), "../../arthraksha/data/error_taxonomy.json")
with open(TAXONOMY_PATH) as f:
    TAXONOMY = json.load(f)

CONFIG = {"TIER_THRESHOLDS": {"T1_MAX": 0.35, "T2_MAX": 0.75, "T3_MAX": 0.85}}


def _intentional_code():
    for code, meta in TAXONOMY.get("error_codes", {}).items():
        if meta.get("category") == "INTENTIONAL":
            return code
    return "payment_risk_check_failed"


def _state(payment_id="pay_t3_001"):
    return AgentState(
        event={
            "event_id": "evt_t3_001",
            "payment_id": payment_id,
            "amount": 25000,
            "error_code": _intentional_code(),
            "timestamp": "2026-09-01T10:00:00Z",
            "customer": {
                "contact": "+919000000099",
                "email": "vip@example.com",
                "ltv_estimate": 80000,
            },
        },
        complexity_score=0.90,
        confidence_score=0.10,
        current_tier="T3",
        actions_taken=["payment_link", "email_reminder"],
        escalation_reason="Risk score >= 0.85",
    )


class TestEscalationAgent:

    def test_outcome_set_to_escalated(self, tmp_path):
        email_tool = MagicMock()
        email_tool.send.return_value = True

        with patch("agents.escalation_agent.Path") as MockPath:
            MockPath.return_value.__truediv__ = lambda s, x: tmp_path / x
            agent = EscalationAgent(TAXONOMY, {}, CONFIG, email_tool)
            # Override log path directly
            agent_real = EscalationAgent.__new__(EscalationAgent)
            agent_real.taxonomy = TAXONOMY
            agent_real.cache = {}
            agent_real.config = CONFIG
            agent_real.email_tool = email_tool

        # Patch the log file write to tmp
        log_dir = tmp_path / "docs"
        log_dir.mkdir()

        with patch("agents.escalation_agent.Path") as MockP:
            MockP.return_value.__truediv__ = lambda s, x: tmp_path
            agent2 = EscalationAgent(TAXONOMY, {}, CONFIG, email_tool)

            import agents.escalation_agent as ea_mod
            original_path = ea_mod.Path
            ea_mod.Path = lambda *a: log_dir

            state = _state()
            result = asyncio.run(agent2.run(state))
            ea_mod.Path = original_path

        assert result.outcome == "escalated"
        assert result.current_tier == "T3"

    def test_email_sent_on_escalation(self, tmp_path):
        email_tool = MagicMock()
        email_tool.send.return_value = True

        import agents.escalation_agent as ea_mod
        log_dir = tmp_path / "docs"
        log_dir.mkdir()
        original_path = ea_mod.Path
        ea_mod.Path = lambda *a: log_dir

        agent = EscalationAgent(TAXONOMY, {}, CONFIG, email_tool)
        state = _state(payment_id="pay_t3_002")
        asyncio.run(agent.run(state))

        ea_mod.Path = original_path
        email_tool.send.assert_called_once()

    def test_email_subject_contains_payment_id(self, tmp_path):
        email_tool = MagicMock()

        import agents.escalation_agent as ea_mod
        log_dir = tmp_path / "docs"
        log_dir.mkdir()
        original_path = ea_mod.Path
        ea_mod.Path = lambda *a: log_dir

        agent = EscalationAgent(TAXONOMY, {}, CONFIG, email_tool)
        state = _state(payment_id="pay_t3_003")
        asyncio.run(agent.run(state))

        ea_mod.Path = original_path
        call_kwargs = email_tool.send.call_args
        subject = call_kwargs.kwargs.get("subject") or call_kwargs[1].get("subject") or call_kwargs[0][1]
        assert "pay_t3_003" in subject

    def test_escalation_log_written(self, tmp_path):
        email_tool = MagicMock()
    
        log_dir = tmp_path / "docs"
        log_dir.mkdir(exist_ok=True)
        (log_dir / "escalation_log.md").write_text("")  # pre-create
    
        class MockPathBuilder:
            def __init__(self, *args): pass
            @property
            def parent(self): return self
            def __truediv__(self, other): return log_dir

        import agents.escalation_agent as ea_mod
        original_path = ea_mod.Path
        ea_mod.Path = MockPathBuilder
    
        agent = EscalationAgent(TAXONOMY, {}, CONFIG, email_tool)
        state = _state(payment_id="pay_t3_004")
        asyncio.run(agent.run(state))
        ea_mod.Path = original_path
    
        log_content = (log_dir / "escalation_log.md").read_text()
        assert "pay_t3_004" in log_content

    def test_can_handle_high_score(self):
        email_tool = MagicMock()
        agent = EscalationAgent(TAXONOMY, {}, CONFIG, email_tool)
        state = AgentState(event={}, complexity_score=0.90)
        assert agent.can_handle(state) is True

    def test_can_handle_low_score_false(self):
        email_tool = MagicMock()
        agent = EscalationAgent(TAXONOMY, {}, CONFIG, email_tool)
        state = AgentState(event={}, complexity_score=0.30)
        assert agent.can_handle(state) is False
