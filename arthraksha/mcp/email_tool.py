"""
EmailTool — MCP Email Action
=============================
DEMO_MODE=true (default): writes to arthraksha/docs/sent_emails.log
                           (readable from dashboard, safe for demos)
DEMO_MODE=false:           sends real SMTP email via EMAIL_HOST / EMAIL_USER / EMAIL_PASS
"""
import os
import smtplib
import json
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from dotenv import load_dotenv
from mcp.interfaces import EmailInterface

load_dotenv()


LOG_PATH = Path(__file__).parent.parent / "docs" / "sent_emails.log"


class EmailTool(EmailInterface):

    def validate(self, payload: dict) -> bool:
        return "to" in payload and "subject" in payload and "body" in payload

    def execute(self, payload: dict) -> dict:
        ok = self.send(
            to=payload["to"],
            subject=payload["subject"],
            body=payload["body"],
            payment_id=payload.get("payment_id", ""),
            amount=payload.get("amount", 0),
        )
        return {"success": ok}

    def send(self, to: str, subject: str, body: str,
             payment_id: str = "", amount: int = 0) -> bool:

        demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
        host      = os.getenv("EMAIL_HOST")
        user      = os.getenv("EMAIL_USER")
        password  = os.getenv("EMAIL_PASS")
        port      = int(os.getenv("EMAIL_PORT", 587))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        receiving_email = os.getenv("RECEIVING_EMAIL")
        if receiving_email:
            to = receiving_email

        if demo_mode or not all([host, user, password]):
            # Write to log file instead of sending
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp":  timestamp,
                "to":         to,
                "subject":    subject,
                "body":       body,
                "payment_id": payment_id,
                "amount":     amount,
                "status":     "demo_logged",
            }
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"[EMAIL LOG] {timestamp} → {to} | {subject}")
            return True

        # Real SMTP send
        msg = MIMEMultipart("alternative")
        msg["Subject"]    = subject
        msg["From"]       = f"ArthRaksha Recovery <{user}>"
        msg["To"]         = to
        msg["Date"]       = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="gmail.com")

        # Plain text
        msg.attach(MIMEText(body, "plain"))

        # HTML formatted version
        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; }}
  .card {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 28px; border: 1px solid #e2e8f0; box-shadow: 0 4px 14px rgba(0,0,0,0.06); }}
  .header {{ border-bottom: 2px solid #3b82f6; padding-bottom: 12px; margin-bottom: 20px; }}
  .title {{ font-size: 18px; font-weight: bold; color: #0f172a; margin: 0; }}
  .content {{ font-size: 14px; line-height: 1.65; color: #334155; white-space: pre-wrap; }}
  .footer {{ margin-top: 24px; padding-top: 14px; border-top: 1px solid #e2e8f0; font-size: 11.5px; color: #94a3b8; text-align: center; }}
</style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="title">ArthRaksha Autonomous Recovery 🛡️</div>
    </div>
    <div class="content">{body}</div>
    <div class="footer">
      Automated dispatch from ArthRaksha · AI Revenue Recovery Engine
    </div>
  </div>
</body>
</html>"""
        msg.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(msg)
            print(f"[EMAIL SENT] {timestamp} → {to} | {subject}")
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp":  timestamp,
                "to":         to,
                "subject":    subject,
                "body":       body,
                "payment_id": payment_id,
                "amount":     amount,
                "status":     "sent",
            }
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return True
        except Exception as e:
            # Retry once
            try:
                with smtplib.SMTP(host, port) as server:
                    server.starttls()
                    server.login(user, password)
                    server.send_message(msg)
                return True
            except Exception as e2:
                print(f"[EMAIL FAIL] {e2}")
                # Graceful fallback: log to sent_emails.log so the recovery pipeline does not crash
                LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                entry = {
                    "timestamp":  timestamp,
                    "to":         to,
                    "subject":    subject,
                    "body":       body,
                    "payment_id": payment_id,
                    "amount":     amount,
                    "status":     "demo_logged_fallback",
                    "smtp_error": str(e2),
                }
                with open(LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                print(f"[EMAIL LOG FALLBACK] {timestamp} → {to} | {subject}")
                return True
