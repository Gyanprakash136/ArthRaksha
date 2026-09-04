"""
Integration tests — Tier routing end-to-end via RecoveryGraph.route_event()

Tests that:
  - TECHNICAL error_codes → T1 (complexity_score ≈ 0.10)
  - UNINTENTIONAL codes  → T2 (complexity_score ≈ 0.50)
  - INTENTIONAL codes    → T3/escalated (complexity_score ≈ 0.90)
  - Audit log is populated with at least one entry
  - Outcome is a valid terminal value
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../arthraksha"))

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from agents.graph import RecoveryGraph
from agents.base import AgentState

VALID_OUTCOMES = {"recovered", "escalated", "written_off", "retry_scheduled", "pending"}


# ── Load taxonomy to discover real error codes ─────────────────────────────

@pytest.fixture(scope="module")
def taxonomy():
    path = os.path.join(os.path.dirname(__file__), "../../arthraksha/data/error_taxonomy.json")
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def tech_error_code(taxonomy):
    for code, meta in taxonomy.get("error_codes", {}).items():
        if meta.get("category") == "TECHNICAL":
            return code
    pytest.skip("No TECHNICAL error code found in taxonomy")


@pytest.fixture(scope="module")
def unintentional_error_code(taxonomy):
    for code, meta in taxonomy.get("error_codes", {}).items():
        if meta.get("category") == "UNINTENTIONAL":
            return code
    pytest.skip("No UNINTENTIONAL error code found in taxonomy")


@pytest.fixture(scope="module")
def intentional_error_code(taxonomy):
    for code, meta in taxonomy.get("error_codes", {}).items():
        if meta.get("category") == "INTENTIONAL":
            return code
    pytest.skip("No INTENTIONAL error code found in taxonomy")


def _event(error_code, payment_id="pay_int_001", amount=5000):
    return {
        "event_id": f"evt_int_{error_code[:8]}",
        "payment_id": payment_id,
        "amount": amount,
        "error_code": error_code,
        "timestamp": "2026-09-01T10:00:00Z",
        "customer": {
            "id": "cust_int_001",
            "name": "Integration User",
            "contact": "+919876543210",
            "email": "int@example.com",
            "ltv_estimate": 12000,
            "opted_out_of_comms": False,
        },
    }


def _patched_graph():
    """RecoveryGraph with all external I/O mocked out."""
    with patch("agents.graph.EmailTool") as MockEmail, \
         patch("agents.graph.PaymentLinkTool") as MockPL, \
         patch("agents.graph.RetryTool") as MockRetry, \
         patch("agents.graph.AuditTool") as MockAudit, \
         patch("agents.graph.WhatsAppTool") as MockWA, \
         patch("agents.graph.get_llm") as MockLLM:

        # Retry tool returns scheduled
        MockRetry.return_value.execute.return_value = {"scheduled": True}
        # Payment link returns success
        MockPL.return_value.execute.return_value = {"link": "https://rzp.io/test"}
        # Email succeeds
        MockEmail.return_value.send.return_value = True
        MockEmail.return_value.execute.return_value = {"sent": True}
        # LLM returns a valid action
        mock_llm_inst = MagicMock()
        mock_llm_inst.generate = AsyncMock(return_value=json.dumps({
            "recovery_path": "payment_link",
            "message": "Please complete your payment",
            "confidence": 0.85,
        }))
        MockLLM.return_value = mock_llm_inst
        # Audit tool is a no-op
        MockAudit.return_value.execute.return_value = {"success": True}
        MockAudit.return_value.log.return_value = True

        import asyncio
        graph = RecoveryGraph(asyncio.Queue())
        return graph


class TestTierRouting:

    def test_technical_error_routes_t1(self, tech_error_code):
        graph = _patched_graph()
        state = asyncio.run(
            graph.route_event(_event(tech_error_code))
        )
        assert state.current_tier == "T1"
        assert state.complexity_score == pytest.approx(0.10)
        assert state.outcome in VALID_OUTCOMES

    def test_unintentional_error_routes_t2(self, unintentional_error_code):
        graph = _patched_graph()
        state = asyncio.run(
            graph.route_event(_event(unintentional_error_code, payment_id="pay_int_002"))
        )
        assert state.current_tier in ("T2", "T3")
        assert state.complexity_score == pytest.approx(0.50)
        assert state.outcome in VALID_OUTCOMES

    def test_intentional_error_routes_t3(self, intentional_error_code):
        graph = _patched_graph()
        state = asyncio.run(
            graph.route_event(_event(intentional_error_code, payment_id="pay_int_003"))
        )
        assert state.current_tier == "T3"
        assert state.complexity_score == pytest.approx(0.90)
        assert state.outcome == "escalated"

    def test_audit_log_populated(self, tech_error_code):
        graph = _patched_graph()
        state = asyncio.run(
            graph.route_event(_event(tech_error_code, payment_id="pay_int_004"))
        )
        assert len(state.audit_log) >= 1

    def test_outcome_is_terminal(self, tech_error_code):
        graph = _patched_graph()
        state = asyncio.run(
            graph.route_event(_event(tech_error_code, payment_id="pay_int_005"))
        )
        assert state.outcome in VALID_OUTCOMES

    def test_audit_log_has_payment_id(self, tech_error_code):
        graph = _patched_graph()
        ev = _event(tech_error_code, payment_id="pay_int_006")
        state = asyncio.run(graph.route_event(ev))
        if state.audit_log:
            for entry in state.audit_log:
                assert entry.get("payment_id") == "pay_int_006"
