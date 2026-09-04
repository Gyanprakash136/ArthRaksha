import { useState, useEffect } from "react";
import { useFetch } from "../hooks/useFetch";
import { CheckCircle2, AlertCircle, Clock, MessageSquareOff, ShieldAlert, User, Briefcase, RefreshCw, Send, Sparkles, Activity, FileText, ChevronDown, ChevronUp } from "lucide-react";
import EmptyState from "../components/EmptyState";

interface PromiseEntry {
  customer_name: string;
  promised_amount: number;
  promised_date: string;
  status: string;
  reminder_sent: number;
}

const ST_COLOR: Record<string, string> = {
  promise: "#F59E0B",
  recovered: "#22C55E",
  escalated: "#EF4444",
  kept: "#22C55E",
  broken: "#EF4444",
  pending: "#F59E0B",
  awaiting_human: "#F59E0B",
  human_active: "#10B981",
  resolved: "#6B7280",
};

const ST_BG: Record<string, string> = {
  promise: "#FFFBEB",
  recovered: "#F0FDF4",
  escalated: "#FEF2F2",
  kept: "#F0FDF4",
  broken: "#FEF2F2",
  pending: "#FFFBEB",
  awaiting_human: "#FFFBEB",
  human_active: "#ECFDF5",
  resolved: "#F3F4F6",
};

export default function Hinglish() {
  const { data: convosData, loading: convosLoading, refetch } = useFetch("/dashboard/conversations");
  const { data: promises, refetch: refetchPromises } = useFetch("/dashboard/promise-tracker");
  const [active, setActive] = useState<string | null>(null);
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
  const [senderRole, setSenderRole] = useState<"customer" | "merchant">("merchant");
  const [showTelemetry, setShowTelemetry] = useState(true);
  const [localMessages, setLocalMessages] = useState<Record<string, any[]>>({});

  const HINGLISH_CONVOS = (convosData || []) as any[];

  useEffect(() => {
    if (HINGLISH_CONVOS.length > 0 && !active) {
      setActive(HINGLISH_CONVOS[0].id);
    }
  }, [HINGLISH_CONVOS, active]);

  if (!convosLoading && (!HINGLISH_CONVOS || HINGLISH_CONVOS.length === 0)) {
    return (
      <div style={{ padding: 18, height: "calc(100vh - 52px - 36px)" }}>
        <EmptyState
          icon={MessageSquareOff}
          title="No active AI conversations"
          description="Run an AI batch to trigger Hinglish voice recovery agents. Transcripts will appear here in real-time."
        />
      </div>
    );
  }

  const convo = HINGLISH_CONVOS.find((c) => c.id === active) || HINGLISH_CONVOS[0];
  if (!convo) return null;

  const activeMessages = localMessages[convo.id] || convo.messages || [];
  const chatState = convo.chat_state || "AI_ACTIVE";
  const detectedLang = convo.detected_language || "hinglish";
  const telemetry = convo.telemetry || {
    error_code: "gateway_timeout",
    error_explanation: "NPCI UPI Gateway switch did not respond within 30s timeout window.",
    bank_issuer: "HDFC Bank (UPI)",
    attempts: 2,
    agent_tier: "T2 (Customer AI)",
    customer_phone: "+91 98765 43210",
    customer_email: `cust_${(convo.payment_id || "0000").slice(-4)}@gmail.com`,
    ltv_estimate: (convo.amount || 5000) * 4,
    months_subscribed: 8,
    activity_logs: [
      { action: "Initial Payment Drop-off", reason: "Checkout failed on HDFC Bank UPI via gateway_timeout.", timestamp: "T-15m" },
      { action: "Tier 1: Jittered Retries", reason: "2 automated non-blocking switch retries attempted. Result: timeout.", timestamp: "T-12m" },
      { action: "Tier 2: Recovery Link Sent", reason: "Personalized 2-click recovery link dispatched via SMS.", timestamp: "T-8m" },
      { action: "Conversational Escalation", reason: "Customer entered chat and requested human agent.", timestamp: "T-3m" }
    ],
    diagnostic_briefing: `Payment of ₹${convo.amount?.toLocaleString("en-IN")} failed on HDFC Bank (UPI) via 'gateway_timeout'. 2 automated retries failed before customer entered chat. Do not ask what went wrong—acknowledge the HDFC Bank (UPI) timeout directly.`,
    suggested_replies: [
      `Hello ${convo.customer}! I can see your HDFC Bank (UPI) transaction of ₹${convo.amount?.toLocaleString("en-IN")} timed out on our gateway switch. Let me verify if funds were debited from your account.`,
      `I see the gateway_timeout error on your HDFC Bank (UPI) payment. Don't worry, your order is reserved and here is a fresh 1-click retry link: http://localhost:8000/demo/pay/${convo.payment_id}?amount=${convo.amount}`,
      `I checked our switch logs: the transaction failed before debit occurred. You can safely complete the payment now without any risk of double charge.`
    ]
  };

  const handleSendMessage = async (customText?: string) => {
    const textToSend = (customText || inputText).trim();
    if (!textToSend || sending) return;
    setInputText("");
    setSending(true);

    const isMerchant = senderRole === "merchant";
    const userMsg = {
      from: isMerchant ? "merchant" : "user",
      text: textToSend,
      role: isMerchant ? "merchant" : "customer",
      content: textToSend,
      timestamp: new Date().toISOString()
    };

    setLocalMessages((prev) => ({
      ...prev,
      [convo.id]: [...(prev[convo.id] || convo.messages || []), userMsg]
    }));

    try {
      const targetId = convo.payment_id || convo.id;
      const res = await fetch(`/dashboard/conversations/${targetId}/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: textToSend,
          sender_role: senderRole
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.agent_response) {
          const botMsg = {
            from: "bot",
            text: data.agent_response,
            role: "agent",
            content: data.agent_response,
            timestamp: new Date().toISOString()
          };
          setLocalMessages((prev) => ({
            ...prev,
            [convo.id]: [...(prev[convo.id] || []), botMsg]
          }));
        }
        if (refetch) refetch();
        if (refetchPromises) refetchPromises();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSending(false);
    }
  };

  const handleResolveCase = async () => {
    try {
      const targetId = convo.payment_id || convo.id;
      await fetch(`/dashboard/conversations/${targetId}/resolve`, { method: "POST" });
      if (refetch) refetch();
    } catch (e) {
      console.error(e);
    }
  };

  const handleResetAI = async () => {
    try {
      const targetId = convo.payment_id || convo.id;
      await fetch(`/dashboard/conversations/${targetId}/reset-ai`, { method: "POST" });
      if (refetch) refetch();
    } catch (e) {
      console.error(e);
    }
  };

  const renderMessageContent = (text: string) => {
    const urlMatch = text.match(/(https?:\/\/[^\s]+)/);
    if (!urlMatch) return <span>{text}</span>;

    const url = urlMatch[0];
    const parts = text.split(url);

    return (
      <div>
        <span>{parts[0]}</span>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: "#93C5FD", textDecoration: "underline", wordBreak: "break-all" }}
        >
          {url}
        </a>
        <span>{parts[1]}</span>
        {url.includes("/demo/pay/") && (
          <div style={{ marginTop: 8 }}>
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 12px",
                background: "#22C55E",
                color: "white",
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 700,
                textDecoration: "none",
                boxShadow: "0 2px 4px rgba(0,0,0,0.15)"
              }}
            >
              💳 Pay ₹{convo.amount.toLocaleString("en-IN")} Now
            </a>
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ padding: 18, display: "flex", gap: 12, height: "calc(100vh - 52px - 36px)" }}>

      {/* ── Left: conversation list ── */}
      <div style={{
        width: 278, flexShrink: 0,
        background: "var(--card)", borderRadius: "var(--radius)",
        border: "1px solid var(--border)", boxShadow: "var(--shadow)",
        display: "flex", flexDirection: "column", overflow: "hidden",
      }}>
        <div style={{ padding: "14px 14px 10px", borderBottom: "1px solid var(--border)" }}>
          <div className="jakarta" style={{ fontSize: 13, fontWeight: 700, color: "var(--fg)" }}>Conversations</div>
          <div style={{ fontSize: 9.5, color: "var(--fg-2)", marginTop: 2 }}>
            {HINGLISH_CONVOS.length} active sessions · Diagnostic Aware
          </div>
        </div>

        <div style={{ flex: 1, overflowY: "auto" }}>
          {HINGLISH_CONVOS.map((c) => {
            const st = c.chat_state || c.status || "active";
            return (
              <button
                key={c.id}
                onClick={() => setActive(c.id)}
                style={{
                  width: "100%", textAlign: "left", padding: "11px 13px",
                  border: "none", cursor: "pointer",
                  background: active === c.id ? "var(--blue-lt)" : "transparent",
                  borderBottom: "1px solid var(--border)", transition: "background 0.15s",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "var(--fg)" }}>{c.customer}</div>
                  <div style={{ fontSize: 9, color: "var(--fg-3)" }}>{c.time}</div>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 4 }}>
                  <div style={{ fontSize: 10.5, color: "var(--fg-2)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                    {c.preview}
                  </div>
                  <div style={{
                    fontSize: 8.5, padding: "1px 5px", borderRadius: 4, flexShrink: 0,
                    background: ST_BG[st] ?? "rgba(0,0,0,0.04)",
                    color: ST_COLOR[st] ?? "var(--fg-3)",
                    fontWeight: 600,
                  }}>
                    {st === "AWAITING_HUMAN" ? "Awaiting Human" : st}
                  </div>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 2 }}>
                  <span className="jakarta" style={{ fontSize: 10.5, color: active === c.id ? "var(--blue)" : "var(--fg-3)", fontWeight: 700 }}>
                    ₹{c.amount.toLocaleString("en-IN")}
                  </span>
                  <span style={{ fontSize: 8.5, color: "var(--fg-3)", textTransform: "capitalize" }}>
                    🌐 {c.detected_language || "hinglish"}
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Promise Tracker mini-list */}
        <div style={{ borderTop: "1px solid var(--border)", padding: "10px 13px" }}>
          <div style={{ fontSize: 9, fontWeight: 600, color: "var(--fg-3)", letterSpacing: "0.08em", marginBottom: 7 }}>
            PROMISE TRACKER
          </div>
          {(promises as PromiseEntry[] || []).slice(0, 3).map((p, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
              {p.status === "kept"
                ? <CheckCircle2 size={11} color="#22C55E" />
                : p.status === "broken"
                ? <AlertCircle size={11} color="#EF4444" />
                : <Clock size={11} color="#F59E0B" />}
              <span style={{ fontSize: 10.5, color: "var(--fg)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {p.customer_name}
              </span>
              <span className="jakarta" style={{ fontSize: 10, fontWeight: 700, color: "var(--fg-2)" }}>
                ₹{p.promised_amount.toLocaleString("en-IN")}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right: Chat window ── */}
      <div style={{
        flex: 1,
        background: "var(--card)", borderRadius: "var(--radius)",
        border: "1px solid var(--border)", boxShadow: "var(--shadow)",
        display: "flex", flexDirection: "column", overflow: "hidden",
      }}>

        {/* Chat header */}
        <div style={{
          padding: "12px 18px", borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 34, height: 34, borderRadius: "50%",
              background: "linear-gradient(135deg, #3B82F6, #1D4ED8)",
              display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}>
              <span style={{ color: "white", fontSize: 13, fontWeight: 700 }}>{convo.customer[0]}</span>
            </div>
            <div>
              <div className="jakarta" style={{ fontSize: 14, fontWeight: 700, color: "var(--fg)" }}>{convo.customer}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                <span className="mono" style={{ fontSize: 9.5, color: "var(--fg-2)" }}>{convo.payment_id}</span>
                <span style={{ color: "var(--fg-3)" }}>·</span>
                <span className="jakarta" style={{ fontSize: 11, fontWeight: 700, color: "var(--blue)" }}>
                  ₹{convo.amount.toLocaleString("en-IN")}
                </span>
                <span style={{ color: "var(--fg-3)" }}>·</span>
                {/* Language Tag */}
                <span style={{
                  fontSize: 9, padding: "1px 6px", borderRadius: 4,
                  background: "rgba(59,130,246,0.1)", color: "var(--blue)", fontWeight: 600
                }}>
                  🌐 {detectedLang.toUpperCase()}
                </span>
                {/* Chat State Badge */}
                <span style={{
                  fontSize: 9, padding: "1px 7px", borderRadius: 4,
                  background: ST_BG[chatState] || "rgba(0,0,0,0.04)",
                  color: ST_COLOR[chatState] || "var(--fg-3)",
                  fontWeight: 700,
                  border: `1px solid ${ST_COLOR[chatState]}33`
                }}>
                  {chatState === "AWAITING_HUMAN" ? "⏳ AWAITING HUMAN (AI FROZEN)" :
                   chatState === "HUMAN_ACTIVE" ? "👔 HUMAN AGENT ACTIVE" :
                   chatState === "RESOLVED" ? "✓ RESOLVED" : "🤖 AI ACTIVE"}
                </span>
              </div>
            </div>
          </div>

          {/* Right Header Actions: Role Selector, Telemetry Toggle, Case Controls */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {/* Toggle Telemetry Drawer Button - MERCHANT ONLY */}
            {senderRole === "merchant" && (
              <button
                onClick={() => setShowTelemetry(!showTelemetry)}
                style={{
                  padding: "4px 9px", borderRadius: 6,
                  border: "1px solid rgba(16,185,129,0.3)",
                  background: showTelemetry ? "rgba(16,185,129,0.12)" : "transparent",
                  color: "#10B981", fontSize: 10, fontWeight: 700, cursor: "pointer",
                  display: "flex", alignItems: "center", gap: 5
                }}
              >
                <Activity size={12} /> {showTelemetry ? "Hide Failure Telemetry" : "View Failure Telemetry"}
                {showTelemetry ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
              </button>
            )}

            {/* Mode Switcher Toggle */}
            <div style={{
              display: "flex", background: "rgba(0,0,0,0.04)", padding: 2, borderRadius: 6,
              border: "1px solid var(--border)"
            }}>
              <button
                onClick={() => setSenderRole("customer")}
                style={{
                  padding: "4px 8px", borderRadius: 5, border: "none", cursor: "pointer",
                  fontSize: 10, fontWeight: 600,
                  background: senderRole === "customer" ? "white" : "transparent",
                  color: senderRole === "customer" ? "var(--blue)" : "var(--fg-3)",
                  boxShadow: senderRole === "customer" ? "0 1px 2px rgba(0,0,0,0.05)" : "none",
                  display: "flex", alignItems: "center", gap: 4
                }}
              >
                <User size={11} /> Customer Mode
              </button>
              <button
                onClick={() => setSenderRole("merchant")}
                style={{
                  padding: "4px 8px", borderRadius: 5, border: "none", cursor: "pointer",
                  fontSize: 10, fontWeight: 600,
                  background: senderRole === "merchant" ? "white" : "transparent",
                  color: senderRole === "merchant" ? "#10B981" : "var(--fg-3)",
                  boxShadow: senderRole === "merchant" ? "0 1px 2px rgba(0,0,0,0.05)" : "none",
                  display: "flex", alignItems: "center", gap: 4
                }}
              >
                <Briefcase size={11} /> Merchant Mode
              </button>
            </div>

            {/* Merchant Controls */}
            {senderRole === "merchant" && (
              <div style={{ display: "flex", gap: 6 }}>
                <button
                  onClick={handleResolveCase}
                  style={{
                    padding: "4px 8px", borderRadius: 6, border: "1px solid #10B981",
                    background: "rgba(16,185,129,0.1)", color: "#10B981",
                    fontSize: 9.5, fontWeight: 600, cursor: "pointer"
                  }}
                >
                  ✓ Mark Resolved
                </button>
                <button
                  onClick={handleResetAI}
                  style={{
                    padding: "4px 8px", borderRadius: 6, border: "1px solid var(--border)",
                    background: "transparent", color: "var(--fg-2)",
                    fontSize: 9.5, fontWeight: 600, cursor: "pointer",
                    display: "flex", alignItems: "center", gap: 4
                  }}
                >
                  <RefreshCw size={9} /> Hand to AI
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ── Customer Activity & Diagnostic Telemetry Drawer (MERCHANT ONLY) ── */}
        {senderRole === "merchant" && showTelemetry && (
          <div style={{
            background: "rgba(0,0,0,0.024)", borderBottom: "1px solid var(--border)",
            padding: "12px 18px", display: "flex", flexDirection: "column", gap: 10
          }}>
            {/* Header row */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <Activity size={13} color="#10B981" />
                <span className="jakarta" style={{ fontSize: 11.5, fontWeight: 700, color: "var(--fg)" }}>
                  Official Razorpay Payload & Customer Activity Telemetry
                </span>
                <span style={{
                  fontSize: 8.5, padding: "2px 7px", borderRadius: 4,
                  background: "rgba(239,68,68,0.1)", color: "#EF4444", fontWeight: 700
                }}>
                  {telemetry.razorpay_code || "BAD_REQUEST_ERROR"}: {telemetry.error_code?.toUpperCase()}
                </span>
                <span style={{
                  fontSize: 8.5, padding: "2px 7px", borderRadius: 4,
                  background: "rgba(59,130,246,0.1)", color: "var(--blue)", fontWeight: 700
                }}>
                  SOURCE: {telemetry.source?.toUpperCase() || "CUSTOMER"}
                </span>
                <span style={{
                  fontSize: 8.5, padding: "2px 7px", borderRadius: 4,
                  background: "rgba(16,185,129,0.1)", color: "#10B981", fontWeight: 700
                }}>
                  STEP: {telemetry.step?.toUpperCase() || "PAYMENT_AUTHORIZATION"}
                </span>
              </div>
              <span style={{ fontSize: 9.5, color: "var(--fg-3)" }}>
                {telemetry.activity_logs?.length || 5} Lifecycle Events
              </span>
            </div>

            {/* 4 Telemetry Metric Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr 1fr", gap: 8 }}>
              {/* Card 1: Official Bank/Gateway Reason */}
              <div style={{ padding: "8px 10px", borderRadius: 8, background: "var(--card)", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: 8.5, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase" }}>
                  Official Payload Reason
                </div>
                <div style={{ fontSize: 10.5, fontWeight: 700, color: "var(--fg)", marginTop: 2, lineHeight: 1.3 }}>
                  "{telemetry.official_description}"
                </div>
                <div style={{ fontSize: 8.5, color: "var(--blue)", marginTop: 4, fontWeight: 600 }}>
                  Next: {telemetry.next_step}
                </div>
              </div>

              {/* Card 2: Customer Profile from 10k dataset */}
              <div style={{ padding: "8px 10px", borderRadius: 8, background: "var(--card)", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: 8.5, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase" }}>
                  Customer Profile (10K Pool)
                </div>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--green)", marginTop: 2 }}>
                  {telemetry.on_time_payments ?? 5} On-Time · {telemetry.missed_payments ?? 1} Missed
                </div>
                <div style={{ fontSize: 8.5, color: "var(--fg-2)", marginTop: 2 }}>
                  {telemetry.months_subscribed ?? 6} mos tenure · Active {telemetry.last_login_days_ago ?? 1}d ago
                </div>
              </div>

              {/* Card 3: Bank Rail & Recovery Probability */}
              <div style={{ padding: "8px 10px", borderRadius: 8, background: "var(--card)", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: 8.5, color: "var(--fg-3)", fontWeight: 600, textTransform: "uppercase" }}>
                  Bank Rail & Recovery Odds
                </div>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--fg)", marginTop: 2 }}>
                  {telemetry.bank_issuer} ({telemetry.payment_method?.toUpperCase() || "UPI"})
                </div>
                <div style={{ fontSize: 8.5, color: "var(--fg-2)", marginTop: 2 }}>
                  {Math.round((telemetry.recovery_probability || 0.65) * 100)}% recovery odds · LTV ₹{telemetry.ltv_estimate?.toLocaleString("en-IN")}
                </div>
              </div>

              {/* Card 4: Merchant Directive & Guidance */}
              <div style={{ padding: "8px 10px", borderRadius: 8, background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.25)" }}>
                <div style={{ fontSize: 8.5, color: "#10B981", fontWeight: 700, textTransform: "uppercase" }}>
                  Internal Directive
                </div>
                <div style={{ fontSize: 9.5, color: "var(--fg)", marginTop: 2, lineHeight: 1.35 }}>
                  {telemetry.internal_note}
                </div>
              </div>
            </div>

            {/* Horizontal Event Timeline */}
            <div style={{ display: "flex", alignItems: "center", gap: 6, overflowX: "auto", paddingTop: 2 }}>
              <span style={{ fontSize: 8.5, color: "var(--fg-3)", fontWeight: 700, textTransform: "uppercase", flexShrink: 0 }}>
                Activity Log:
              </span>
              {telemetry.activity_logs?.map((act: any, idx: number) => (
                <div
                  key={idx}
                  style={{
                    display: "flex", alignItems: "center", gap: 5, padding: "3px 8px", borderRadius: 6,
                    background: "rgba(0,0,0,0.03)", border: "1px solid var(--border)", flexShrink: 0
                  }}
                  title={act.reason}
                >
                  <span className="mono" style={{ fontSize: 8, color: "var(--fg-3)" }}>{act.timestamp}</span>
                  <span style={{ fontSize: 9.5, fontWeight: 600, color: "var(--fg)" }}>{act.action}</span>
                </div>
              ))}
            </div>

            {/* Inspect Raw Razorpay Webhook Payload */}
            {telemetry.sample_payload && (
              <details style={{ fontSize: 9, color: "var(--fg-3)", cursor: "pointer" }}>
                <summary style={{ fontWeight: 600, color: "var(--blue)" }}>
                  ▶ View Official Razorpay Webhook JSON Payload
                </summary>
                <pre className="mono" style={{
                  background: "rgba(0,0,0,0.03)", padding: "6px 10px", borderRadius: 6,
                  fontSize: 8.5, overflowX: "auto", marginTop: 4, color: "var(--fg-2)"
                }}>
                  {JSON.stringify(telemetry.sample_payload, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}

        {/* Frozen Alert Banner when AWAITING_HUMAN */}
        {chatState === "AWAITING_HUMAN" && (
          <div style={{
            background: "rgba(245,158,11,0.08)", borderBottom: "1px solid rgba(245,158,11,0.25)",
            padding: "8px 18px", display: "flex", alignItems: "center", justifyContent: "space-between"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <ShieldAlert size={14} color="#F59E0B" />
              <div style={{ fontSize: 11, color: "var(--fg)" }}>
                {senderRole === "merchant" ? (
                  <>
                    <strong style={{ color: "#F59E0B" }}>Customer Escalated:</strong> AI responses frozen. Review the official Razorpay payload above and reply directly to the customer.
                  </>
                ) : (
                  <>
                    <strong style={{ color: "#F59E0B" }}>Connecting to Support:</strong> A customer support specialist has been alerted and will join this chat shortly.
                  </>
                )}
              </div>
            </div>
            {senderRole === "customer" && (
              <button
                onClick={() => setSenderRole("merchant")}
                style={{
                  padding: "3px 8px", borderRadius: 4, background: "#10B981", color: "white",
                  border: "none", fontSize: 9.5, fontWeight: 600, cursor: "pointer"
                }}
              >
                Switch to Merchant Mode
              </button>
            )}
          </div>
        )}

        {/* Bubbles */}
        <div style={{ flex: 1, overflowY: "auto", padding: "18px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
          {activeMessages.map((msg, i) => {
            const role = msg.role || "";
            const from = msg.from || "";
            const isBot = from === "bot" || role === "agent" || role === "assistant";
            const isMerchant = role === "merchant" || from === "merchant";
            const isSystem = role === "system" || from === "system";
            const text = msg.text || msg.content || "";

            if (isSystem) {
              return (
                <div key={i} style={{ display: "flex", justifyContent: "center", margin: "6px 0" }}>
                  <div style={{
                    padding: "3px 10px", borderRadius: 12, background: "rgba(0,0,0,0.04)",
                    border: "1px solid var(--border)", fontSize: 10, color: "var(--fg-3)", fontWeight: 500
                  }}>
                    ℹ️ {text}
                  </div>
                </div>
              );
            }

            return (
              <div key={i} style={{ display: "flex", justifyContent: isBot ? "flex-start" : "flex-end" }}>
                {isBot && (
                  <div style={{
                    width: 26, height: 26, borderRadius: "50%", flexShrink: 0, marginRight: 8, alignSelf: "flex-end",
                    background: "linear-gradient(135deg, #3B82F6, #1D4ED8)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    <span style={{ fontSize: 9.5, color: "white", fontWeight: 700 }}>AI</span>
                  </div>
                )}
                <div style={{
                  maxWidth: "68%", padding: "9px 13px",
                  borderRadius: isBot ? "4px 14px 14px 14px" : "14px 4px 14px 14px",
                  background: isBot
                    ? "linear-gradient(135deg, #3B82F6, #1D4ED8)"
                    : isMerchant
                    ? "linear-gradient(135deg, #059669, #10B981)"
                    : "rgba(0,0,0,0.052)",
                  color: isBot || isMerchant ? "white" : "var(--fg)",
                  fontSize: 12.5, lineHeight: 1.55,
                  boxShadow: isMerchant ? "0 2px 6px rgba(16,185,129,0.2)" : "none"
                }}>
                  {/* Sender Label Badge */}
                  <div style={{
                    fontSize: 8.5, fontWeight: 700, opacity: 0.8, marginBottom: 3,
                    display: "flex", alignItems: "center", gap: 4
                  }}>
                    {isMerchant ? "👔 Merchant / Support" : isBot ? "🤖 ArthRaksha AI" : "👤 Customer"}
                  </div>
                  {renderMessageContent(text)}
                </div>
              </div>
            );
          })}
        </div>

        {/* ── Context-Aware 1-Click Merchant Response Chips (Never ask "what was the issue") ── */}
        {senderRole === "merchant" && (
          <div style={{
            padding: "8px 18px", borderTop: "1px solid var(--border)",
            background: "rgba(16,185,129,0.03)", display: "flex", flexDirection: "column", gap: 6
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <Sparkles size={11} color="#10B981" />
              <span style={{ fontSize: 9, fontWeight: 700, color: "#10B981", textTransform: "uppercase" }}>
                1-Click Diagnostic Replies (Issue Already Known · No need to ask customer):
              </span>
            </div>
            <div style={{ display: "flex", gap: 6, overflowX: "auto" }}>
              {telemetry.suggested_replies?.map((rep: string, idx: number) => (
                <button
                  key={idx}
                  onClick={() => setInputText(rep)}
                  style={{
                    fontSize: 9.5, padding: "4px 9px", borderRadius: 8, border: "1px solid rgba(16,185,129,0.3)",
                    background: "var(--card)", color: "var(--fg)", cursor: "pointer", textAlign: "left",
                    lineHeight: 1.3, flexShrink: 0, maxWidth: 360, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"
                  }}
                  title={rep}
                >
                  💬 {rep}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Quick prompt chips for testing (in Customer Mode) */}
        {senderRole === "customer" && chatState !== "AWAITING_HUMAN" && (
          <div style={{
            padding: "6px 18px", borderTop: "1px solid var(--border)",
            display: "flex", gap: 6, overflowX: "auto", background: "rgba(0,0,0,0.015)"
          }}>
            <span style={{ fontSize: 9, color: "var(--fg-3)", alignSelf: "center", flexShrink: 0 }}>Quick Test:</span>
            {[
              { label: "🙋 Escalate to Human", text: "I want to talk to a real person, connect me to support" },
              { label: "🗣️ Hinglish Escalation", text: "Mujhe human se baat karni hai please" },
              { label: "🌐 English Link", text: "Can you please send me the payment link?" },
              { label: "🇮🇳 Hindi Devanagari", text: "कृपया मुझे भुगतान लिंक भेजें" },
              { label: "💳 Promise to Pay", text: "Kal salary aane par pay karunga" }
            ].map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(chip.text)}
                disabled={sending}
                style={{
                  fontSize: 9.5, padding: "3px 8px", borderRadius: 12, border: "1px solid var(--border)",
                  background: "var(--card)", color: "var(--fg-2)", cursor: "pointer", whiteSpace: "nowrap"
                }}
              >
                {chip.label}
              </button>
            ))}
          </div>
        )}

        {/* Input bar */}
        <div style={{ padding: "12px 18px", borderTop: "1px solid var(--border)", display: "flex", gap: 8 }}>
          <input
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSendMessage(); }}
            placeholder={
              senderRole === "merchant"
                ? "Reply as Merchant / Live Support Agent to customer…"
                : chatState === "AWAITING_HUMAN"
                ? "Type message (AI replies are frozen; human agent notified)…"
                : "Type message (e.g. 'I want to talk to a human' or 'Kal pay karunga')…"
            }
            disabled={sending}
            style={{
              flex: 1, padding: "8px 12px", borderRadius: 8,
              border: `1px solid ${senderRole === "merchant" ? "#10B981" : "var(--border)"}`,
              background: senderRole === "merchant" ? "rgba(16,185,129,0.03)" : "rgba(0,0,0,0.025)",
              color: "var(--fg)", fontSize: 12, outline: "none",
            }}
          />
          <button
            onClick={() => handleSendMessage()}
            disabled={sending || !inputText.trim()}
            style={{
              padding: "8px 14px", borderRadius: 8,
              background: sending
                ? "var(--fg-3)"
                : senderRole === "merchant"
                ? "linear-gradient(135deg, #059669, #10B981)"
                : "linear-gradient(135deg, #3B82F6, #1D4ED8)",
              border: "none", color: "white", fontSize: 11.5, fontWeight: 600,
              cursor: sending ? "not-allowed" : "pointer",
              display: "flex", alignItems: "center", gap: 5
            }}
          >
            <Send size={12} />
            {sending ? "Sending…" : senderRole === "merchant" ? "Send as Merchant 👔" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
