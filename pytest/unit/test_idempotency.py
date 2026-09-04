"""
Unit tests — Idempotency Store (SQLiteIdempotencyStore)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../arthraksha"))

import pytest
import tempfile
from services.idempotency_store import SQLiteIdempotencyStore


@pytest.fixture
def store(tmp_path):
    return SQLiteIdempotencyStore(db_path=str(tmp_path / "idem_test.db"))


class TestIdempotencyStore:
    def test_new_key_not_duplicate(self, store):
        assert not store.is_duplicate("RC_evt001:auto_retry:0")

    def test_mark_then_duplicate(self, store):
        key = "RC_evt002:payment_link:1"
        store.mark_executed(key, {"outcome": "recovered"})
        assert store.is_duplicate(key)

    def test_get_result_returns_stored(self, store):
        key = "RC_evt003:email_reminder:0"
        payload = {"outcome": "pending", "tier": "T2"}
        store.mark_executed(key, payload)
        result = store.get_result(key)
        assert result == payload

    def test_get_result_unknown_key_returns_none(self, store):
        assert store.get_result("RC_nonexistent:auto_retry:0") is None

    def test_double_mark_does_not_raise(self, store):
        key = "RC_evt004:auto_retry:0"
        store.mark_executed(key, {"x": 1})
        store.mark_executed(key, {"x": 2})  # should silently ignore (IntegrityError caught)
        result = store.get_result(key)
        assert result == {"x": 1}  # first write wins

    def test_independent_keys_independent(self, store):
        store.mark_executed("RC_a:auto_retry:0", {"a": 1})
        store.mark_executed("RC_b:auto_retry:0", {"b": 2})
        assert store.is_duplicate("RC_a:auto_retry:0")
        assert store.is_duplicate("RC_b:auto_retry:0")
        assert not store.is_duplicate("RC_c:auto_retry:0")
