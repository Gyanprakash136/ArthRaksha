"""
Unit tests — Audit Trail completeness (AuditTool + AgentState.log_action)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../arthraksha"))

import pytest
import sqlite3
import tempfile
from unittest.mock import patch
from agents.base import AgentState, BaseAgent
from mcp.audit_tool import AuditTool


# ── Patch get_connection to use tmp DB ──────────────────────────────────────

@pytest.fixture
def audit_db(tmp_path):
    db = str(tmp_path / "audit_test.db")
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE audit_log (
        log_id TEXT PRIMARY KEY, payment_id TEXT, timestamp TEXT,
        action_taken TEXT, action_reason TEXT, llm_reasoning TEXT, outcome TEXT,
        attempt_number INTEGER, stopping_rule_triggered INTEGER,
        confidence_score REAL, cache_hit INTEGER, tokens_used INTEGER)""")
    conn.commit()
    conn.close()
    return db


def _make_state(payment_id="pay_audit_001"):
    return AgentState(
        event={
            "event_id": "evt_audit_001",
            "payment_id": payment_id,
            "amount": 8000,
            "error_code": "gateway_technical_error",
        },
        current_tier="T2",
        complexity_score=0.55,
        confidence_score=0.82,
        attempt_number=1,
        tokens_used=320,
    )


class TestAuditLogStructure:
    def test_log_action_appends_to_state(self):
        state = _make_state()

        class _DummyAgent(BaseAgent):
            async def run(self, s): return s
            def can_handle(self, s): return True

        agent = _DummyAgent.__new__(_DummyAgent)
        agent.log_action(state, "payment_link", "High LTV customer", "recovered")

        assert len(state.audit_log) == 1
        entry = state.audit_log[0]
        assert entry["action_taken"] == "payment_link"
        assert entry["action_reason"] == "High LTV customer"
        assert entry["outcome"] == "recovered"
        assert entry["payment_id"] == "pay_audit_001"
        assert entry["agent_tier"] == "T2"
        assert entry["confidence_score"] == pytest.approx(0.82)
        assert entry["tokens_used"] == 320

    def test_log_action_has_timestamp(self):
        state = _make_state()
        from agents.base import BaseAgent
        class _A(BaseAgent):
            async def run(self, s): return s
            def can_handle(self, s): return True
        a = _A.__new__(_A)
        a.log_action(state, "auto_retry", "T1 rule")
        assert "timestamp" in state.audit_log[0]
        assert "Z" in state.audit_log[0]["timestamp"]

    def test_multiple_actions_ordered(self):
        state = _make_state()
        class _A(BaseAgent):
            async def run(self, s): return s
            def can_handle(self, s): return True
        a = _A.__new__(_A)
        a.log_action(state, "auto_retry", "first action")
        a.log_action(state, "payment_link", "second action")
        assert state.audit_log[0]["action_taken"] == "auto_retry"
        assert state.audit_log[1]["action_taken"] == "payment_link"


class TestAuditToolDB:
    def test_writes_to_db(self, audit_db):
        import mcp.audit_tool as audit_mod
        import sqlite3 as _sqlite3

        original = audit_mod.get_connection
        audit_mod.get_connection = lambda: _sqlite3.connect(audit_db)

        tool = AuditTool()
        entry = {
            "payment_id": "pay_audit_001",
            "timestamp": "2026-09-01T10:00:00Z",
            "action_taken": "payment_link",
            "action_reason": "High LTV",
            "llm_reasoning": "LTV > threshold",
            "outcome": "recovered",
            "attempt_number": 1,
            "stopping_rule_triggered": False,
            "confidence_score": 0.85,
            "cache_hit": True,
            "tokens_used": 450,
        }
        result = tool.log(entry)
        audit_mod.get_connection = original

        assert result is True
        conn = _sqlite3.connect(audit_db)
        row = conn.execute("SELECT action_taken, outcome FROM audit_log").fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "payment_link"
        assert row[1] == "recovered"

    def test_validate_requires_list(self):
        tool = AuditTool()
        assert tool.validate({"audit_log": []}) is True
        assert tool.validate({"audit_log": "bad"}) is False
        assert tool.validate({}) is False
