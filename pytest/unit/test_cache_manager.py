"""
Unit tests — CacheManager (decision_cache.json)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../arthraksha"))

import pytest
import json
from services.cache_manager import CacheManager


@pytest.fixture
def cache(tmp_path):
    c = CacheManager.__new__(CacheManager)
    c.cache_path = tmp_path / "test_cache.json"
    # seed empty cache
    c.cache_path.write_text(json.dumps({"_meta": {}, "decisions": {}}))
    return c


class TestCacheManagerKeys:
    def test_high_ltv_key(self, cache):
        event = {"error_code": "insufficient_funds", "attempts": 0,
                 "customer": {"ltv_estimate": 50000}}
        assert cache.build_key(event) == "insufficient_funds__0__high"

    def test_mid_ltv_key(self, cache):
        event = {"error_code": "card_expired", "attempts": 1,
                 "customer": {"ltv_estimate": 10000}}
        assert cache.build_key(event) == "card_expired__1__mid"

    def test_low_ltv_key(self, cache):
        event = {"error_code": "gateway_technical_error", "attempts": 2,
                 "customer": {"ltv_estimate": 1000}}
        assert cache.build_key(event) == "gateway_technical_error__2__low"


class TestCacheManagerGetSet:
    def test_miss_returns_none(self, cache):
        assert cache.get("missing_key") is None

    def test_set_then_get(self, cache):
        decision = {"recovery_path": "payment_link", "message": "Pay here"}
        cache.set("k1", decision, success_rate=0.8)
        result = cache.get("k1")
        assert result is not None
        assert result["action"] == "payment_link"
        assert result["success_rate"] == 0.8

    def test_get_increments_use_count(self, cache):
        cache.set("k2", {"recovery_path": "email_reminder", "message": "Reminder"}, 0.6)
        cache.get("k2")
        cache.get("k2")
        result = cache.get("k2")
        assert result["use_count"] == 3

    def test_update_success_rate_rolling_average(self, cache):
        cache.set("k3", {"recovery_path": "auto_retry", "message": ""}, success_rate=1.0)
        # use_count starts at 0, first update: (1.0*0 + 0) / 1 = 0.0
        cache.update_success_rate("k3", recovered=False)
        result = cache.get("k3")
        assert result["success_rate"] == 0.0

    def test_update_nonexistent_key_noop(self, cache):
        # Should not raise
        cache.update_success_rate("does_not_exist", recovered=True)
