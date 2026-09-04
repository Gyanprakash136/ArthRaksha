from agents.base import BaseAgent, AgentState
from algorithms.stopping_rules import StoppingRulesEngine
from services.guardrails import Guardrails
import os
import time

class RecoveryAgent(BaseAgent):
    def __init__(self, taxonomy, cache, config, llm, tools_map):
        super().__init__(taxonomy, cache, config)
        self.llm = llm
        self.tools = tools_map
        self.cache_manager = cache

    async def run(self, state: AgentState) -> AgentState:
        state.current_tier = "T2"
        
        # Check cache
        cache_key = self.cache_manager.build_key(state.event)
        decision = self.cache_manager.get(cache_key)
        
        if decision:
            state.cache_hit = True
            state.tokens_used = 0
            state.llm_reasoning = "Cache hit"
            action_path = decision["action"]
            message_template = decision["message_template"]
        else:
            # ReAct REASON
            context = {
                "customer": state.event.get("customer", {}),
                "history": state.actions_taken,
                "error_meta": self.taxonomy.get("error_codes", {}).get(state.event.get("error_code"), {})
            }
            try:
                llm_response = await self.llm.classify(state.event, context)
                action_path = llm_response.get("recovery_path", "payment_link")
                message_template = llm_response.get("message", "")
                state.confidence_score = float(llm_response.get("confidence", 1.0))
                state.llm_reasoning = llm_response.get("reasoning", "")
                state.tokens_used = 150  # Mock metric
                
                # Cache decision
                self.cache_manager.set(cache_key, llm_response, 0.5)
            except Exception as e:
                # Fallback on LLM failure
                action_path = "payment_link"
                message_template = "Your payment failed. Please use this link to complete it."
                state.llm_reasoning = f"LLM_UNAVAILABLE_TAXONOMY_FALLBACK: {str(e)}"
                state.confidence_score = 0.5

        if state.event.get("send_email") or state.event.get("preferred_channel") == "email":
            action_path = "email_reminder"

        # ReAct ACT
        # Layer 2 Guardrails
        is_valid, reason = Guardrails.validate_action(state, action_path, self.taxonomy)
        if not is_valid:
            self.log_action(state, action_path, f"Guardrails blocked: {reason}", "escalated")
            state.outcome = "escalated"
            state.escalation_reason = reason
            return state

        # Layer 3 Guardrails
        sanitized_msg = Guardrails.sanitize_output(message_template, state.event)
        
        # ReAct ACT — build tool-specific payloads
        customer     = state.event.get("customer", {})
        payment_id   = state.event.get("payment_id", "")
        amount       = state.event.get("amount", 0)
        customer_name = customer.get("name", "Customer")
        email         = customer.get("email", "")
        phone         = customer.get("contact", "")
        demo_base     = os.getenv("DEMO_BASE_URL", "http://localhost:8000")

        # Generate payment link string first (used in email/whatsapp body)
        payment_link = f"{demo_base}/demo/pay/{payment_id}?amount={amount}"

        if action_path == "email_reminder":
            payload = {
                "to":         email or f"customer+{payment_id[:8]}@example.com",
                "subject":    f"Action required: Complete your ₹{amount:,} payment",
                "body": (
                    f"Namaste {customer_name}! 🙏\n\n"
                    f"Your payment of ₹{amount:,} could not be processed.\n\n"
                    f"Good news — you can complete it in 2 clicks:\n"
                    f"👉 {payment_link}\n\n"
                    f"This link is valid for 24 hours.\n\n"
                    f"Need help? Reply to this email.\n\n"
                    f"— ArthRaksha Recovery Team\n"
                    f"Ref: {payment_id}"
                ),
                "payment_id": payment_id,
                "amount":     amount,
            }
        elif action_path == "payment_link":
            payload = {
                "payment_id":   payment_id,
                "amount":       amount,
                "customer_id":  phone or email or "unknown",
                "customer_name": customer_name,
            }
        elif action_path == "whatsapp_reminder":
            payload = {
                "to":      phone or email or "unknown",
                "message": (
                    f"Namaste {customer_name} ji! 🙏 "
                    f"Aapka ₹{amount:,} payment fail hua. "
                    f"Ek click mein fix karein: {payment_link}"
                ),
                "payment_id": payment_id,
                "amount":     amount,
            }
        elif action_path == "auto_retry":
            payload = {
                "payment_id":  payment_id,
                "delay_hours": 1.0,
            }
        else:
            payload = {
                "payment_id":  payment_id,
                "amount":      amount,
                "customer_id": phone or email or "unknown",
                "message":     sanitized_msg,
            }

        # Execute the chosen tool
        tool = self.tools.get(action_path)
        tool_success = False
        if tool:
            try:
                result = tool.execute(payload)
                tool_success = result.get("success", True)
            except Exception:
                # Single retry after 2s
                time.sleep(2)
                try:
                    result = tool.execute(payload)
                    tool_success = result.get("success", True)
                except Exception as e:
                    state.escalation_reason = f"Tool {action_path} failed permanently: {str(e)}"
                    tool_success = False
        else:
            # Unknown tool path — log and continue as pending
            print(f"[WARN] No tool registered for action_path: {action_path}")
            tool_success = True   # Don't escalate on unknown path

        if tool_success:
            state.outcome = "pending"
        else:
            state.outcome = "escalated"

            
        state.last_action = action_path
        state.reasoning_steps += 1
        
        self.log_action(state, action_path, "ReAct Loop execution", state.outcome)
        
        # ReAct OBSERVE
        state = StoppingRulesEngine.evaluate(state, self.taxonomy)
        
        return state

    def can_handle(self, state: AgentState) -> bool:
        return state.complexity_score < self.config.get("TIER_THRESHOLDS", {}).get("T2_MAX", 0.75)
