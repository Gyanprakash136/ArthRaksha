from agents.base import BaseAgent, AgentState

class SupervisorAgent(BaseAgent):
    def __init__(self, taxonomy, cache, config):
        super().__init__(taxonomy, cache, config)

    async def run(self, state: AgentState) -> AgentState:
        # 1. Check reasoning loops
        if state.reasoning_steps > 3:
            self._kill(state, "infinite_loop")
            return state
            
        # 2. Check stuck in same action
        if state.attempt_number > 1 and state.last_action and len(state.actions_taken) > 0:
            if state.last_action == state.actions_taken[-1]:
                self._kill(state, "stuck_in_loop")
                return state
                
        # 3. Time elapsed
        max_time = self.config.get("STOPPING_RULES", {}).get("AGENT_TIMEOUT_SECONDS", 30)
        if state.time_elapsed_seconds > max_time:
            self._kill(state, "timeout")
            return state
            
        # 4. Low confidence
        if state.confidence_score < 0.15 and state.attempt_number > 1:
            self._kill(state, "low_confidence")
            return state
            
        # 5. Hallucination check (Mocked as relying on prior flags for now)
        if state.llm_reasoning == "LLMParseError":
            self._kill(state, "hallucination_detected")
            return state

        return state

    def _kill(self, state: AgentState, reason: str):
        state.outcome = "escalated"
        state.escalation_reason = f"Supervisor Kill: {reason}"
        state.stopping_rule_triggered = True
        self.log_action(state, "supervisor_kill", reason, "escalated")

    def can_handle(self, state: AgentState) -> bool:
        return True
