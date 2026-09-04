import sys

def replace_all(file_path):
    with open(file_path, "r") as f:
        content = f.read()
        
    replacements = {
        "AI Recovery Intelligence · India": "Enterprise Payment Recovery · India",
        
        "The intelligence<br />\n              that{\" \"}\n              <span style={{ color: \"#1954ec\" }}>recovers</span><br />\n              what India's<br />\n              payments lose.": "Intelligent<br />\n              Revenue<br />\n              <span style={{ color: \"#1954ec\" }}>Recovery</span><br />\n              for Enterprise<br />\n              India.",
        
        "ArthRaksha deploys three-tier AI agents — rule engines, language models, human specialists — to recover failed transactions at scale, in Hinglish, at speed.": "Stop losing revenue to failed transactions. ArthRaksha combines deterministic routing, conversational AI, and human-in-the-loop workflows to recover dropped payments at scale—while preserving customer trust.",
        
        "Recovery Metrics · Batch Average": "Platform Performance Metrics",
        
        "A three-tier<br />\n              recovery<br />\n              engine.": "Revenue<br />\n              recovery,<br />\n              engineered<br />\n              for scale.",
        
        "Recovery is not a single event. ArthRaksha routes each failed payment through a tiered decision engine — beginning with instant rule-based logic, escalating to language model reasoning, and ending with specialist human judgment when capital justifies it.": "Every failed transaction is unique. ArthRaksha intelligently routes failures through a dynamic decision matrix. From instant retries to culturally-calibrated conversational negotiations, we ensure every salvageable payment is captured.",
        
        "The system learns continuously, warming a semantic cache that reduces token cost with every processed batch.": "Our infrastructure learns continuously, optimizing recovery paths and reducing operational overhead with every processed batch.",
        
        "stage: \"T1\", name: \"Auto.\", tag: \"Rule Engine\",": "stage: \"T1\", name: \"Deterministic.\", tag: \"Automated Retry Engine\",",
        
        "Classifies payment failures within milliseconds using deterministic logic. BAD_REQUEST_ERROR, GATEWAY_ERROR, INSUFFICIENT_FUNDS — each carries a resolution template that fires without LLM cost. 40% of all cases close at this tier.": "Instantly processes low-complexity failures like insufficient funds or temporary gateway timeouts. Resolves standard declines with zero latency and high precision. 40% of standard drops are recovered instantly.",
        
        "stage: \"T2\", name: \"LLM.\", tag: \"Language Intelligence\",": "stage: \"T2\", name: \"Conversational.\", tag: \"AI Voice & Chat Agents\",",
        
        "When heuristics are insufficient, a large language model evaluates customer intent, payment history, and error context. It drafts a Hinglish message — conversational, culturally calibrated — and dispatches a WhatsApp payment link. 78% of T2 cases resolve within the first contact.": "Deploys empathetic, context-aware AI agents that engage customers in natural Hinglish. By understanding the context behind the drop, our agents negotiate alternative payment methods securely. 78% resolution on first contact.",
        
        "stage: \"T3\", name: \"Human.\", tag: \"Specialist Escalation\",": "stage: \"T3\", name: \"Specialist.\", tag: \"Human-in-the-Loop\",",
        
        "High-value disputes and intentional non-payment require human judgment. The case arrives fully annotated: error timeline, AI confidence scores, conversation transcript, suggested negotiation strategy. The agent inherits context, not chaos.": "Seamlessly escalates high-ticket or high-risk transactions to human specialists. Specialists inherit full conversation context, intent analysis, and recommended negotiation strategies to close the loop securely.",
        
        "Powered by Razorpay Webhook Intelligence": "Powered by Advanced Razorpay Intelligence"
    }
    
    for old, new in replacements.items():
        if old not in content:
            print(f"Warning: Could not find substring: {old[:50]}...")
        content = content.replace(old, new)
        
    with open(file_path, "w") as f:
        f.write(content)

replace_all("frontend/src/pages/Landing.tsx")
print("Done.")
