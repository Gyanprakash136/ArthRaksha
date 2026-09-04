"""
ArthRaksha — Runtime Monitor (Supervisor)
============================================
Implements IRuntimeMonitor.
Tracks observable execution properties (time, tokens, iterations, loops).
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from interfaces import IRuntimeMonitor

logger = logging.getLogger(__name__)

class RuntimeMonitor(IRuntimeMonitor):
    """
    Control plane element: monitors execution limits.
    """
    def __init__(self):
        self.MAX_ITERATIONS = 5
        self.MAX_TOOL_CALLS = 6
        self.MAX_TOKENS = 1500
        self.MAX_TIME_MS = 30000
        self.MAX_SAME_ACTION = 2

    def check(self, agent_state: dict) -> dict:
        """
        Evaluate if the agent is within bounds.
        """
        iters = agent_state.get("iteration_count", 0)
        tokens = agent_state.get("token_count", 0)
        time_ms = agent_state.get("elapsed_ms", 0)
        tools = agent_state.get("tool_call_count", 0)
        same_action = agent_state.get("same_action_count", 0)
        
        if iters >= self.MAX_ITERATIONS:
            return {"ok": False, "action": "stop", "reason": f"Iteration limit ({self.MAX_ITERATIONS}) reached."}
            
        if tokens >= self.MAX_TOKENS:
            return {"ok": False, "action": "stop", "reason": f"Token budget ({self.MAX_TOKENS}) exceeded."}
            
        if time_ms >= self.MAX_TIME_MS:
            return {"ok": False, "action": "stop", "reason": f"Execution time ({self.MAX_TIME_MS}ms) exceeded."}
            
        if tools >= self.MAX_TOOL_CALLS:
            return {"ok": False, "action": "stop", "reason": f"Tool call limit ({self.MAX_TOOL_CALLS}) reached."}
            
        if same_action >= self.MAX_SAME_ACTION:
            return {"ok": False, "action": "stop", "reason": f"Repeated action limit ({self.MAX_SAME_ACTION}) reached. Loop detected."}
            
        # Warning if approaching limits
        if iters == self.MAX_ITERATIONS - 1 or tokens > self.MAX_TOKENS * 0.8:
            return {"ok": True, "action": "warn", "reason": "Approaching execution limits."}
            
        return {"ok": True, "action": "continue", "reason": "Within bounds."}

# Global instance
runtime_monitor = RuntimeMonitor()
