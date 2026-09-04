"""
Chaos tests — 1000-event burst, SQLite concurrency, queue overflow, stopping rules under load
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../arthraksha"))

import pytest
import asyncio
import json
import random
import sqlite3
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock, patch
from agents.graph import RecoveryGraph
from agents.base import AgentState
from algorithms.stopping_rules import StoppingRulesEngine

TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), "../../arthraksha/data/error_taxonomy.json")
with open(TAXONOMY_PATH) as f:
    TAXONOMY = json.load(f)

ERROR_CODES = list(TAXONOMY.get("error_codes", {}).keys())
VALID_OUTCOMES = {"recovered", "escalated", "written_off", "retry_scheduled", "pending"}


# ── helpers ──────────────────────────────────────────────────────────────────

def _event(n: int):
    return {
        "event_id": f"evt_chaos_{n:06d}",
        "payment_id": f"pay_chaos_{n:06d}",
        "amount": random.randint(100, 200_000),
        "error_code": random.choice(ERROR_CODES),
        "timestamp": "2026-09-01T10:00:00Z",
        "customer": {
            "id": f"cust_{n:06d}",
            "contact": "+919000000000",
            "email": "chaos@example.com",
            "ltv_estimate": random.randint(1000, 100_000),
            "opted_out_of_comms": False,
        },
    }


def _patched_graph(retry_queue=None):
    if retry_queue is None:
        retry_queue = asyncio.Queue()
    with patch("agents.graph.EmailTool") as ME, \
         patch("agents.graph.PaymentLinkTool") as MPL, \
         patch("agents.graph.RetryTool") as MRT, \
         patch("agents.graph.AuditTool") as MAT, \
         patch("agents.graph.WhatsAppTool") as MWA, \
         patch("agents.graph.get_llm") as MLLM:

        MRT.return_value.execute.return_value = {"scheduled": True}
        MPL.return_value.execute.return_value = {"link": "https://rzp.io/test"}
        ME.return_value.send.return_value = True
        ME.return_value.execute.return_value = {"sent": True}
        mock_llm_inst = MagicMock()
        mock_llm_inst.generate = AsyncMock(return_value=json.dumps({
            "recovery_path": "payment_link",
            "message": "Chaos test",
            "confidence": 0.80,
        }))
        MLLM.return_value = mock_llm_inst
        MAT.return_value.execute.return_value = {"success": True}
        MAT.return_value.log.return_value = True

        graph = RecoveryGraph(retry_queue)
    return graph


# ── burst test ────────────────────────────────────────────────────────────────

class TestBurst:
    @pytest.mark.timeout(120)
    def test_1000_events_all_resolve(self):
        """1000 concurrent events must all resolve without exception."""
        async def _run():
            graph = _patched_graph()
            events = [_event(i) for i in range(1000)]
            tasks = [graph.route_event(e) for e in events]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        results = asyncio.run(_run())
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"{len(exceptions)} events raised exceptions"

    @pytest.mark.timeout(120)
    def test_1000_events_valid_outcomes(self):
        """All 1000 results must have a valid terminal outcome."""
        async def _run():
            graph = _patched_graph()
            events = [_event(i) for i in range(1000)]
            return await asyncio.gather(*[graph.route_event(e) for e in events],
                                        return_exceptions=True)

        results = asyncio.run(_run())
        bad = [r for r in results if not isinstance(r, Exception) and r.outcome not in VALID_OUTCOMES]
        assert len(bad) == 0, f"{len(bad)} events had invalid outcome"

    @pytest.mark.timeout(120)
    def test_burst_throughput(self):
        """1000 events must complete within 60 seconds."""
        async def _run():
            graph = _patched_graph()
            return await asyncio.gather(*[graph.route_event(_event(i)) for i in range(1000)],
                                        return_exceptions=True)

        start = time.time()
        asyncio.run(_run())
        elapsed = time.time() - start
        assert elapsed < 60, f"Burst took {elapsed:.1f}s (limit: 60s)"


# ── SQLite concurrency ────────────────────────────────────────────────────────

class TestSQLiteConcurrency:
    def test_concurrent_idempotency_writes_no_corruption(self, tmp_path):
        """10 threads writing distinct keys simultaneously must not corrupt the DB."""
        from services.idempotency_store import SQLiteIdempotencyStore
        db = str(tmp_path / "concurrent.db")
        store = SQLiteIdempotencyStore(db_path=db)

        import threading
        errors = []

        def _write(n):
            try:
                store.mark_executed(f"RC_evt_{n:04d}:auto_retry:0", {"n": n})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_write, args=(i,)) for i in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(errors) == 0

        # All 50 keys must be present
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM idempotency").fetchone()[0]
        conn.close()
        assert count == 50

    def test_duplicate_write_under_concurrency_safe(self, tmp_path):
        """10 threads writing the SAME key must not raise; first write wins."""
        from services.idempotency_store import SQLiteIdempotencyStore
        db = str(tmp_path / "dup.db")
        store = SQLiteIdempotencyStore(db_path=db)

        import threading
        errors = []

        def _write():
            try:
                store.mark_executed("RC_shared:auto_retry:0", {"x": 1})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_write) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(errors) == 0
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM idempotency").fetchone()[0]
        conn.close()
        assert count == 1


# ── queue overflow ────────────────────────────────────────────────────────────

class TestQueueOverflow:
    @pytest.mark.timeout(30)
    def test_bounded_queue_does_not_deadlock(self):
        """asyncio.Queue with maxsize=10 fills and drains without deadlock."""
        async def _run():
            q = asyncio.Queue(maxsize=10)
            # Fill the queue
            for i in range(10):
                await q.put(f"item_{i}")
            assert q.full()
            # Drain
            for _ in range(10):
                q.get_nowait()
                q.task_done()
            assert q.empty()

        asyncio.run(_run())

    def test_queue_backpressure_respected(self):
        """put_nowait on a full queue raises QueueFull — caller must handle it."""
        async def _run():
            q = asyncio.Queue(maxsize=2)
            q.put_nowait("a")
            q.put_nowait("b")
            with pytest.raises(asyncio.QueueFull):
                q.put_nowait("c")

        asyncio.run(_run())


# ── stopping rules under load ─────────────────────────────────────────────────

class TestStoppingRulesUnderLoad:
    def test_stopping_rules_consistent_across_1000_events(self):
        """No state mutation should bleed between stopping rule evaluations."""
        random.seed(42)
        for i in range(1000):
            state = AgentState(
                event={
                    "event_id": f"evt_sr_{i}",
                    "payment_id": f"pay_sr_{i}",
                    "amount": random.randint(50, 300_000),
                    "error_code": random.choice(ERROR_CODES),
                    "customer": {
                        "contact": "+91999",
                        "opted_out_of_comms": random.choice([True, False]),
                    },
                },
                attempt_number=random.randint(0, 5),
                actions_taken=random.choices(
                    ["auto_retry", "payment_link", "email_reminder"],
                    k=random.randint(0, 4)
                ),
                outcome="pending",
            )
            result = StoppingRulesEngine.evaluate(state, TAXONOMY)
            # Must always return a valid outcome
            assert result.outcome in VALID_OUTCOMES

    def test_fraud_always_written_off(self):
        """payment_risk_check_failed must ALWAYS result in written_off regardless of other state."""
        for i in range(100):
            state = AgentState(
                event={
                    "event_id": f"evt_fraud_{i}",
                    "payment_id": f"pay_fraud_{i}",
                    "amount": random.randint(1000, 500_000),
                    "error_code": "payment_risk_check_failed",
                    "customer": {"contact": "+91999", "opted_out_of_comms": False},
                },
                attempt_number=random.randint(0, 3),
            )
            result = StoppingRulesEngine.evaluate(state, TAXONOMY)
            assert result.outcome == "written_off"
            assert result.stopping_rule_triggered
