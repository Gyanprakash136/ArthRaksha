from agents.base import BaseAgent, AgentState
from services.guardrails import Guardrails
import json
import os
from pathlib import Path

class EscalationAgent(BaseAgent):
    def __init__(self, taxonomy, cache, config, email_tool):
        super().__init__(taxonomy, cache, config)
        self.email_tool = email_tool

    async def run(self, state: AgentState) -> AgentState:
        state.current_tier = "T3"
        
        summary = {
            "payment_id": state.event.get("payment_id"),
            "amount": state.event.get("amount"),
            "error_code": state.event.get("error_code"),
            "customer_ltv": state.event.get("customer", {}).get("ltv_estimate"),
            "actions_taken": state.actions_taken,
            "escalation_reason": state.escalation_reason or "Risk score >= 0.85",
            "recommended_action": "human_review",
            "audit_log": state.audit_log
        }
        
        # Layer 3 Guardrails
        sanitized_summary_text = Guardrails.sanitize_output(json.dumps(summary, indent=2), state.event)
        
        # Send Email to human
        admin_email = os.getenv("ADMIN_EMAIL", "risk-team@example.com")
        self.email_tool.send(
            to=admin_email,
            subject=f"URGENT: Escalation for Payment {summary['payment_id']}",
            body=f"Human review required.\n\nDetails:\n{sanitized_summary_text}"
        )
        
        # Write to log file
        log_dir = Path(__file__).parent.parent / "docs"
        log_dir.mkdir(exist_ok=True)
        with open(log_dir / "escalation_log.md", "a") as f:
            f.write(f"\n## Escalation: {summary['payment_id']}\n")
            f.write(f"Reason: {summary['escalation_reason']}\n")
            f.write(f"```json\n{sanitized_summary_text}\n```\n")
            
        state.outcome = "escalated"
        self.log_action(state, "human_handoff", "T3 escalation executed", "escalated")
        
        return state

    def can_handle(self, state: AgentState) -> bool:
        return state.complexity_score >= self.config.get("TIER_THRESHOLDS", {}).get("T2_MAX", 0.75) or state.outcome == "escalated"
