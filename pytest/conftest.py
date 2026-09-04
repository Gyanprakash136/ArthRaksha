"""
conftest.py — root fixture file for ArthRaksha pytest suite.
Adds `arthraksha/` to sys.path so all internal imports resolve correctly.
"""
import sys
import os
import json
import sqlite3
import tempfile
import pytest

# ── path bootstrap ──────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTHRAKSHA = os.path.join(ROOT, "arthraksha")
if ARTHRAKSHA not in sys.path:
    sys.path.insert(0, ARTHRAKSHA)

# ── taxonomy fixture ─────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def taxonomy():
    tax_path = os.path.join(ARTHRAKSHA, "data", "error_taxonomy.json")
    with open(tax_path) as f:
        return json.load(f)

# ── minimal valid event factory ──────────────────────────────────────────────
@pytest.fixture
def make_event():
    """Returns a factory that builds minimal valid payment-failure events."""
    counter = {"n": 0}

    def _make(
        error_code="gateway_technical_error",
        amount=5000,
        ltv=15000,
        opted_out=False,
        attempts=0,
        extra=None,
    ):
        counter["n"] += 1
        ev = {
            "event_id": f"evt_test_{counter['n']:05d}",
            "payment_id": f"pay_test_{counter['n']:05d}",
            "amount": amount,
            "error_code": error_code,
            "timestamp": "2026-09-01T10:00:00Z",
            "customer": {
                "id": f"cust_{counter['n']:05d}",
                "name": "Test User",
                "contact": "+919876543210",
                "email": "test@example.com",
                "ltv_estimate": ltv,
                "opted_out_of_comms": opted_out,
            },
        }
        if extra:
            ev.update(extra)
        return ev

    return _make

# ── ephemeral DB fixture (patches config.database) ───────────────────────────
@pytest.fixture
def temp_db(monkeypatch):
    """Creates an in-memory-backed temp SQLite DB and patches get_connection."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    import config.database as db_module

    # Initialise schema
    db_module.DB_PATH = type("P", (), {"parent": type("P", (), {"__truediv__": lambda s, x: s})()})()
    original_get = db_module.get_connection

    def _patched_get():
        conn = sqlite3.connect(tmp.name)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(db_module, "get_connection", _patched_get)

    # Bootstrap tables
    from config.database import init_db
    db_module.DB_PATH = type("P", (), {
        "__str__": lambda s: tmp.name,
        "parent": type("P2", (), {
            "mkdir": lambda *a, **kw: None,
            "__truediv__": lambda s, x: s,
        })()
    })()

    conn = sqlite3.connect(tmp.name)
    conn.execute("""CREATE TABLE IF NOT EXISTS idempotency_store (
        event_id TEXT PRIMARY KEY, processed_at TEXT, outcome TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS recovery_ledger (
        payment_id TEXT PRIMARY KEY, amount INTEGER, error_code TEXT,
        agent_tier TEXT, complexity_score REAL, outcome TEXT,
        amount_recovered INTEGER, attempts INTEGER, created_at TEXT, updated_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        log_id TEXT PRIMARY KEY, payment_id TEXT, timestamp TEXT,
        action_taken TEXT, action_reason TEXT, llm_reasoning TEXT, outcome TEXT,
        attempt_number INTEGER, stopping_rule_triggered INTEGER,
        confidence_score REAL, cache_hit INTEGER, tokens_used INTEGER)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS promise_tracker (
        promise_id TEXT PRIMARY KEY, payment_id TEXT, customer_id TEXT,
        promised_amount INTEGER, promised_date TEXT, status TEXT,
        created_at TEXT, reminder_sent INTEGER)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS voice_sessions (
        session_id TEXT PRIMARY KEY, payment_id TEXT, turn_count INTEGER DEFAULT 0,
        last_intent TEXT, last_promised_date TEXT, promise_kept INTEGER DEFAULT 0,
        churn_signal INTEGER DEFAULT 0, status TEXT DEFAULT 'active',
        last_updated TEXT, transcript TEXT)""")
    conn.commit()
    conn.close()

    yield tmp.name

    os.unlink(tmp.name)
