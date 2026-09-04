import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

class CacheManager:
    def __init__(self):
        self.cache_path = Path(__file__).parent.parent / "data" / "decision_cache.json"
        
        # Ensure file exists
        if not self.cache_path.exists():
            default_cache = {
              "_meta": {
                "description": "Cached LLM decisions to avoid repeat calls",
                "cache_key_format": "error_code__attempt__ltv_tier",
                "ltv_tiers": {
                  "high": "ltv > 20000",
                  "mid": "ltv 5000-20000",
                  "low": "ltv < 5000"
                }
              },
              "decisions": {}
            }
            self.cache_path.parent.mkdir(exist_ok=True)
            with open(self.cache_path, "w") as f:
                json.dump(default_cache, f, indent=2)

    def _read_cache(self) -> dict:
        with open(self.cache_path, "r") as f:
            return json.load(f)

    def _write_cache(self, data: dict) -> None:
        with open(self.cache_path, "w") as f:
            json.dump(data, f, indent=2)

    def build_key(self, event: dict) -> str:
        ltv = event.get("customer", {}).get("ltv_estimate", 0)
        ltv_tier = "high" if ltv > 20000 else "mid" if ltv > 5000 else "low"
        error_code = event.get("error_code", "unknown")
        attempts = event.get("attempts", 0)
        return f"{error_code}__{attempts}__{ltv_tier}"

    def get(self, key: str) -> Optional[dict]:
        cache_data = self._read_cache()
        decisions = cache_data.get("decisions", {})
        
        if key in decisions:
            # Increment use_count on hit
            decisions[key]["use_count"] += 1
            self._write_cache(cache_data)
            return decisions[key]
            
        return None

    def set(self, key: str, decision: dict, success_rate: float) -> None:
        cache_data = self._read_cache()
        
        cache_data.setdefault("decisions", {})[key] = {
            "action": decision.get("recovery_path"),
            "message_template": decision.get("message"),
            "cached_at": datetime.now(timezone.utc).isoformat() + "Z",
            "success_rate": success_rate,
            "use_count": 0
        }
        
        self._write_cache(cache_data)

    def update_success_rate(self, key: str, recovered: bool) -> None:
        cache_data = self._read_cache()
        decisions = cache_data.get("decisions", {})
        
        if key in decisions:
            old_rate = decisions[key].get("success_rate", 0.0)
            use_count = decisions[key].get("use_count", 0)
            outcome = 1.0 if recovered else 0.0
            
            # Recalculate rolling average
            new_rate = ((old_rate * use_count) + outcome) / (use_count + 1)
            
            decisions[key]["success_rate"] = round(new_rate, 4)
            self._write_cache(cache_data)
