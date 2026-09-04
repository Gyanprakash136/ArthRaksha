import os
import uuid
import re
from datetime import datetime

try:
    from services.hinglish_voice.session_store import VoiceSessionStore
except ImportError:
    from arthraksha.services.hinglish_voice.session_store import VoiceSessionStore

try:
    from mcp.email_tool import EmailTool
except ImportError:
    from arthraksha.mcp.email_tool import EmailTool


class HinglishVoiceAgent:
    """
    Intelligent Multi-Lingual Conversational Recovery Agent.
    Supports English, Hindi (Devanagari), and Hinglish (Code-mixed) with:
      1. Adaptive language detection and mirroring
      2. Intent classification and Promise-to-Pay extraction
      3. Human escalation intent detection with admin email alerts
      4. Hard loop guard (freezes AI when AWAITING_HUMAN)
      5. Sender role management (Customer vs. Merchant)
    """

    def __init__(self):
        self.store = VoiceSessionStore()
        self.email_tool = EmailTool()

        # Multi-lingual templates
        self.templates = {
            "english": {
                "pay": "Certainly! Here is your secure payment link: {link}. Please let us know if you face any issues.",
                "churn": "We understand. Could you please share what issue occurred? We are here to assist you.",
                "delay": "No problem! We will send you a reminder on {date}. Rest assured until then.",
                "unclear": "No worries! Your payment was for ₹{amount}. How can we help you complete it?",
                "follow_up_delay": "Earlier you mentioned {last_date}. What is the current status? Recovery link: {link}",
                "escalate": "We apologize for the inconvenience. We are transferring you to a human support agent.",
                "escalate_holding": "Your request has been noted. A human agent will connect with you shortly."
            },
            "hindi": {
                "pay": "बिल्कुल! आपका सुरक्षित भुगतान लिंक यहाँ है: {link}। कोई समस्या हो तो कृपया बताएं।",
                "churn": "हम समझ गए। क्या आप बता सकते हैं कि क्या समस्या आई? हम आपकी सहायता करना चाहते हैं।",
                "delay": "कोई बात नहीं! हम आपको {date} को याद दिला देंगे। तब तक निश्चिंत रहें।",
                "unclear": "कोई बात नहीं! आपका भुगतान ₹{amount} का था। क्या हम इसे पूरा करने में आपकी सहायता कर सकते हैं?",
                "follow_up_delay": "पिछली बार आपने {last_date} कहा था। क्या स्थिति है? लिंक: {link}",
                "escalate": "माफ़ी चाहते हैं, हम आपको एक human agent से कनेक्ट कर रहे हैं।",
                "escalate_holding": "आपकी रिक्वेस्ट दर्ज कर ली गई है। एक human agent आपसे जल्द ही जुड़ेगा।"
            },
            "hinglish": {
                "pay": "Bilkul! Aapka payment link yahan hai: {link}. Koi problem ho toh batayein.",
                "churn": "Samajh gaye. Kya aap bata sakte hain kya issue tha? Hum help karna chahte hain.",
                "delay": "No problem! Hum {date} ko remind kar denge. Tab tak koi tension nahi.",
                "unclear": "Koi baat nahi! Aapka payment ₹{amount} ka tha. Kya hum help kar sakte hain?",
                "follow_up_delay": "Pichli baar aapne {last_date} ka bola tha. Kya status hai? Link: {link}",
                "escalate": "Maafi chahte hain, hum aapko ek human agent se connect kar rahe hain.",
                "escalate_holding": "Aapki request note kar li gayi hai. Ek human agent aapke paas aa raha hai."
            }
        }

    def detect_language(self, message: str, current_language: str = None) -> str:
        """
        Detects whether incoming message is English, Hindi (Devanagari), or Hinglish.
        Rules:
          - Predominant Devanagari range \u0900-\u097F -> 'hindi'
          - Roman Hindi keywords present -> 'hinglish'
          - English words without Roman Hindi keywords -> 'english'
          - Neutral/ambiguous -> current_language or default 'hinglish'
        """
        if not message or not message.strip():
            return current_language or "hinglish"

        # 1. Check for Devanagari Unicode characters (Hindi script)
        devanagari_chars = [c for c in message if '\u0900' <= c <= '\u097F']
        if len(devanagari_chars) >= 2 or (len(message.strip()) > 0 and len(devanagari_chars) / len(message.strip()) > 0.15):
            return "hindi"

        message_lower = message.lower()
        words = set(re.findall(r'[a-zA-Z]+', message_lower))
        if not words:
            return current_language or "hinglish"

        # Roman Hindi / Hinglish indicator vocabulary
        hinglish_vocab = {
            "kal", "aaj", "parso", "karna", "karni", "karunga", "karungi", "karo", "karein", "karta", "karti",
            "hai", "hain", "ho", "gaya", "gayi", "gaye", "bhejo", "bhejiye", "paisa", "paise", "rupaye",
            "mujhe", "mera", "meri", "mere", "aap", "aapka", "aapki", "hum", "humko", "nahi", "nai", "mat",
            "kyun", "kyu", "kya", "bhai", "yaar", "sir", "thoda", "dena", "dekh", "lo", "bolo", "insaan",
            "banda", "madad", "se", "ko", "par", "pe", "mein", "ka", "ki", "ke", "chahiye", "kuch", "baat",
            "karega", "aayegi", "aayega", "deduct", "kat"
        }

        hinglish_matches = words.intersection(hinglish_vocab)
        if len(hinglish_matches) >= 1:
            return "hinglish"

        # English indicator vocabulary
        english_vocab = {
            "the", "is", "are", "i", "you", "we", "they", "my", "your", "our", "to", "for", "in",
            "on", "at", "please", "send", "link", "payment", "pay", "failed", "money", "card",
            "help", "support", "human", "person", "real", "agent", "connect", "issue", "problem",
            "order", "deducted", "account", "bank", "why", "what", "when", "how", "can", "will",
            "want", "need", "tomorrow", "friday", "monday", "cancel", "not", "working", "hello",
            "hi", "hey", "talk", "representative", "care", "executive", "refund"
        }

        english_matches = words.intersection(english_vocab)
        if len(english_matches) >= 1 or len(words) >= 2:
            return "english"

        # Stick to current session language if available, else default to hinglish
        return current_language or "hinglish"

    def detect_human_escalation(self, message: str) -> bool:
        """Detects if the customer is requesting a human agent / live support."""
        message_lower = message.lower()
        triggers = [
            "human", "real person", "support", "agent", "insaan", "banda",
            "customer care", "representative", "executive", "baat karni",
            "connect me", "live person", "real human", "talk to human",
            "talk to support", "call me", "help me talk", "connect to agent"
        ]
        return any(trigger in message_lower for trigger in triggers)

    def detect_promise(self, message: str) -> dict:
        """Looks for promise patterns and recovery intent across English, Hindi, and Hinglish."""
        message_lower = message.lower()

        has_promise = False
        promised_date = None
        intent = "unclear"
        confidence = 0.5

        # Delay / Scheduling keywords
        delay_keywords = [
            "kal", "tomorrow", "next week", "friday", "monday", "thursday",
            "tuesday", "wednesday", "weekend", "parso", "kal tak", "salary",
            "कल", "परसों", "अगले हफ्ते", "सोमवार", "शुक्रवार"
        ]
        if any(w in message_lower for w in delay_keywords):
            has_promise = True
            intent = "delay"
            confidence = 0.9
            if any(w in message_lower for w in ["kal", "tomorrow", "कल"]):
                promised_date = "tomorrow"
            elif any(w in message_lower for w in ["friday", "शुक्रवार"]):
                promised_date = "friday"
            elif any(w in message_lower for w in ["monday", "सोमवार"]):
                promised_date = "monday"
            elif "salary" in message_lower:
                promised_date = "salary day"
            else:
                promised_date = "next week"

        # Churn keywords
        elif any(w in message_lower for w in ["nahi", "nai", "cancel", "stop", "band", "don't want", "not interested", "नहीं", "रद्द"]):
            intent = "churn"
            confidence = 0.85

        # Pay / Request link keywords
        elif any(w in message_lower for w in [
            "link", "pay", "karta hun", "karti hun", "karo", "bhejo", "kar diya",
            "send link", "send payment link", "how to pay", "make payment",
            "लिंक", "पेमेंट", "भेजें", "भुगतान"
        ]):
            intent = "pay"
            confidence = 0.9

        return {
            "has_promise": has_promise,
            "promised_date": promised_date,
            "intent": intent,
            "confidence": confidence
        }

    def generate_response(self, intent: str, context: dict, language: str = "hinglish") -> str:
        """Returns the pre-defined template filled with context in the specified language."""
        lang_dict = self.templates.get(language, self.templates["hinglish"])
        template = lang_dict.get(intent, lang_dict["unclear"])

        filled = template
        for k, v in context.items():
            filled = filled.replace(f"{{{k}}}", str(v))

        # Clean up any unfilled variables
        filled = re.sub(r'\{.*?\}', '', filled)
        return filled.strip()

    def send_admin_escalation_alert(self, payment_id: str, amount: int, trigger_message: str, transcript: list) -> bool:
        """Dispatches an urgent human escalation email alert to the merchant admin."""
        admin_email = os.getenv("ADMIN_EMAIL", os.getenv("RECEIVING_EMAIL", "jatinbadgal49@gmail.com"))
        subject = f"[ArthRaksha] Human Assistance Required — Payment {payment_id}"

        # Format transcript text
        transcript_lines = []
        for m in transcript:
            role = m.get("role", m.get("from", "user")).upper()
            content = m.get("content", m.get("text", ""))
            ts = m.get("timestamp", "")
            transcript_lines.append(f"[{ts}] {role}: {content}")
        transcript_text = "\n".join(transcript_lines) if transcript_lines else f"Customer: {trigger_message}"

        body = (
            f"URGENT ESCALATION ALERT\n"
            f"==================================================\n"
            f"A customer has explicitly requested live human assistance in chat.\n"
            f"AI automated replies have been FROZEN for this session.\n\n"
            f"Payment ID:        {payment_id}\n"
            f"Amount at Risk:    ₹{amount:,}\n"
            f"Customer Message:  \"{trigger_message}\"\n"
            f"Timestamp:         {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}\n"
            f"Current State:     AWAITING_HUMAN\n\n"
            f"Conversation Transcript So Far:\n"
            f"--------------------------------------------------\n"
            f"{transcript_text}\n"
            f"--------------------------------------------------\n\n"
            f"Action Required:\n"
            f"Please log in to the ArthRaksha Merchant Dashboard to respond as a Human Agent:\n"
            f"http://localhost:8000/dashboard/conversations\n"
        )

        try:
            return self.email_tool.send(
                to=admin_email,
                subject=subject,
                body=body,
                payment_id=payment_id,
                amount=amount
            )
        except Exception as e:
            print(f"[ESCALATION EMAIL ERROR] {e}")
            return False

    def run_conversation(self, event: dict, customer_message: str, sender_role: str = "customer") -> dict:
        """
        Processes a conversation turn with:
          - Role separation (Merchant vs. Customer)
          - Hard loop guard (AI replies frozen in AWAITING_HUMAN state)
          - Adaptive language detection (English, Hindi, Hinglish)
          - Human escalation intent detection with instant admin email notification
        """
        payment_id = event.get('payment_id', 'demo_id')
        amount = event.get('amount', 5000)
        timestamp = datetime.utcnow().isoformat()

        # 1. Load session
        session = self.store.load(payment_id) or {
            "session_id": payment_id,
            "payment_id": payment_id,
            "turn_count": 0,
            "chat_state": "AI_ACTIVE",
            "detected_language": "hinglish",
            "transcript": []
        }

        # 2. BUG #4 FIX: Handle Merchant Role
        if sender_role == "merchant":
            # Merchant is joining/replying: transition to HUMAN_ACTIVE
            session["chat_state"] = "HUMAN_ACTIVE"
            session["transcript"].append({
                "role": "merchant",
                "from": "merchant",
                "content": customer_message,
                "text": customer_message,
                "timestamp": timestamp
            })
            self.store.save(payment_id, session)
            return {
                "customer_message": customer_message,
                "sender_role": "merchant",
                "agent_response": None,
                "chat_state": "HUMAN_ACTIVE",
                "status": "human_active",
                "action": "human_replied"
            }

        # 3. BUG #3 FIX: Hard Loop Guard when AWAITING_HUMAN
        current_chat_state = session.get("chat_state", "AI_ACTIVE")
        if current_chat_state == "AWAITING_HUMAN":
            # AI responses are FROZEN. Hard return — do NOT call LLM or send duplicate template messages!
            session["transcript"].append({
                "role": "customer",
                "from": "user",
                "content": customer_message,
                "text": customer_message,
                "timestamp": timestamp
            })
            self.store.save(payment_id, session)
            return {
                "customer_message": customer_message,
                "sender_role": "customer",
                "agent_response": None,
                "chat_state": "AWAITING_HUMAN",
                "status": "awaiting_human",
                "action": "hold",
                "message": "AI replies are frozen. A human agent has been alerted."
            }

        if current_chat_state == "RESOLVED":
            return {
                "customer_message": customer_message,
                "sender_role": "customer",
                "agent_response": "This support case has been marked as resolved by a support agent.",
                "chat_state": "RESOLVED",
                "status": "resolved",
                "action": "closed"
            }

        # 4. BUG #1 FIX: Adaptive Language Detection
        detected_lang = self.detect_language(customer_message, session.get("detected_language"))
        session["detected_language"] = detected_lang

        # 5. BUG #2 FIX: Detect Human Escalation Intent
        if self.detect_human_escalation(customer_message):
            session["chat_state"] = "AWAITING_HUMAN"
            holding_response = self.templates[detected_lang]["escalate_holding"]

            # Append transcript
            session["transcript"].append({
                "role": "customer",
                "from": "user",
                "content": customer_message,
                "text": customer_message,
                "timestamp": timestamp
            })
            session["transcript"].append({
                "role": "agent",
                "from": "bot",
                "content": holding_response,
                "text": holding_response,
                "timestamp": timestamp
            })
            session["status"] = "awaiting_human"
            self.store.save(payment_id, session)

            # Trigger Admin Email Alert immediately
            self.send_admin_escalation_alert(
                payment_id=payment_id,
                amount=amount,
                trigger_message=customer_message,
                transcript=session["transcript"]
            )

            return {
                "customer_message": customer_message,
                "detected_intent": "human_escalation",
                "agent_response": holding_response,
                "chat_state": "AWAITING_HUMAN",
                "detected_language": detected_lang,
                "action": "escalate_to_human",
                "status": "awaiting_human",
                "admin_notified": True
            }

        # 6. Detect Customer Promise / Payment Intent
        detection = self.detect_promise(customer_message)
        current_intent = detection["intent"]
        template_intent = current_intent

        # Handle Memory (Follow-up)
        if current_intent == "delay" and session.get("last_intent") == "delay":
            template_intent = "follow_up_delay"

        # Handle Stopping Rule (>= 4 turns without resolution -> escalate)
        is_escalated = False
        if session["turn_count"] >= 3 and current_intent not in ["pay"]:
            template_intent = "escalate"
            is_escalated = True
            session["chat_state"] = "AWAITING_HUMAN"

        # 7. Generate Response in Detected Language
        demo_base = os.getenv("DEMO_BASE_URL", "http://localhost:8000")
        context = {
            "link": f"{demo_base}/demo/pay/{payment_id}?amount={amount}",
            "amount": amount,
            "date": detection['promised_date'] or ("tomorrow" if detected_lang == "english" else "kal"),
            "last_date": session.get("last_promised_date") or ("yesterday" if detected_lang == "english" else "kal")
        }

        response = self.generate_response(template_intent, context, language=detected_lang)

        # 8. Update Session State
        session["turn_count"] += 1
        session["last_intent"] = current_intent

        if detection["promised_date"]:
            session["last_promised_date"] = detection["promised_date"]

        if current_intent == "churn":
            session["churn_signal"] = 1

        # Append transcript
        session["transcript"].append({
            "role": "customer",
            "from": "user",
            "content": customer_message,
            "text": customer_message,
            "timestamp": timestamp
        })
        session["transcript"].append({
            "role": "agent",
            "from": "bot",
            "content": response,
            "text": response,
            "timestamp": timestamp
        })

        # Save session or close if resolved
        if is_escalated:
            session["status"] = "awaiting_human"
            self.send_admin_escalation_alert(
                payment_id=payment_id,
                amount=amount,
                trigger_message=customer_message,
                transcript=session["transcript"]
            )
        elif current_intent == "pay" or event.get("outcome") == "recovered":
            session["status"] = "closed"
            if current_intent == "pay":
                session["promise_kept"] = 1

        self.store.save(payment_id, session)

        return {
            "customer_message": customer_message,
            "detected_intent": current_intent,
            "agent_response": response,
            "detected_language": detected_lang,
            "chat_state": session.get("chat_state", "AI_ACTIVE"),
            "promise_created": detection["has_promise"],
            "promised_date": detection["promised_date"],
            "action": "escalate" if is_escalated else "continue",
            "transcript_id": str(uuid.uuid4())
        }
