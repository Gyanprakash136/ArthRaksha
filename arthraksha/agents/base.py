from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

@dataclass
class AgentState:
    event: dict
    attempt_number: int = 0
    actions_taken: list = field(default_factory=list)
    llm_reasoning: str = ""
    current_tier: str = "T1"
    complexity_score: float = 0.0
    outcome: str = "pending"
    stopping_rule_triggered: bool = False
    escalation_reason: str = ""
    audit_log: list = field(default_factory=list)
    reasoning_steps: int = 0
    last_action: str = ""
    confidence_score: float = 1.0
    cache_hit: bool = False
    tokens_used: int = 0
    time_elapsed_seconds: float = 0.0
    cache_hits_this_batch: int = 0
    cache_misses_this_batch: int = 0
    tokens_saved_this_batch: int = 0

class BaseAgent(ABC):
    def __init__(self, taxonomy: dict, cache: dict, config: dict):
        self.taxonomy = taxonomy
        self.cache = cache
        self.config = config

    @abstractmethod
    async def run(self, state: AgentState) -> AgentState:
        pass

    @abstractmethod
    def can_handle(self, state: AgentState) -> bool:
        pass

    def log_action(self, state: AgentState, action: str, reason: str, outcome: str = "pending") -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payment_id": state.event["payment_id"],
            "amount": state.event["amount"],
            "error_code": state.event["error_code"],
            "agent_tier": state.current_tier,
            "complexity_score": state.complexity_score,
            "action_taken": action,
            "action_reason": reason,
            "llm_reasoning": state.llm_reasoning,
            "outcome": outcome,
            "attempt_number": state.attempt_number,
            "stopping_rule_triggered": state.stopping_rule_triggered,
            "confidence_score": state.confidence_score,
            "cache_hit": state.cache_hit,
            "tokens_used": state.tokens_used
        }
        state.audit_log.append(entry)
