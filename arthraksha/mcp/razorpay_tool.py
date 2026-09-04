"""
ArthRaksha — Razorpay MCP Tools
=================================
Wraps Razorpay API calls as MCP tools.

In test/demo mode: returns realistic simulated responses.
In live mode:      makes real Razorpay API calls via requests.

Tools:
  trigger_retry         → retry a failed subscription charge
  send_payment_link     → generate + send a Razorpay payment link
  cancel_subscription   → cancel a subscription (INTENTIONAL path)
  fetch_subscription    → get current subscription status
  fetch_payment         → get payment details
"""

import json
import random
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    from fastmcp import FastMCP
    mcp = FastMCP("arthraksha-razorpay")
except ImportError:
    class FastMCP:
        def __init__(self, name): self.name = name
        def tool(self):
            def decorator(fn): return fn
            return decorator
    mcp = FastMCP("arthraksha-razorpay")

# ── check if live mode is configured ──────────────────────────────────────────
def _is_live() -> bool:
    try:
        from config.settings import settings
        return bool(settings.razorpay_key_id and settings.razorpay_key_secret)
    except Exception:
        return False


def _sim_response(success: bool, data: dict, latency_ms: int = 120) -> dict:
    """Wrap a simulated response in a standard envelope."""
    return {
        "mode":       "simulation",
        "success":    success,
        "latency_ms": latency_ms,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        **data,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Tool: trigger_retry
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def trigger_retry(
    subscription_id: str,
    payment_id:      str,
    merchant_id:     str,
) -> dict:
    """
    Trigger a retry for a failed subscription charge.

    Used for TECHNICAL failures where auto-retry is the recovery path.

    Returns:
      - success (bool)
      - new_payment_id
      - status ("created" | "failed" | "pending")
      - retry_at (ISO timestamp)
      - message

    Args:
        subscription_id: e.g. "sub_xxxxxxxxxx"
        payment_id:      The failed payment ID to retry
        merchant_id:     Merchant identifier

    In demo mode: simulates 65% success rate (matching RBI stats).
    """
    if _is_live():
        # Production: real Razorpay call
        try:
            import requests
            from config.settings import settings
            resp = requests.post(
                f"https://api.razorpay.com/v1/subscriptions/{subscription_id}/retry",
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                timeout=10,
            )
            data = resp.json()
            return {
                "mode":           "live",
                "success":        resp.status_code == 200,
                "razorpay_data":  data,
                "timestamp":      datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {"mode": "live", "success": False, "error": str(e)}

    # ── Simulation ──
    success        = random.random() < 0.65   # 65% retry success rate
    new_payment_id = f"pay_{uuid.uuid4().hex[:10]}"
    retry_at       = (datetime.now(timezone.utc) + timedelta(seconds=random.randint(5, 30))).isoformat()

    return _sim_response(success, {
        "subscription_id": subscription_id,
        "original_payment_id": payment_id,
        "new_payment_id":  new_payment_id if success else None,
        "status":          "created" if success else "failed",
        "retry_at":        retry_at,
        "message": (
            f"Retry payment {new_payment_id} created for subscription {subscription_id}."
            if success else
            f"Retry failed for subscription {subscription_id}. Will attempt again."
        ),
    })


# ══════════════════════════════════════════════════════════════════════════════
#  Tool: send_payment_link
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def send_payment_link(
    subscription_id: str,
    customer_email:  str,
    customer_phone:  str,
    customer_name:   str,
    amount_paise:    int,
    merchant_id:     str,
    expire_hours:    int = 48,
    preferred_lang:  str = "en",
) -> dict:
    """
    Generate a Razorpay payment link and send it to the customer.

    Used for UNINTENTIONAL failures (insufficient funds, card expired, etc.)
    where the customer needs to take action.

    Returns:
      - success (bool)
      - payment_link_id
      - short_url  (the link to send to customer)
      - expires_at (ISO timestamp)
      - sms_sent   (bool)
      - email_sent (bool)
      - message

    Args:
        subscription_id: Subscription being recovered
        customer_email:  Customer's email address
        customer_phone:  Customer's phone (e.g. "+919876543210")
        customer_name:   Customer's full name
        amount_paise:    Amount in paise (rupees × 100)
        merchant_id:     Merchant identifier
        expire_hours:    Link expiry in hours (default 48)
        preferred_lang:  "en" or "hi" (Hinglish notification)

    In demo mode: simulates 42% click-through rate.
    """
    if _is_live():
        try:
            import requests
            from config.settings import settings

            expire_ts = int(
                (datetime.now(timezone.utc) + timedelta(hours=expire_hours)).timestamp()
            )
            payload = {
                "amount":      amount_paise,
                "currency":    "INR",
                "description": f"Subscription recovery — {subscription_id}",
                "customer":    {
                    "name":    customer_name,
                    "email":   customer_email,
                    "contact": customer_phone,
                },
                "notify":      {"sms": True, "email": True},
                "expire_by":   expire_ts,
                "reminder_enable": True,
                "notes":       {"subscription_id": subscription_id, "merchant_id": merchant_id},
            }
            resp = requests.post(
                "https://api.razorpay.com/v1/payment_links",
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                json=payload,
                timeout=10,
            )
            data = resp.json()
            return {
                "mode":           "live",
                "success":        resp.status_code == 200,
                "payment_link_id": data.get("id"),
                "short_url":      data.get("short_url"),
                "expires_at":     datetime.fromtimestamp(expire_ts, tz=timezone.utc).isoformat(),
                "razorpay_data":  data,
            }
        except Exception as e:
            return {"mode": "live", "success": False, "error": str(e)}

    # ── Simulation ──
    link_id   = f"plink_{uuid.uuid4().hex[:10]}"
    short_url = f"https://rzp.io/i/{uuid.uuid4().hex[:6].upper()}"
    expires   = (datetime.now(timezone.utc) + timedelta(hours=expire_hours)).isoformat()

    # Hinglish SMS content
    if preferred_lang == "hi":
        sms_content = (
            f"Namaste {customer_name.split()[0]}! "
            f"Aapka payment ₹{amount_paise//100} fail ho gaya. "
            f"Iss link pe click karke complete karein: {short_url} "
            f"(48 ghante mein expire ho jayega)"
        )
    else:
        sms_content = (
            f"Hi {customer_name.split()[0]}, your payment of ₹{amount_paise//100} "
            f"failed. Complete it here: {short_url} (expires in {expire_hours}h)"
        )

    return _sim_response(True, {
        "subscription_id":  subscription_id,
        "payment_link_id":  link_id,
        "short_url":        short_url,
        "amount_rupees":    amount_paise / 100,
        "expires_at":       expires,
        "sms_sent":         True,
        "email_sent":       True,
        "sms_content":      sms_content,
        "message": f"Payment link {short_url} sent to {customer_email} and {customer_phone}.",
    })


# ══════════════════════════════════════════════════════════════════════════════
#  Tool: cancel_subscription
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def cancel_subscription(
    subscription_id: str,
    merchant_id:     str,
    reason:          str = "customer_request",
    cancel_at_end:   bool = True,
) -> dict:
    """
    Cancel a subscription (used for INTENTIONAL churn path).

    Args:
        subscription_id: The subscription to cancel
        merchant_id:     Merchant identifier
        reason:          Cancellation reason for records
        cancel_at_end:   If True, cancel at end of billing period (default)
                         If False, cancel immediately

    Returns:
      - success (bool)
      - status ("cancelled" | "pending_cancellation")
      - effective_date
      - message
    """
    if _is_live():
        try:
            import requests
            from config.settings import settings

            resp = requests.post(
                f"https://api.razorpay.com/v1/subscriptions/{subscription_id}/cancel",
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                json={"cancel_at_cycle_end": 1 if cancel_at_end else 0},
                timeout=10,
            )
            return {
                "mode":    "live",
                "success": resp.status_code == 200,
                "data":    resp.json(),
            }
        except Exception as e:
            return {"mode": "live", "success": False, "error": str(e)}

    # ── Simulation ──
    effective = (
        datetime.now(timezone.utc) + timedelta(days=30)
        if cancel_at_end
        else datetime.now(timezone.utc)
    ).isoformat()

    return _sim_response(True, {
        "subscription_id": subscription_id,
        "status":          "pending_cancellation" if cancel_at_end else "cancelled",
        "effective_date":  effective,
        "reason":          reason,
        "message": (
            f"Subscription {subscription_id} will be cancelled at end of billing period."
            if cancel_at_end else
            f"Subscription {subscription_id} cancelled immediately."
        ),
    })


# ══════════════════════════════════════════════════════════════════════════════
#  Tool: fetch_subscription
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def fetch_subscription(subscription_id: str) -> dict:
    """
    Fetch current subscription status and details from Razorpay.

    Returns subscription status, plan, last charge info, and customer details.

    Args:
        subscription_id: e.g. "sub_xxxxxxxxxx"
    """
    if _is_live():
        try:
            import requests
            from config.settings import settings

            resp = requests.get(
                f"https://api.razorpay.com/v1/subscriptions/{subscription_id}",
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                timeout=10,
            )
            return {"mode": "live", "success": resp.status_code == 200, "data": resp.json()}
        except Exception as e:
            return {"mode": "live", "success": False, "error": str(e)}

    # ── Simulation ──
    return _sim_response(True, {
        "subscription_id": subscription_id,
        "status": random.choice(["active", "past_due", "paused"]),
        "plan_id": f"plan_{uuid.uuid4().hex[:8]}",
        "charge_at": (datetime.now(timezone.utc) + timedelta(days=random.randint(1, 30))).isoformat(),
        "total_count":  12,
        "paid_count":   random.randint(1, 11),
        "remaining_count": random.randint(1, 11),
    })


# ── CLI test ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🔧 Razorpay Tool Tests (simulation mode)\n")

    r = trigger_retry("sub_test001", "pay_test001", "MID_0001")
    print(f"✅ trigger_retry:      success={r['success']}, status={r.get('status')}")

    r = send_payment_link(
        "sub_test001", "user@example.com", "+919876543210",
        "Arjun Sharma", 79900, "MID_0001", preferred_lang="hi"
    )
    print(f"✅ send_payment_link:  url={r.get('short_url')}")
    print(f"   SMS: {r.get('sms_content', '')[:80]}...")

    r = cancel_subscription("sub_test001", "MID_0001")
    print(f"✅ cancel_subscription: status={r.get('status')}")
