from config.settings import STOPPING_RULES

class StoppingRulesEngine:
    
    @staticmethod
    def evaluate(state, taxonomy: dict):
        """Evaluates stopping rules in order. Returns updated state."""
        error_code = state.event.get("error_code")
        error_meta = taxonomy.get("error_codes", {}).get(error_code, {})
        max_attempts = error_meta.get("max_attempts", STOPPING_RULES["MAX_ATTEMPTS_DEFAULT"])
        
        # RULE 1 - Fraud flag
        if error_code == "payment_risk_check_failed":
            return StoppingRulesEngine._stop(state, "fraud_flag", "written_off")
            
        # RULE 2 - Max attempts reached
        if state.attempt_number >= max_attempts:
            return StoppingRulesEngine._stop(state, "max_attempts_reached", "escalated")

            
        # RULE 3 - Explicit cancellation
        if error_code == "payment_cancelled" and state.attempt_number > 1:
            return StoppingRulesEngine._stop(state, "customer_intent_to_cancel", "written_off")
            
        # RULE 4 - Opted out
        customer = state.event.get("customer", {})
        if customer.get("opted_out_of_comms", False):
            return StoppingRulesEngine._stop(state, "customer_opted_out", "written_off")
            
        # RULE 5 - Low value threshold
        amount = state.event.get("amount", 0)
        if amount < STOPPING_RULES["MIN_RECOVERY_AMOUNT"] and state.attempt_number > 1:
            return StoppingRulesEngine._stop(state, "below_recovery_threshold", "written_off")
            
        # RULE 6 - Repeated same failure
        if len(state.actions_taken) >= 3:
            last_three = state.actions_taken[-3:]
            if len(set(last_three)) == 1 and state.outcome == "pending":
                return StoppingRulesEngine._stop(state, "recovery_path_exhausted", "escalated")
                
        return state

    @staticmethod
    def _stop(state, rule_name: str, outcome: str):
        state.stopping_rule_triggered = True
        state.outcome = outcome
        state.escalation_reason = f"Stopping rule triggered: {rule_name}"
        return state
