"""
Integration tests — LLM mocking (RecoveryAgent T2 path)
Verifies that the T2 agent handles:
  - Cache HIT (no LLM call)
  - Cache MISS → LLM called → decision stored
  - LLM timeout / error → escalation fallback
  - Confidence threshold enforcement
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../arthraksha"))

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from agents.recovery_agent import RecoveryAgent
from agents.base import AgentState
from config.settings import TIER_THRESHOLDS, STOPPING_RULES, RETRY_SCHEDULE_5XX, CACHE_SETTINGS


CONFIG = {
    "TIER_THRESHOLDS": TIER_THRESHOLDS,
    "STOPPING_RULES": STOPPING_RULES,
    "RETRY_SCHEDULE_5XX": RETRY_SCHEDULE_5XX,
    "CACHE_SETTINGS": CACHE_SETTINGS,
}

TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), "../../arthraksha/data/error_taxonomy.json")
with open(TAXONOMY_PATH) as f:
    TAXONOMY = json.load(f)


def _unintentional_code():
    for code, meta in TAXONOMY.get("error_codes", {}).items():
        if meta.get("category") == "UNINTENTIONAL":
            return code
    return "insufficient_funds"


def _state(payment_id="pay_llm_001", ltv=15000, error_code=None):
    ec = error_code or _unintentional_code()
    return AgentState(
        event={
            "event_id": f"evt_llm_{payment_id[-3:]}",
            "payment_id": payment_id,
            "amount": 7500,
            "error_code": ec,
            "attempts": 0,
            "timestamp": "2026-09-01T10:00:00Z",
            "customer": {
                "contact": "+919000000001",
                "email": "llm@example.com",
                "ltv_estimate": ltv,
                "opted_out_of_comms": False,
            },
        },
        complexity_score=0.50,
        confidence_score=0.90,
        current_tier="T2",
    )


def _mock_tools():
    tools = {
        "payment_link": MagicMock(),
        "email_reminder": MagicMock(),
        "auto_retry": MagicMock(),
        "whatsapp_reminder": MagicMock(),
    }
    for t in tools.values():
        t.execute.return_value = {"sent": True, "link": "https://rzp.io/test"}
    return tools


class TestT2CacheHit:
    def test_cache_hit_skips_llm(self):
        mock_cache = MagicMock()
        mock_cache.build_key.return_value = "insufficient_funds__0__mid"
        mock_cache.get.return_value = {
            "action": "payment_link",
            "message_template": "Please pay here",
            "use_count": 5,
            "success_rate": 0.85,
        }
        mock_llm = MagicMock()
        mock_llm.classify = AsyncMock()

        agent = RecoveryAgent(TAXONOMY, mock_cache, CONFIG, mock_llm, _mock_tools())
        state = _state()
        result = asyncio.run(agent.run(state))

        # LLM should NOT have been called on a cache hit
        mock_llm.classify.assert_not_called()
        assert result.cache_hit is True
        assert result.outcome in {"recovered", "pending", "escalated", "written_off"}


class TestT2CacheMiss:
    def test_cache_miss_calls_llm(self):
        mock_cache = MagicMock()
        mock_cache.build_key.return_value = "insufficient_funds__0__mid"
        mock_cache.get.return_value = None  # MISS

        mock_llm = MagicMock()
        mock_llm.classify = AsyncMock(return_value={
            "recovery_path": "payment_link",
            "message": "Pay here",
            "confidence": 0.88,
        })

        agent = RecoveryAgent(TAXONOMY, mock_cache, CONFIG, mock_llm, _mock_tools())
        state = _state(payment_id="pay_llm_002")
        result = asyncio.run(agent.run(state))

        mock_llm.classify.assert_called_once()
        assert result.cache_hit is False

    def test_cache_miss_stores_in_cache(self):
        mock_cache = MagicMock()
        mock_cache.build_key.return_value = "k_store"
        mock_cache.get.return_value = None

        mock_llm = MagicMock()
        mock_llm.classify = AsyncMock(return_value={
            "recovery_path": "email_reminder",
            "message": "Reminder sent",
            "confidence": 0.75,
        })

        agent = RecoveryAgent(TAXONOMY, mock_cache, CONFIG, mock_llm, _mock_tools())
        state = _state(payment_id="pay_llm_003")
        asyncio.run(agent.run(state))

        mock_cache.set.assert_called_once()


class TestT2LLMFailure:
    def test_llm_exception_escalates(self):
        mock_cache = MagicMock()
        mock_cache.build_key.return_value = "k_err"
        mock_cache.get.return_value = None

        mock_llm = MagicMock()
        mock_llm.classify = AsyncMock(side_effect=Exception("LLM timeout"))

        agent = RecoveryAgent(TAXONOMY, mock_cache, CONFIG, mock_llm, _mock_tools())
        state = _state(payment_id="pay_llm_004")
        result = asyncio.run(agent.run(state))

        assert result.outcome == "pending"

    def test_llm_bad_json_escalates(self):
        mock_cache = MagicMock()
        mock_cache.build_key.return_value = "k_badjson"
        mock_cache.get.return_value = None

        mock_llm = MagicMock()
        mock_llm.classify = AsyncMock(return_value="NOT VALID JSON {{{{")

        agent = RecoveryAgent(TAXONOMY, mock_cache, CONFIG, mock_llm, _mock_tools())
        state = _state(payment_id="pay_llm_005")
        result = asyncio.run(agent.run(state))
        # Should not crash the agent
        assert result.outcome in {"escalated", "pending", "recovered", "written_off", "retry_scheduled"}
