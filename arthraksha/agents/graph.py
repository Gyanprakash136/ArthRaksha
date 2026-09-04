import json
import os
from pathlib import Path
from agents.base import AgentState
from agents.recovery_agent import RecoveryAgent
from agents.supervisor_agent import SupervisorAgent
from agents.escalation_agent import EscalationAgent
from services.t1_engine import T1Engine
from services.cache_manager import CacheManager
from models.llm import get_llm                      # ← factory replaces hard-coded class
from config.settings import TIER_THRESHOLDS, STOPPING_RULES, RETRY_SCHEDULE_5XX, CACHE_SETTINGS
import asyncio
from mcp.email_tool import EmailTool
from mcp.payment_link_tool import PaymentLinkTool
from mcp.retry_tool import RetryTool
from mcp.audit_tool import AuditTool
from mcp.whatsapp_tool import WhatsAppTool


class RecoveryGraph:
    def __init__(self, retry_queue: asyncio.Queue):
        # Load Taxonomy
        taxonomy_path = Path(__file__).parent.parent / "data" / "error_taxonomy.json"
        with open(taxonomy_path, "r") as f:
            self.taxonomy = json.load(f)

        self.config = {
            "TIER_THRESHOLDS":    TIER_THRESHOLDS,
            "STOPPING_RULES":     STOPPING_RULES,
            "RETRY_SCHEDULE_5XX": RETRY_SCHEDULE_5XX,
            "CACHE_SETTINGS":     CACHE_SETTINGS,
        }

        self.cache_manager = CacheManager()

        # LLM — resolved from LLM_PROVIDER env var (default: ollama / llama3.2)
        self.llm = get_llm()

        # MCP Tools
        self.email_tool        = EmailTool()
        self.payment_link_tool = PaymentLinkTool()
        self.retry_tool        = RetryTool(retry_queue)
        self.audit_tool        = AuditTool()
        self.whatsapp_tool     = WhatsAppTool()

        self.tools_map = {
            "payment_link":      self.payment_link_tool,
            "email_reminder":    self.email_tool,
            "whatsapp_reminder": self.whatsapp_tool,
            "auto_retry":        self.retry_tool,
        }

        # Agents / Engines
        self.t1_engine  = T1Engine(self.taxonomy, self.retry_tool)
        self.t2_agent   = RecoveryAgent(self.taxonomy, self.cache_manager, self.config, self.llm, self.tools_map)
        self.t3_agent   = EscalationAgent(self.taxonomy, self.cache_manager, self.config, self.email_tool)
        self.supervisor = SupervisorAgent(self.taxonomy, self.cache_manager, self.config)

    async def route_event(self, event: dict) -> AgentState:
        state = AgentState(event=event)

        # Classify error → complexity score
        error_code = event.get("error_code", "")
        error_meta = self.taxonomy.get("error_codes", {}).get(error_code, {})
        category   = error_meta.get("category", "AMBIGUOUS")

        if category == "TECHNICAL":
            state.complexity_score = 0.10
        elif category == "INTENTIONAL":
            state.complexity_score = 0.90
        else:
            state.complexity_score = 0.50   # UNINTENTIONAL / AMBIGUOUS → T2

        # Hard tier routing
        t1_max = self.config["TIER_THRESHOLDS"]["T1_MAX"]
        t2_max = self.config["TIER_THRESHOLDS"]["T2_MAX"]

        if state.complexity_score < t1_max:
            # T1 — deterministic auto-retry
            state.current_tier = "T1"
            state = await self.t1_engine.run(state)

        elif state.complexity_score < t2_max:
            # T2 — LLM-assisted recovery (Ollama by default)
            state = await self.t2_agent.run(state)
            state = await self.supervisor.run(state)

            # If supervisor escalates, hand off to T3
            if state.outcome == "escalated":
                state = await self.t3_agent.run(state)
        else:
            # T3 — intentional failure / high risk → escalate immediately
            state.current_tier = "T3"
            state = await self.t3_agent.run(state)

        # ── NO fake outcome override ──────────────────────────────────────────
        # Outcomes stay as set by the agents:
        #   "pending"    → tool was dispatched (email/link sent); awaiting customer action
        #   "recovered"  → confirmation received via /demo/pay/{id}/confirm
        #   "escalated"  → supervisor or T3 escalated
        #   "written_off"→ stopping rule triggered (fraud / opted-out / max attempts)
        # ─────────────────────────────────────────────────────────────────────

        # Final audit log flush
        self.audit_tool.execute({"audit_log": state.audit_log})

        return state


# Singleton shared by the FastAPI app (one retry queue per process)
app = RecoveryGraph(asyncio.Queue())
