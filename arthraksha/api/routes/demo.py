"""
Demo Payment Page — simulates a customer receiving and clicking a payment link.

Routes:
  GET  /demo/pay/{payment_id}?amount=999
    → Renders an HTML page: "Priya Sharma — ₹999 — Click to Pay"
  POST /demo/pay/{payment_id}/confirm
    → Updates recovery_ledger.outcome = 'recovered'
    → Returns JSON { "status": "recovered", "payment_id": "..." }

This closes the loop:
  EmailTool sends link → customer clicks → /demo/pay/{id} → clicks Pay →
  POST /demo/pay/{id}/confirm → DB updated → dashboard shows "recovered"
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from config.database import get_connection

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.get("/pay/{payment_id}", response_class=HTMLResponse)
def demo_payment_page(payment_id: str, amount: int = 0):
    """Renders a mock payment page the 'customer' sees after clicking the link."""

    # Try to fetch customer name and real amount from DB
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT amount, error_code FROM recovery_ledger WHERE payment_id = ?",
        (payment_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        db_amount    = row[0] if row[0] else amount
        error_code   = row[1] or "payment_failure"
    else:
        db_amount    = amount
        error_code   = "payment_failure"

    display_amount = f"₹{db_amount:,}" if db_amount else f"₹{amount:,}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Complete Your Payment · ArthRaksha</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      min-height: 100vh;
      display: flex; align-items: center; justify-content: center;
      padding: 20px;
    }}
    .card {{
      background: #1e293b;
      border: 1px solid rgba(59,130,246,0.2);
      border-radius: 20px;
      padding: 40px;
      max-width: 440px;
      width: 100%;
      box-shadow: 0 25px 60px rgba(0,0,0,0.5);
    }}
    .logo {{
      display: flex; align-items: center; gap: 10px;
      margin-bottom: 32px;
    }}
    .logo-icon {{
      width: 38px; height: 38px; border-radius: 10px;
      background: linear-gradient(135deg, #3B82F6, #1D4ED8);
      display: flex; align-items: center; justify-content: center;
      font-size: 18px;
    }}
    .logo-text {{ color: #fff; font-size: 16px; font-weight: 700; }}
    .logo-sub  {{ color: rgba(255,255,255,0.4); font-size: 10px; }}
    .amount-box {{
      background: rgba(59,130,246,0.08);
      border: 1px solid rgba(59,130,246,0.2);
      border-radius: 14px;
      padding: 24px;
      text-align: center;
      margin-bottom: 24px;
    }}
    .amount-label {{ color: rgba(255,255,255,0.5); font-size: 12px; margin-bottom: 8px; }}
    .amount {{ color: #fff; font-size: 42px; font-weight: 800; }}
    .payment-id {{ color: rgba(255,255,255,0.3); font-size: 11px; margin-top: 6px; font-family: monospace; }}
    .reason-box {{
      background: rgba(245,158,11,0.08);
      border: 1px solid rgba(245,158,11,0.2);
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 28px;
      color: rgba(255,255,255,0.65);
      font-size: 13px;
      line-height: 1.5;
    }}
    .reason-box strong {{ color: #FBBF24; }}
    .pay-btn {{
      width: 100%;
      padding: 16px;
      border-radius: 12px;
      border: none;
      background: linear-gradient(135deg, #22C55E, #16A34A);
      color: white;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      transition: transform 0.1s, opacity 0.2s;
      display: flex; align-items: center; justify-content: center; gap: 10px;
      font-family: inherit;
    }}
    .pay-btn:hover {{ transform: translateY(-1px); opacity: 0.95; }}
    .pay-btn:active {{ transform: translateY(0); }}
    .pay-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    .secure {{
      text-align: center;
      color: rgba(255,255,255,0.25);
      font-size: 11px;
      margin-top: 16px;
    }}
    .success-state {{
      display: none;
      text-align: center;
      padding: 20px 0;
    }}
    .success-state .check {{ font-size: 64px; margin-bottom: 16px; }}
    .success-state h2 {{ color: #22C55E; font-size: 22px; font-weight: 800; margin-bottom: 8px; }}
    .success-state p {{ color: rgba(255,255,255,0.5); font-size: 13px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">
      <div class="logo-icon">⚡</div>
      <div>
        <div class="logo-text">ArthRaksha</div>
        <div class="logo-sub">Secure Payment Recovery</div>
      </div>
    </div>

    <div id="payment-form">
      <div class="amount-box">
        <div class="amount-label">Amount Due</div>
        <div class="amount">{display_amount}</div>
        <div class="payment-id">{payment_id}</div>
      </div>

      <div class="reason-box">
        <strong>Payment failed</strong> — {error_code.replace('_', ' ').title()}<br>
        No worries! Click below to complete your payment securely.
        Your data is safe and no extra charges apply.
      </div>

      <button class="pay-btn" id="pay-btn" onclick="confirmPayment()">
        <span>🔒</span> Pay {display_amount} Now
      </button>
      <div class="secure">🛡️ 256-bit SSL Encrypted · Powered by Razorpay</div>
    </div>

    <div class="success-state" id="success">
      <div class="check">✅</div>
      <h2>Payment Successful!</h2>
      <p>Your payment of <strong style="color:#fff">{display_amount}</strong> has been received.<br>
         You'll receive a confirmation shortly.</p>
    </div>
  </div>

  <script>
    async function confirmPayment() {{
      const btn = document.getElementById('pay-btn');
      btn.disabled = true;
      btn.innerHTML = '<span>⏳</span> Processing...';

      try {{
        const resp = await fetch('/demo/pay/{payment_id}/confirm', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ amount: {db_amount} }}),
        }});
        const data = await resp.json();

        if (data.status === 'recovered') {{
          document.getElementById('payment-form').style.display = 'none';
          document.getElementById('success').style.display = 'block';
        }} else {{
          btn.disabled = false;
          btn.innerHTML = '<span>🔒</span> Retry Payment';
        }}
      }} catch (e) {{
        btn.disabled = false;
        btn.innerHTML = '<span>🔒</span> Try Again';
      }}
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.post("/pay/{payment_id}/confirm")
def confirm_payment(payment_id: str):
    """
    Called when customer clicks 'Pay Now' on the demo page.
    Updates recovery_ledger.outcome = 'recovered'.
    This is the event that closes the recovery loop.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE recovery_ledger SET outcome = 'recovered', updated_at = datetime('now') WHERE payment_id = ?",
        (payment_id,),
    )
    cursor.execute(
        "UPDATE promise_tracker SET status = 'kept' WHERE payment_id = ?",
        (payment_id,),
    )
    cursor.execute(
        "UPDATE voice_sessions SET status = 'closed', promise_kept = 1, last_updated = datetime('now') WHERE session_id = ? OR payment_id = ?",
        (payment_id, payment_id),
    )
    updated = cursor.rowcount
    conn.commit()
    conn.close()

    if updated > 0:
        print(f"[DEMO CONFIRM] Payment recovered: {payment_id}")
        return JSONResponse({"status": "recovered", "payment_id": payment_id})
    else:
        # Payment ID not in ledger yet — insert a placeholder (race condition during fast sim)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR IGNORE INTO recovery_ledger 
               (payment_id, amount, error_code, agent_tier, complexity_score, outcome, attempts, created_at, updated_at)
               VALUES (?, 0, 'demo_confirm', 'DEMO', 0.0, 'recovered', 1, datetime('now'), datetime('now'))""",
            (payment_id,),
        )
        conn.commit()
        conn.close()
        return JSONResponse({"status": "recovered", "payment_id": payment_id})
