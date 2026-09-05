import { useState } from "react";
import {
  ChevronLeft, FileText, Zap, Shield, Code as CodeIcon, Server,
  Smartphone, BookOpen, GitBranch, AlertTriangle, CheckCircle
} from "lucide-react";

interface Props {
  onBack: () => void;
}

const SIDEBAR_SECTIONS = [
  {
    title: "Getting Started",
    links: [
      { id: "intro",       label: "Introduction",     icon: BookOpen },
      { id: "quickstart",  label: "Quickstart",        icon: Zap },
      { id: "auth",        label: "Authentication",    icon: Shield },
    ],
  },
  {
    title: "Core Concepts",
    links: [
      { id: "architecture", label: "3-Tier Architecture", icon: Server },
      { id: "taxonomy",     label: "Failure Taxonomy",    icon: GitBranch },
      { id: "compliance",   label: "Compliance Rules",    icon: AlertTriangle },
      { id: "agent",        label: "Hinglish AI Agent",   icon: Smartphone },
    ],
  },
  {
    title: "API Reference",
    links: [
      { id: "webhooks", label: "Webhooks",    icon: CodeIcon },
      { id: "events",   label: "Event Types", icon: FileText },
    ],
  },
];

const H1 = ({ children }: { children: React.ReactNode }) => (
  <h1 style={{ fontSize: 34, fontWeight: 300, marginBottom: 16, letterSpacing: "-0.01em", color: "#fff" }}>
    {children}
  </h1>
);
const H2 = ({ children }: { children: React.ReactNode }) => (
  <h2 style={{ fontSize: 19, fontWeight: 600, marginTop: 40, marginBottom: 14, borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: 8, color: "#fff" }}>
    {children}
  </h2>
);
const P = ({ children }: { children: React.ReactNode }) => (
  <p style={{ fontSize: 14, lineHeight: 1.75, color: "rgba(255,255,255,0.7)", marginBottom: 16 }}>
    {children}
  </p>
);
const Code = ({ children }: { children: React.ReactNode }) => (
  <code style={{ background: "rgba(96,165,250,0.1)", color: "#60A5FA", padding: "2px 6px", borderRadius: 4, fontSize: 13, fontFamily: "monospace" }}>
    {children}
  </code>
);
const Pre = ({ children }: { children: React.ReactNode }) => (
  <pre style={{ background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, padding: 20, overflowX: "auto", fontSize: 12.5, color: "rgba(255,255,255,0.85)", fontFamily: "monospace", lineHeight: 1.6, marginBottom: 24 }}>
    {children}
  </pre>
);
const Badge = ({ color, children }: { color: string; children: React.ReactNode }) => (
  <span style={{ background: color + "22", color, border: `1px solid ${color}44`, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600, marginRight: 6 }}>
    {children}
  </span>
);
const Callout = ({ icon: Icon, color, title, children }: { icon: any; color: string; title: string; children: React.ReactNode }) => (
  <div style={{ border: `1px solid ${color}33`, background: `${color}0d`, borderRadius: 8, padding: "14px 18px", marginBottom: 20, display: "flex", gap: 12 }}>
    <Icon size={16} color={color} style={{ marginTop: 2, flexShrink: 0 }} />
    <div>
      <div style={{ fontWeight: 600, color, fontSize: 13, marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 13, color: "rgba(255,255,255,0.65)", lineHeight: 1.6 }}>{children}</div>
    </div>
  </div>
);

// ─── PAGE CONTENT ─────────────────────────────────────────────────────────────

function PageIntro() {
  return (
    <div>
      <H1>Introduction to ArthRaksha</H1>
      <P>
        ArthRaksha (अर्थरक्षा) is an autonomous payment failure recovery and revenue defense engine
        built for Indian fintech merchants. It sits between your payment gateway (Razorpay) and your
        core systems — intercepting every <Code>payment.failed</Code> webhook, classifying the root
        cause in real time, and dispatching the optimal recovery action without any human intervention.
      </P>
      <P>
        In high-volume payment ecosystems across India's UPI and card rails, <strong style={{ color: "#fff" }}>8–22% of checkout
        attempts fail</strong>. Standard retry loops either bombard customers (violating TRAI regulations)
        or abandon the cart entirely. ArthRaksha recovers up to <strong style={{ color: "#60A5FA" }}>53.2% of at-risk revenue</strong> while
        enforcing strict RBI and TRAI compliance automatically.
      </P>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, margin: "28px 0" }}>
        {[
          { label: "3-Tier Routing", desc: "T1 Auto-Retry · T2 AI Outreach · T3 Escalation", color: "#60A5FA" },
          { label: "Multi-Channel", desc: "Payment Links · Hinglish AI · Email · SMS", color: "#34D399" },
          { label: "Compliance-First", desc: "RBI TAT · TRAI TCCCPR · SHA-256 Audit", color: "#A78BFA" },
        ].map(c => (
          <div key={c.label} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, padding: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: c.color, marginBottom: 6 }}>{c.label}</div>
            <div style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", lineHeight: 1.5 }}>{c.desc}</div>
          </div>
        ))}
      </div>

      <H2>How it works</H2>
      {[
        { n: "1", title: "Ingestion", body: "Your payment gateway sends a payment.failed webhook. ArthRaksha verifies the HMAC-SHA256 signature and enforces idempotency before processing." },
        { n: "2", title: "Classification", body: "The Zero-Guessing Taxonomy Engine parses the error code, failure source (customer / gateway / issuer bank), and transaction step to build a composite risk score (0.0 – 1.0)." },
        { n: "3", title: "Routing", body: "Score < 0.35 → T1 auto-retry. Score 0.35–0.85 → T2 AI engagement (payment link or Hinglish dialogue). Score ≥ 0.85 → T3 immediate human escalation." },
        { n: "4", title: "Recovery", body: "The customer receives a contextual, compliant outreach. Outcomes are written to the tamper-evident audit ledger with SHA-256 hash chaining." },
      ].map(s => (
        <div key={s.n} style={{ display: "flex", gap: 16, marginBottom: 16 }}>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: "rgba(96,165,250,0.15)", border: "1px solid rgba(96,165,250,0.3)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: "#60A5FA", flexShrink: 0 }}>{s.n}</div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#fff", marginBottom: 4 }}>{s.title}</div>
            <div style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", lineHeight: 1.6 }}>{s.body}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function PageQuickstart() {
  return (
    <div>
      <H1>Quickstart</H1>
      <P>Get ArthRaksha running locally in under 5 minutes.</P>

      <H2>Prerequisites</H2>
      <ul style={{ paddingLeft: 20, color: "rgba(255,255,255,0.65)", fontSize: 13, lineHeight: 2 }}>
        <li>Python 3.11+</li>
        <li>Node.js 18+ (for the React dashboard)</li>
        <li>HuggingFace API token (free tier works)</li>
      </ul>

      <H2>1 — Clone & Install</H2>
      <Pre>{`git clone https://github.com/Gyanprakash136/ArthRaksha.git
cd ArthRaksha

# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..`}</Pre>

      <H2>2 — Configure Environment</H2>
      <P>Copy <Code>.env.example</Code> and fill in your credentials:</P>
      <Pre>{`# Agent Brain (LLM for recovery decisions)
LLM_PROVIDER=huggingface
HUGGINGFACEHUB_API_TOKEN=hf_xxxxxxxxxxxx

# Razorpay (test keys from dashboard)
RAZORPAY_KEY=rzp_test_xxxxxxxxxxxx
RAZORPAY_SECRET=xxxxxxxxxxxxxxxxxxxx

# Email notifications
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your@email.com
EMAIL_PASS=your_app_password
RECEIVING_EMAIL=alerts@yourcompany.com

# Database
DATABASE_PATH=data/arthraksha.db
ENVIRONMENT=development`}</Pre>

      <H2>3 — Start the Server</H2>
      <Pre>{`# Start FastAPI backend (port 8000)
uvicorn arthraksha.api.main:app --reload --port 8000

# In a separate terminal — start frontend dev server
cd frontend && npm run dev`}</Pre>

      <H2>4 — Run a Batch Simulation</H2>
      <P>Open the dashboard at <Code>http://localhost:5173</Code>, navigate to <strong style={{ color: "#fff" }}>Overview</strong>, and click <strong style={{ color: "#60A5FA" }}>Run Batch</strong>. This processes 50 events from the 10,000-event synthetic dataset through the full agentic pipeline.</P>

      <Callout icon={CheckCircle} color="#34D399" title="Expected result">
        Within ~10 seconds you'll see recovery metrics populate: T1/T2/T3 event counts,
        recovery rate, revenue recovered, and a live audit trail.
      </Callout>
    </div>
  );
}

function PageAuth() {
  return (
    <div>
      <H1>Authentication</H1>
      <P>
        ArthRaksha uses two separate authentication layers: <strong style={{ color: "#fff" }}>HMAC-SHA256 webhook verification</strong> for
        inbound payment gateway events, and <strong style={{ color: "#fff" }}>session-based merchant login</strong> for the dashboard.
      </P>

      <H2>Webhook Signature Verification</H2>
      <P>
        Every inbound webhook to <Code>POST /webhook/razorpay</Code> is verified against Razorpay's
        HMAC-SHA256 signature before processing. Requests with invalid or missing signatures are
        rejected with <Code>400 Bad Request</Code>.
      </P>
      <Pre>{`# Razorpay signs each webhook with your webhook secret:
X-Razorpay-Signature: sha256=<hmac_hex>

# ArthRaksha verifies:
import hmac, hashlib
expected = hmac.new(
    key=RAZORPAY_SECRET.encode(),
    msg=raw_body,
    digestmod=hashlib.sha256
).hexdigest()
assert hmac.compare_digest(expected, received_signature)`}</Pre>

      <H2>Idempotency Guard</H2>
      <P>
        Every event carries a unique <Code>event_id</Code>. ArthRaksha checks the
        <Code>idempotency_store</Code> table before processing — duplicate events return
        <Code>200 OK</Code> immediately without re-running the pipeline.
      </P>

      <H2>Dashboard Login</H2>
      <P>
        The merchant dashboard uses role-based access. Navigate to <Code>/auth</Code> and log in
        with your merchant credentials. The session is stored in localStorage and validated on each
        API call.
      </P>
      <Pre>{`POST /auth/login
Content-Type: application/json

{
  "email": "merchant@example.com",
  "password": "your_password",
  "role": "merchant"   // or "customer"
}`}</Pre>
      <Callout icon={AlertTriangle} color="#F59E0B" title="Merchant vs Customer mode">
        The dashboard enforces role separation. Batch controls, Case Explorer, and Insights are
        visible in <strong>Merchant mode only</strong>. Customer mode is limited to the payment
        conversation interface.
      </Callout>
    </div>
  );
}

function PageArchitecture() {
  const tiers = [
    {
      name: "Tier 1 — Deterministic Auto-Retry",
      badge: "T1",
      color: "#34D399",
      score: "Risk score < 0.35",
      failures: ["gateway_technical_error", "bank_switch_down", "upi_timeout", "npci_down"],
      strategy: "Jittered exponential backoff aligned with issuing bank recovery windows (HDFC, ICICI, SBI). Zero customer friction or outreach.",
      latency: "< 5 ms",
      cost: "₹0.00",
    },
    {
      name: "Tier 2 — AI Customer Engagement",
      badge: "T2",
      color: "#60A5FA",
      score: "Risk score 0.35 – 0.85",
      failures: ["insufficient_funds", "invalid_otp", "invalid_cvv", "card_expired"],
      strategy: "Semantic cache lookup first (< 5ms). Cache miss → LLM (Qwen-2.5-7B) selects channel: 2-click payment link (78.6% of cases) or multi-turn Hinglish AI dialogue (21.4%).",
      latency: "~850 ms (cached: < 5 ms)",
      cost: "₹0.15 (link) / ₹1.20 (AI chat)",
    },
    {
      name: "Tier 3 — Human Risk Escalation",
      badge: "T3",
      color: "#F87171",
      score: "Risk score ≥ 0.85",
      failures: ["payment_risk_check_failed", "card_declined_suspicious", "stolen_instrument"],
      strategy: "Complete automation freeze. All outreach halted to prevent chargeback liability. Priority SMTP alert to human operations team. Audit record locked.",
      latency: "< 2 ms",
      cost: "₹0.00 (direct)",
    },
  ];

  return (
    <div>
      <H1>3-Tier Architecture</H1>
      <P>
        ArthRaksha uses a <strong style={{ color: "#fff" }}>hybrid deterministic-stochastic state machine</strong>.
        High-frequency technical faults are handled deterministically without LLM calls. Stochastic
        LLM tokens are reserved exclusively for nuanced customer engagement in Tier 2.
      </P>

      {tiers.map(t => (
        <div key={t.badge} style={{ border: `1px solid ${t.color}33`, borderRadius: 10, padding: 20, marginBottom: 20, background: `${t.color}08` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <span style={{ background: t.color + "22", color: t.color, border: `1px solid ${t.color}44`, borderRadius: 6, padding: "3px 10px", fontSize: 12, fontWeight: 700 }}>{t.badge}</span>
            <span style={{ fontSize: 15, fontWeight: 600, color: "#fff" }}>{t.name}</span>
          </div>
          <div style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", marginBottom: 10 }}>{t.score}</div>
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>Failure types handled</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {t.failures.map(f => <code key={f} style={{ background: "rgba(0,0,0,0.3)", color: "rgba(255,255,255,0.7)", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontFamily: "monospace" }}>{f}</code>)}
            </div>
          </div>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.65)", lineHeight: 1.6, marginBottom: 12 }}>{t.strategy}</div>
          <div style={{ display: "flex", gap: 24, fontSize: 12 }}>
            <span><span style={{ color: "rgba(255,255,255,0.4)" }}>Latency: </span><span style={{ color: t.color }}>{t.latency}</span></span>
            <span><span style={{ color: "rgba(255,255,255,0.4)" }}>Cost: </span><span style={{ color: "#fff" }}>{t.cost}</span></span>
          </div>
        </div>
      ))}

      <H2>Semantic Cache (Tier 2)</H2>
      <P>
        Before calling the LLM, Tier 2 performs a cosine-similarity lookup against cached recovery
        directives. If a similar event exists with similarity ≥ 0.92, the cached action is returned
        instantly, saving ~850ms and ~₹1.20 per event.
      </P>
      <Pre>{`Cache Hit  → < 5ms,  ₹0.00  (reuse prior LLM decision)
Cache Miss → ~850ms, ₹0.15–₹1.20  (new LLM call + cache write)`}</Pre>
    </div>
  );
}

function PageTaxonomy() {
  return (
    <div>
      <H1>Failure Taxonomy</H1>
      <P>
        Rather than letting a generative model guess the cause of a payment failure, ArthRaksha
        applies a <strong style={{ color: "#fff" }}>Zero-Guessing Taxonomy Engine</strong> that parses
        the Razorpay error payload across three structured dimensions.
      </P>

      <H2>Classification Dimensions</H2>
      {[
        {
          title: "1. Error Classification",
          items: [
            { code: "BAD_REQUEST_ERROR", desc: "Customer-side issue — wrong OTP, expired card, insufficient funds" },
            { code: "GATEWAY_ERROR", desc: "Payment processor fault — acquirer timeout, routing failure" },
            { code: "SERVER_ERROR", desc: "Internal system error — Razorpay or bank infrastructure down" },
          ],
        },
        {
          title: "2. Failure Source",
          items: [
            { code: "customer", desc: "Customer initiated the wrong action or lacks funds" },
            { code: "gateway", desc: "Acquirer / processor failed to route the transaction" },
            { code: "issuer_bank", desc: "Customer's bank or NPCI is unavailable" },
          ],
        },
        {
          title: "3. Transaction Step",
          items: [
            { code: "payment_initiation", desc: "Failed before the authorization request was sent" },
            { code: "payment_authorization", desc: "Bank rejected the authorization" },
            { code: "payment_authentication", desc: "3DS / OTP challenge failed" },
          ],
        },
      ].map(section => (
        <div key={section.title} style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#fff", marginBottom: 12 }}>{section.title}</div>
          {section.items.map(item => (
            <div key={item.code} style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 10 }}>
              <code style={{ background: "rgba(96,165,250,0.1)", color: "#60A5FA", padding: "3px 8px", borderRadius: 4, fontSize: 12, fontFamily: "monospace", flexShrink: 0 }}>{item.code}</code>
              <span style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", lineHeight: 1.5 }}>{item.desc}</span>
            </div>
          ))}
        </div>
      ))}

      <H2>Composite Risk Score</H2>
      <P>
        ArthRaksha combines error class, failure source, transaction step, customer LTV, and
        historical payment behaviour into a single composite risk score (0.0–1.0) to route events
        to the correct tier.
      </P>
      <Pre>{`risk_score = weighted_sum(
  error_class_weight    * 0.35,  # BAD_REQUEST=low, SERVER_ERROR=high
  failure_source_weight * 0.25,  # customer < gateway < issuer
  fraud_signal_weight   * 0.30,  # risk_check_failed bumps to 0.85+
  ltv_modifier          * 0.10   # high-LTV customers get T2 preference
)`}</Pre>
    </div>
  );
}

function PageCompliance() {
  return (
    <div>
      <H1>Compliance Rules</H1>
      <P>
        ArthRaksha enforces Indian financial and telecom regulations programmatically on every
        recovery action — no manual configuration required.
      </P>

      <H2>TRAI TCCCPR (2018) — Contact Restrictions</H2>
      <Callout icon={AlertTriangle} color="#F59E0B" title="Automatic curfew enforcement">
        All automated outreach is programmatically blocked between <strong>21:00 – 09:00 IST</strong>.
        Events queued during this window are held and dispatched at 09:01 IST the following morning.
      </Callout>
      <ul style={{ paddingLeft: 20, color: "rgba(255,255,255,0.65)", fontSize: 13, lineHeight: 2.2 }}>
        <li>Maximum <strong style={{ color: "#fff" }}>2 customer contacts per 24-hour period</strong></li>
        <li>Minimum <strong style={{ color: "#fff" }}>4-hour cooldown</strong> between consecutive messages</li>
        <li>Violation detection automatically locks the payment ID from further outreach</li>
      </ul>

      <H2>RBI TAT Circular (DPSS.629)</H2>
      <P>
        Auto-retry windows and reversal timings for UPI and IMPS transactions adhere to
        Reserve Bank of India authorized turnaround times. The T1 exponential backoff
        schedules are bank-specific (HDFC, ICICI, SBI, Axis) to align with known
        infrastructure recovery windows.
      </P>

      <H2>Promise-to-Pay Expiry</H2>
      <P>
        When a customer commits to pay at a future time (e.g., <em style={{ color: "rgba(255,255,255,0.5)" }}>"Kal salary aayegi"</em>),
        ArthRaksha monitors the ledger for fulfillment. After 24 hours of non-payment:
      </P>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
        <div style={{ background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.2)", borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#34D399", marginBottom: 8 }}>Amount ≥ ₹2,500 or LTV ≥ ₹10,000</div>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.6)" }}>Escalate to Human Ops — case assigned to a recovery specialist.</div>
        </div>
        <div style={{ background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.2)", borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#F87171", marginBottom: 8 }}>Amount &lt; ₹2,500</div>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.6)" }}>Auto write-off — human intervention cost (₹60–₹120/ticket) exceeds expected recovery margin.</div>
        </div>
      </div>

      <H2>SHA-256 Tamper-Evident Audit Chain</H2>
      <P>
        Every state transition in the recovery ledger is chained with a SHA-256 block hash,
        creating an immutable compliance audit trail.
      </P>
      <Pre>{`block_hash = SHA256(
  prev_hash + payment_id + agent_tier + action_taken + timestamp
)`}</Pre>
      <P>Any tampering with a historical record invalidates all subsequent hashes, making unauthorized modification detectable.</P>
    </div>
  );
}

function PageAgent() {
  return (
    <div>
      <H1>Hinglish AI Agent</H1>
      <P>
        The Tier 2 conversational AI speaks to customers in their natural language — pure English,
        pure Hindi, or code-mixed Hinglish — without any manual language selection. It handles
        multi-turn negotiation, promise-to-pay scheduling, and payment link delivery.
      </P>

      <H2>Language Detection</H2>
      <P>
        Language is detected automatically using Unicode script analysis and keyword frequency
        scoring — no external NLP API required.
      </P>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 24 }}>
        {[
          { lang: "English", example: "I can't pay right now, my card is declined", color: "#60A5FA" },
          { lang: "Hindi", example: "मेरे अकाउंट में पैसे नहीं हैं", color: "#34D399" },
          { lang: "Hinglish", example: "Yaar meri card decline ho gayi, kya karu?", color: "#A78BFA" },
        ].map(l => (
          <div key={l.lang} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, padding: 14 }}>
            <Badge color={l.color}>{l.lang}</Badge>
            <div style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", marginTop: 8, fontStyle: "italic", lineHeight: 1.5 }}>"{l.example}"</div>
          </div>
        ))}
      </div>

      <H2>Conversation Flow</H2>
      {[
        { role: "Agent", msg: "Namaste! Aapka ₹4,999 ka payment process nahi hua. Kya aap ek secure payment link use karna chahenge?" },
        { role: "Customer", msg: "Kal salary aayegi, tab kar sakta hoon?" },
        { role: "Agent", msg: "Bilkul! Hum kal 10 AM ko aapko reminder bhejenge. Kya yeh theek hai?" },
      ].map((m, i) => (
        <div key={i} style={{ display: "flex", gap: 12, marginBottom: 12, flexDirection: m.role === "Customer" ? "row-reverse" : "row" }}>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: m.role === "Agent" ? "rgba(96,165,250,0.2)" : "rgba(52,211,153,0.2)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, color: m.role === "Agent" ? "#60A5FA" : "#34D399", flexShrink: 0 }}>
            {m.role[0]}
          </div>
          <div style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "rgba(255,255,255,0.75)", lineHeight: 1.6, maxWidth: "75%" }}>
            {m.msg}
          </div>
        </div>
      ))}

      <H2>Key Capabilities</H2>
      <ul style={{ paddingLeft: 20, color: "rgba(255,255,255,0.65)", fontSize: 13, lineHeight: 2.2 }}>
        <li>Multi-turn dialogue with session memory across conversation turns</li>
        <li>Promise-to-pay recording and automatic 24h follow-up scheduling</li>
        <li>2-click secure payment link generation and delivery</li>
        <li>Automatic escalation to human agent when sentiment is negative or complexity is high</li>
        <li>TRAI curfew awareness — no messages sent between 21:00–09:00 IST</li>
      </ul>
    </div>
  );
}

function PageWebhooks() {
  return (
    <div>
      <H1>Webhooks</H1>
      <P>
        Configure your Razorpay dashboard to send <Code>payment.failed</Code> events to the
        ArthRaksha ingestion endpoint. All events are verified, deduplicated, and queued for
        agentic processing.
      </P>

      <H2>Ingestion Endpoint</H2>
      <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: 16, marginBottom: 24 }}>
        <div style={{ fontSize: 11, color: "#8f8f93", marginBottom: 6, fontFamily: "monospace" }}>Production</div>
        <code style={{ fontSize: 14, color: "#60A5FA", fontFamily: "monospace" }}>POST /webhook/razorpay</code>
        <div style={{ marginTop: 12, fontSize: 11, color: "#8f8f93", fontFamily: "monospace" }}>Test / Development</div>
        <code style={{ fontSize: 14, color: "#34D399", fontFamily: "monospace" }}>POST /webhook/test</code>
      </div>

      <H2>Razorpay Webhook Payload</H2>
      <Pre>{`{
  "entity": "event",
  "event": "payment.failed",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_abc123xyz",
        "amount": 499900,
        "currency": "INR",
        "status": "failed",
        "error_code": "BAD_REQUEST_ERROR",
        "error_description": "Payment failed due to insufficient funds",
        "error_source": "customer",
        "error_step": "payment_authorization",
        "error_reason": "insufficient_funds",
        "contact": "+919876543210",
        "email": "customer@example.com"
      }
    }
  }
}`}</Pre>

      <H2>Test Endpoint Payload</H2>
      <P>The <Code>/webhook/test</Code> endpoint accepts a simplified payload for development:</P>
      <Pre>{`{
  "event_id": "evt_abc123",
  "payment_id": "pay_abc123",
  "amount": 4999,
  "currency": "INR",
  "error_code": "insufficient_funds",
  "error_description": "Payment failed due to insufficient funds",
  "customer": {
    "name": "Priya Sharma",
    "email": "priya@example.com",
    "phone": "+919876543210",
    "bank_issuer": "HDFC",
    "months_subscribed": 8,
    "ltv_estimate": 35940
  },
  "complexity_score": 0.45,
  "recovery_probability": 0.72
}`}</Pre>

      <H2>Response</H2>
      <Pre>{`{
  "payment_id": "pay_abc123",
  "final_outcome": "recovered",
  "agent_tier": "T2",
  "audit_trail": [
    {
      "timestamp": "2026-09-05T08:30:00Z",
      "action_taken": "payment_link_sent",
      "action_reason": "insufficient_funds: customer routed to 2-click payment link",
      "outcome": "recovered",
      "agent_tier": "T2",
      "cache_hit": false,
      "tokens_used": 312
    }
  ]
}`}</Pre>
    </div>
  );
}

function PageEvents() {
  const events = [
    { code: "insufficient_funds",           tier: "T2", color: "#60A5FA", desc: "Customer account balance too low to cover the transaction amount." },
    { code: "card_expired",                 tier: "T2", color: "#60A5FA", desc: "Card expiry date has passed. Agent prompts for alternate card or UPI." },
    { code: "invalid_cvv",                  tier: "T2", color: "#60A5FA", desc: "CVV mismatch. Customer redirected to retry with correct credentials." },
    { code: "invalid_otp",                  tier: "T2", color: "#60A5FA", desc: "OTP entered incorrectly or expired. New payment link generated." },
    { code: "upi_timeout",                  tier: "T1", color: "#34D399", desc: "UPI collect request timed out. Auto-retried with jittered backoff." },
    { code: "gateway_technical_error",      tier: "T1", color: "#34D399", desc: "Acquirer / gateway processing failure. Retried automatically." },
    { code: "bank_switch_down",             tier: "T1", color: "#34D399", desc: "Issuing bank switch temporarily unavailable. Queued for retry." },
    { code: "npci_down",                    tier: "T1", color: "#34D399", desc: "NPCI infrastructure outage. Auto-retry after 15-minute window." },
    { code: "payment_risk_check_failed",    tier: "T3", color: "#F87171", desc: "Fraud risk score threshold breached. All automation halted immediately." },
    { code: "card_declined_suspicious",     tier: "T3", color: "#F87171", desc: "Unusual card usage pattern detected. Human review required." },
    { code: "stolen_instrument_reported",   tier: "T3", color: "#F87171", desc: "Card or UPI instrument flagged as stolen. Case locked for compliance." },
  ];

  return (
    <div>
      <H1>Event Types</H1>
      <P>
        ArthRaksha recognizes the following error codes from the Razorpay failure payload. Each
        code maps deterministically to a recovery tier — no LLM classification is used for routing.
      </P>

      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <Badge color="#34D399">T1 — Auto Retry</Badge>
        <Badge color="#60A5FA">T2 — AI Engagement</Badge>
        <Badge color="#F87171">T3 — Human Escalation</Badge>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {events.map(e => (
          <div key={e.code} style={{ display: "flex", alignItems: "center", gap: 14, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, padding: "12px 16px" }}>
            <span style={{ background: e.color + "22", color: e.color, border: `1px solid ${e.color}33`, borderRadius: 4, padding: "2px 7px", fontSize: 10, fontWeight: 700, flexShrink: 0, width: 22, textAlign: "center" }}>{e.tier}</span>
            <code style={{ color: "rgba(255,255,255,0.85)", fontSize: 12, fontFamily: "monospace", width: 240, flexShrink: 0 }}>{e.code}</code>
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", lineHeight: 1.5 }}>{e.desc}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── PAGE MAP ─────────────────────────────────────────────────────────────────

const PAGE_MAP: Record<string, React.ReactNode> = {
  intro:        <PageIntro />,
  quickstart:   <PageQuickstart />,
  auth:         <PageAuth />,
  architecture: <PageArchitecture />,
  taxonomy:     <PageTaxonomy />,
  compliance:   <PageCompliance />,
  agent:        <PageAgent />,
  webhooks:     <PageWebhooks />,
  events:       <PageEvents />,
};

// ─── SHELL ────────────────────────────────────────────────────────────────────

export default function Docs({ onBack }: Props) {
  const [activePage, setActivePage] = useState("intro");

  const activeLabel = SIDEBAR_SECTIONS
    .flatMap(s => s.links)
    .find(l => l.id === activePage)?.label ?? "";

  return (
    <div style={{ display: "flex", height: "100vh", background: "#070708", color: "#fff", fontFamily: "Inter, sans-serif", overflow: "hidden" }}>

      {/* ── SIDEBAR ── */}
      <aside style={{ width: 264, borderRight: "1px solid rgba(255,255,255,0.07)", display: "flex", flexDirection: "column", background: "rgba(255,255,255,0.015)", flexShrink: 0 }}>

        <div style={{ padding: "18px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", gap: 10 }}>
          <button onClick={onBack} style={{ background: "transparent", border: "none", color: "#8f8f93", cursor: "pointer", display: "flex", alignItems: "center", padding: 0 }}>
            <ChevronLeft size={18} />
          </button>
          <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: "0.02em" }}>Documentation</div>
        </div>

        <nav style={{ flex: 1, padding: "20px 12px", overflowY: "auto", display: "flex", flexDirection: "column", gap: 24 }}>
          {SIDEBAR_SECTIONS.map((section, idx) => (
            <div key={idx}>
              <div style={{ fontSize: 10, fontWeight: 700, color: "#8f8f93", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 8, paddingLeft: 8 }}>
                {section.title}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {section.links.map(link => {
                  const isActive = activePage === link.id;
                  return (
                    <button
                      key={link.id}
                      onClick={() => setActivePage(link.id)}
                      style={{
                        display: "flex", alignItems: "center", gap: 10,
                        padding: "8px 10px", borderRadius: 6,
                        background: isActive ? "rgba(96,165,246,0.12)" : "transparent",
                        border: "none", cursor: "pointer", textAlign: "left",
                        color: isActive ? "#60A5FA" : "rgba(255,255,255,0.55)",
                        transition: "all 0.12s ease", width: "100%"
                      }}
                    >
                      <link.icon size={13} />
                      <span style={{ fontSize: 13, fontWeight: isActive ? 500 : 400 }}>{link.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      {/* ── CONTENT ── */}
      <main style={{ flex: 1, overflowY: "auto", padding: "52px 72px" }}>
        <div style={{ maxWidth: 740, margin: "0 auto" }}>

          {/* Breadcrumb */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#8f8f93", marginBottom: 28 }}>
            <span>Docs</span>
            <span>/</span>
            <span style={{ color: "#60A5FA" }}>{activeLabel}</span>
          </div>

          {PAGE_MAP[activePage] ?? null}

        </div>
      </main>
    </div>
  );
}
