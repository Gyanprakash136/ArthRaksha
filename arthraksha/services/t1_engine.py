from services.guardrails import Guardrails
from algorithms.stopping_rules import StoppingRulesEngine

class T1Engine:
    def __init__(self, taxonomy: dict, retry_tool):
        self.taxonomy = taxonomy
        self.retry_tool = retry_tool

    async def run(self, state):
        """Deterministic Engine - No LLM"""
        state.current_tier = "T1"
        
        # Layer 1 + 2 guardrails check handled in outer graph or here
        # For this engine, we directly apply stopping rules
        state = StoppingRulesEngine.evaluate(state, self.taxonomy)
        if state.stopping_rule_triggered:
            return state
            
        error_code = state.event.get("error_code")
        error_meta = self.taxonomy.get("error_codes", {}).get(error_code, {})
        
        # Guardrails validate action
        is_valid, reason = Guardrails.validate_action(state, "auto_retry", self.taxonomy)
        if not is_valid:
            state.outcome = "escalated"
            state.escalation_reason = f"T1 Guardrail failed: {reason}"
            return state

        # Read config from taxonomy
        delay_hours = error_meta.get("retry_delay_hours", 2.0)
        
        # Execute tool
        payload = {"payment_id": state.event["payment_id"], "delay_hours": delay_hours}
        result = self.retry_tool.execute(payload)
        
        if result.get("scheduled"):
            state.outcome = "retry_scheduled"
            action_taken = "auto_retry_scheduled"
            reason = f"Deterministic T1 rule for {error_code} applied"
        else:
            state.outcome = "pending"
            action_taken = "auto_retry_failed"
            reason = "Retry tool execution failed"
            
        # Log action
        entry = {
            "timestamp": state.event.get("timestamp"),  # simplified
            "payment_id": state.event["payment_id"],
            "amount": state.event["amount"],
            "error_code": error_code,
            "agent_tier": "T1",
            "complexity_score": state.complexity_score,
            "action_taken": action_taken,
            "action_reason": reason,
            "llm_reasoning": "N/A (T1 deterministic)",
            "outcome": state.outcome,
            "attempt_number": state.attempt_number,
            "stopping_rule_triggered": state.stopping_rule_triggered,
            "confidence_score": 1.0,
            "cache_hit": False,
            "tokens_used": 0
        }
        state.audit_log.append(entry)
        state.last_action = action_taken
        
        return state
