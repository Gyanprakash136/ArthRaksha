"""
PaymentLinkTool — MCP Payment Link Generator
=============================================
DEMO_MODE=true:  returns http://localhost:8000/demo/pay/{payment_id}
                 (customer can click "Pay" → confirms payment → updates DB)
Production:      calls Razorpay API to create a real payment link
"""
import os
from mcp.interfaces import PaymentLinkInterface


class PaymentLinkTool(PaymentLinkInterface):

    def validate(self, payload: dict) -> bool:
        return "payment_id" in payload and "amount" in payload

    def execute(self, payload: dict) -> dict:
        link = self.generate(
            payment_id=payload["payment_id"],
            amount=payload["amount"],
            customer_id=payload.get("customer_id", "unknown"),
            customer_name=payload.get("customer_name", ""),
        )
        return {
            "success":    True,
            "link":       link,
            "expires_at": "24 hours",
        }

    def generate(self, payment_id: str, amount: int,
                 customer_id: str, customer_name: str = "") -> str:

        demo_mode  = os.getenv("DEMO_MODE", "true").lower() == "true"
        rzp_key    = os.getenv("RAZORPAY_KEY")
        rzp_secret = os.getenv("RAZORPAY_SECRET")

        if demo_mode or not (rzp_key and rzp_secret):
            # Demo link: serves a real HTML page via FastAPI /demo/pay/{payment_id}
            base = os.getenv("DEMO_BASE_URL", "http://localhost:8000")
            link = f"{base}/demo/pay/{payment_id}?amount={amount}"
            print(f"[PAYMENT LINK] Demo link generated: {link}")
            return link

        # ── Production: Razorpay Payment Links API ────────────────────────────
        import httpx
        import json

        headers = {"Content-Type": "application/json"}
        payload = {
            "amount":      amount * 100,    # Razorpay uses paise
            "currency":    "INR",
            "description": f"Payment recovery for {customer_name or customer_id}",
            "reference_id": payment_id,
            "customer": {"name": customer_name, "contact": customer_id},
            "notify": {"sms": True, "email": True},
            "reminder_enable": True,
            "callback_url": f"{os.getenv('WEBHOOK_BASE_URL', '')}/webhook/razorpay/confirmed",
        }

        try:
            resp = httpx.post(
                "https://api.razorpay.com/v1/payment_links",
                json=payload,
                headers=headers,
                auth=(rzp_key, rzp_secret),
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json().get("short_url", f"https://rzp.io/{payment_id}")
        except Exception as e:
            print(f"[PAYMENT LINK] Razorpay API failed ({e}), using demo link")
            base = os.getenv("DEMO_BASE_URL", "http://localhost:8000")
            return f"{base}/demo/pay/{payment_id}?amount={amount}"
