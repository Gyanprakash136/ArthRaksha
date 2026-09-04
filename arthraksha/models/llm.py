"""
ArthRaksha LLM Layer — Two Distinct Roles
==========================================

  AGENT BRAIN (recovery decisions):
    → HuggingFaceLLM   (Qwen2.5-7B-Instruct via HF Inference API)
    → Used by T2 RecoveryAgent to classify events and choose recovery paths
    → Set via: LLM_PROVIDER=huggingface  (default)

  DASHBOARD STREAMING (live narration):
    → OllamaStreamer    (llama3.2 local, token-by-token SSE to frontend)
    → Used by /dashboard/stream endpoint to show real-time agent activity
    → Ollama NEVER makes recovery decisions — it only narrates them

Agent interface (HuggingFaceLLM / OpenAI-compatible):
  .classify(event, context)            → dict
  .generate_message(template, context) → str
  .health_check()                      → bool

Streaming interface (OllamaStreamer):
  .stream_narration(prompt)            → AsyncGenerator[str, None]
"""

import os
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv
try:
    from config import settings
except ImportError:
    from arthraksha.config import settings

load_dotenv()


class LLMTimeoutError(Exception):
    pass


class LLMParseError(Exception):
    pass


def _load_system_prompt() -> str:
    path = Path(__file__).parent.parent / "config" / "system_prompt.txt"
    with open(path, "r") as f:
        return f.read()


def _extract_json(text: str) -> dict:
    """Pull the first {...} block from LLM output — handles markdown fences etc."""
    if "{" in text and "}" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    raise LLMParseError(f"No JSON object found in: {text[:200]}")


# ── Ollama (local) ────────────────────────────────────────────────────────────

class OllamaLLM:
    """
    Calls the local Ollama REST API using the /api/chat endpoint.
    Model defaults to llama3.2 (already pulled, 2GB).
    Production swap: point LLM_BASE_URL at any OpenAI-compatible endpoint.
    """

    def __init__(self):
        self.base_url = getattr(settings, "OLLAMA_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        self.model    = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout  = float(os.getenv("LLM_TIMEOUT_SEC", "30"))
        self.system_prompt = _load_system_prompt()

    async def classify(self, event: dict, context: dict) -> dict:
        """Ask the LLM to choose a recovery path. Returns parsed JSON dict."""
        user_msg = (
            f"Failed payment event:\n{json.dumps(event, indent=2)}\n\n"
            f"Customer context:\n{json.dumps(context, indent=2)}\n\n"
            f"Available recovery paths: payment_link, email_reminder, "
            f"whatsapp_reminder, auto_retry\n\n"
            f"Reply with JSON only."
        )

        payload = {
            "model":  self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            "options": {
                "temperature": 0.1,
                "num_predict": 256,
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.timeout,
                )
                resp.raise_for_status()

            data = resp.json()
            text = data["message"]["content"].strip()
            return _extract_json(text)

        except httpx.TimeoutException:
            raise LLMTimeoutError(f"Ollama timed out after {self.timeout}s")
        except json.JSONDecodeError as e:
            raise LLMParseError(f"JSON parse failed: {e}")
        except Exception as e:
            raise Exception(f"Ollama error: {e}")

    async def generate_message(self, template: str, context: dict) -> str:
        """Fill a message template. Calls LLM only if [DYNAMIC] tag is present."""
        if "[DYNAMIC]" not in template:
            filled = template
            for k, v in context.items():
                filled = filled.replace(f"{{{k}}}", str(v))
            return filled

        user_msg = (
            f"Rewrite this message naturally in Hinglish (mix of Hindi and English), "
            f"keeping it warm and concise (max 2 sentences):\n"
            f"{template.replace('[DYNAMIC]', '')}\n\n"
            f"Context: {json.dumps(context)}"
        )
        payload = {
            "model":  self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": "You write short, friendly payment recovery messages in Hinglish."},
                {"role": "user",   "content": user_msg},
            ],
            "options": {"temperature": 0.4, "num_predict": 128},
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
            return resp.json()["message"]["content"].strip()
        except Exception:
            return template.replace("[DYNAMIC]", "").strip()

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False


# ── OpenAI-compatible (any provider: OpenAI, Groq, Together, Mistral…) ───────

class OpenAICompatibleLLM:
    """
    Works with any OpenAI-format API.
    Set env vars:
      OPENAI_BASE_URL  (e.g. https://api.openai.com/v1)
      OPENAI_API_KEY
      OPENAI_MODEL     (e.g. gpt-4o-mini, mistral-small, llama-3-70b)
    """

    def __init__(self):
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.api_key  = os.getenv("OPENAI_API_KEY", "")
        self.model    = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.timeout  = float(os.getenv("LLM_TIMEOUT_SEC", "15"))
        self.system_prompt = _load_system_prompt()

    async def classify(self, event: dict, context: dict) -> dict:
        user_msg = (
            f"Event: {json.dumps(event)}\nContext: {json.dumps(context)}\n"
            f"Reply with JSON only."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            "temperature": 0.1,
            "max_tokens": 256,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload, headers=headers, timeout=self.timeout,
                )
                resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            return _extract_json(text)
        except httpx.TimeoutException:
            raise LLMTimeoutError(f"OpenAI API timed out after {self.timeout}s")
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")

    async def generate_message(self, template: str, context: dict) -> str:
        if "[DYNAMIC]" not in template:
            filled = template
            for k, v in context.items():
                filled = filled.replace(f"{{{k}}}", str(v))
            return filled
        # Delegate to simple string fill for non-dynamic templates
        return template.replace("[DYNAMIC]", "").strip()

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=3.0,
                )
            return resp.status_code == 200
        except Exception:
            return False


# ── HuggingFace (legacy, kept for backward compat) ───────────────────────────

class HuggingFaceLLM:
    """Legacy HF Inference API. Requires HUGGINGFACEHUB_API_TOKEN in .env."""

    def __init__(self):
        self.api_token = getattr(settings, "HUGGINGFACEHUB_API_TOKEN", os.getenv("HUGGINGFACEHUB_API_TOKEN"))
        if not self.api_token:
            raise ValueError("HUGGINGFACEHUB_API_TOKEN not found in .env")
        self.api_url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct"
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
        self.system_prompt = _load_system_prompt()

    async def classify(self, event: dict, context: dict) -> dict:
        payload = {
            "inputs": f"{self.system_prompt}\n\nEVENT:\n{json.dumps(event)}\n\nCONTEXT:\n{json.dumps(context)}\n\nOUTPUT JSON:",
            "parameters": {"max_new_tokens": 512, "temperature": 0.1, "return_full_text": False},
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.api_url, headers=self.headers, json=payload, timeout=10.0)
                resp.raise_for_status()
            text = resp.json()[0].get("generated_text", "").strip()
            return _extract_json(text)
        except httpx.TimeoutException:
            raise LLMTimeoutError("HuggingFace API timed out after 10s")
        except Exception as e:
            raise Exception(f"HF API Error: {e}")

    async def generate_message(self, template: str, context: dict) -> str:
        if "[DYNAMIC]" not in template:
            filled = template
            for k, v in context.items():
                filled = filled.replace(f"{{{k}}}", str(v))
            return filled
        return template.replace("[DYNAMIC]", "").strip()

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.api_url, headers=self.headers,
                                         json={"inputs": "ping", "parameters": {"max_new_tokens": 1}}, timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False


# ── Agent Brain Factory ────────────────────────────────────────────────────────

def get_llm():
    """
    Returns the LLM used by the agent brain (T2 recovery decisions).
    Default: HuggingFaceLLM (Qwen2.5-7B-Instruct)

    .env:
      LLM_PROVIDER=huggingface  ← default, agent brain
      LLM_PROVIDER=openai       ← any OpenAI-compatible endpoint
      LLM_PROVIDER=ollama       ← local fallback (if HF token unavailable)
    """
    provider = getattr(settings, "LLM_PROVIDER", os.getenv("LLM_PROVIDER", "huggingface")).lower()

    if provider == "huggingface":
        return HuggingFaceLLM()
    elif provider == "openai":
        return OpenAICompatibleLLM()
    elif provider == "ollama":
        return OllamaLLM()
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use: huggingface | openai | ollama")


# ── OllamaStreamer — Dashboard Streaming Only ─────────────────────────────────
# Completely separate from the agent brain.
# HuggingFace decides WHAT to do. Ollama NARRATES what happened, token-by-token.

from typing import AsyncGenerator

class OllamaStreamer:
    """
    Streams real-time agent activity narration to the dashboard via SSE.
    Used exclusively by the /dashboard/stream endpoint.

    Ollama NEVER makes recovery decisions — that's HuggingFace's job.
    Ollama takes the already-decided agent state and produces a human-readable
    live narrative that streams token-by-token to the frontend.

    Example output (streamed):
      "Analyzing Priya Sharma's ₹999 payment failure..."
      "Error classified as card_expired (UNINTENTIONAL category)..."
      "Routing to T2 agent. HuggingFace model selected email_reminder..."
      "Payment link generated: http://localhost:8000/demo/pay/pay_abc123..."
      "Email dispatched to priya@gmail.com ✓"
    """

    def __init__(self):
        self.base_url = getattr(settings, "OLLAMA_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        self.model    = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.enabled  = os.getenv("OLLAMA_STREAM", "true").lower() == "true"

    async def stream_narration(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Streams a narrative description of agent activity token-by-token.
        Yields each token chunk as it arrives from Ollama.
        """
        if not self.enabled:
            yield prompt
            return

        payload = {
            "model":  self.model,
            "stream": True,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a live commentary system for ArthRaksha, an AI payment recovery agent. "
                        "Narrate what the agent just did in 2-3 short sentences. "
                        "Be specific: name the customer, amount, error type, action taken. "
                        "Use ₹ for amounts. Write in present tense. No markdown, no bullet points."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": 0.3, "num_predict": 120},
        }

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=20.0,
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield token
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"[stream error: {e}]"

    async def narrate_event(self, state_summary: dict) -> AsyncGenerator[str, None]:
        """
        Convenience wrapper — takes an agent state summary dict and builds the prompt.

        state_summary keys:
          customer_name, amount, error_code, agent_tier, action_taken,
          outcome, payment_link (optional), email_to (optional)
        """
        name   = state_summary.get("customer_name", "Customer")
        amount = state_summary.get("amount", 0)
        code   = state_summary.get("error_code", "unknown_error")
        tier   = state_summary.get("agent_tier", "T2")
        action = state_summary.get("action_taken", "payment_link")
        outcome = state_summary.get("outcome", "pending")

        prompt = (
            f"The agent just processed a failed payment:\n"
            f"  Customer: {name}\n"
            f"  Amount: ₹{amount:,}\n"
            f"  Error: {code}\n"
            f"  Agent tier: {tier}\n"
            f"  Action taken: {action}\n"
            f"  Outcome: {outcome}\n\n"
            f"Narrate this in 2-3 sentences for a live dashboard feed."
        )

        async for token in self.stream_narration(prompt):
            yield token


# Singleton streamer (reuse across requests)
ollama_streamer = OllamaStreamer()
