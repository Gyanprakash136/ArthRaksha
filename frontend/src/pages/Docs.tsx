import { useState } from "react";
import { ChevronLeft, FileText, Zap, Shield, Code, Server, Smartphone, BookOpen } from "lucide-react";

interface Props {
  onBack: () => void;
}

const SIDEBAR_SECTIONS = [
  {
    title: "Getting Started",
    links: [
      { id: "intro", label: "Introduction", icon: BookOpen },
      { id: "quickstart", label: "Quickstart", icon: Zap },
      { id: "auth", label: "Authentication", icon: Shield },
    ]
  },
  {
    title: "Core Concepts",
    links: [
      { id: "architecture", label: "Tiered Architecture", icon: Server },
      { id: "agent", label: "Conversational AI", icon: Smartphone },
    ]
  },
  {
    title: "API Reference",
    links: [
      { id: "webhooks", label: "Webhooks", icon: Code },
      { id: "events", label: "Event Types", icon: FileText },
    ]
  }
];

export default function Docs({ onBack }: Props) {
  const [activePage, setActivePage] = useState("intro");

  return (
    <div style={{ display: "flex", height: "100vh", background: "#070708", color: "#fff", fontFamily: "Inter, sans-serif", overflow: "hidden" }}>
      
      {/* ── SIDEBAR ── */}
      <aside style={{ width: 260, borderRight: "1px solid rgba(255,255,255,0.08)", display: "flex", flexDirection: "column", background: "rgba(255,255,255,0.02)" }}>
        
        {/* Header */}
        <div style={{ padding: "20px 24px", borderBottom: "1px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", gap: 12 }}>
          <button onClick={onBack} style={{
            background: "transparent", border: "none", color: "#8f8f93", cursor: "pointer", display: "flex", alignItems: "center", padding: 0
          }}>
            <ChevronLeft size={18} />
          </button>
          <div style={{ fontSize: 14, fontWeight: 600, letterSpacing: "0.02em" }}>Documentation</div>
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: "24px 16px", overflowY: "auto", display: "flex", flexDirection: "column", gap: 24 }}>
          {SIDEBAR_SECTIONS.map((section, idx) => (
            <div key={idx}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#8f8f93", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 12, paddingLeft: 8 }}>
                {section.title}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {section.links.map(link => {
                  const isActive = activePage === link.id;
                  return (
                    <button
                      key={link.id}
                      onClick={() => setActivePage(link.id)}
                      style={{
                        display: "flex", alignItems: "center", gap: 10,
                        padding: "8px 10px", borderRadius: 6,
                        background: isActive ? "rgba(59,130,246,0.12)" : "transparent",
                        border: "none", cursor: "pointer", textAlign: "left",
                        color: isActive ? "#60A5FA" : "rgba(255,255,255,0.65)",
                        transition: "all 0.15s ease"
                      }}
                    >
                      <link.icon size={14} />
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
      <main style={{ flex: 1, overflowY: "auto", padding: "60px 80px" }}>
        <div style={{ maxWidth: 720, margin: "0 auto" }}>
          
          {/* Breadcrumb */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#8f8f93", marginBottom: 24 }}>
            <span>Docs</span>
            <span>/</span>
            <span style={{ color: "#60A5FA" }}>{SIDEBAR_SECTIONS.flatMap(s => s.links).find(l => l.id === activePage)?.label}</span>
          </div>

          {activePage === "intro" && (
            <div className="doc-content">
              <h1 style={{ fontSize: 36, fontWeight: 300, marginBottom: 16, letterSpacing: "-0.01em" }}>Introduction to ArthRaksha</h1>
              <p style={{ fontSize: 15, lineHeight: 1.6, color: "rgba(255,255,255,0.75)", marginBottom: 32 }}>
                ArthRaksha is an intelligent payment recovery platform designed to intercept, analyze, and recover dropped transactions. By integrating natively with your payment gateway's webhooks, we salvage revenue that would otherwise be permanently lost.
              </p>
              
              <h2 style={{ fontSize: 20, fontWeight: 500, marginTop: 40, marginBottom: 16, borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: 8 }}>How it works</h2>
              <ul style={{ paddingLeft: 20, display: "flex", flexDirection: "column", gap: 12, color: "rgba(255,255,255,0.75)", lineHeight: 1.6, fontSize: 14 }}>
                <li><strong>1. Ingestion:</strong> Your payment gateway sends a `payment.failed` webhook to our endpoint.</li>
                <li><strong>2. Analysis:</strong> Our Deterministic Routing Engine evaluates the error code, context, and customer history.</li>
                <li><strong>3. Action:</strong> The case is instantly resolved via auto-retry, assigned to an AI Conversational Agent, or escalated to a human specialist.</li>
                <li><strong>4. Recovery:</strong> The customer successfully pays via an alternate link, and your dashboard reflects the salvaged revenue.</li>
              </ul>
            </div>
          )}

          {activePage === "webhooks" && (
            <div className="doc-content">
              <h1 style={{ fontSize: 36, fontWeight: 300, marginBottom: 16, letterSpacing: "-0.01em" }}>Webhooks Integration</h1>
              <p style={{ fontSize: 15, lineHeight: 1.6, color: "rgba(255,255,255,0.75)", marginBottom: 32 }}>
                ArthRaksha relies on real-time event streaming to instantly react to payment drops. Configure your gateway to send webhook events to our ingestion endpoint.
              </p>
              
              <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: 16, marginBottom: 32 }}>
                <div style={{ fontSize: 12, color: "#8f8f93", marginBottom: 8, fontFamily: "monospace" }}>POST /webhook/razorpay</div>
                <code style={{ fontSize: 13, color: "#60A5FA", fontFamily: "monospace" }}>https://api.arthraksha.io/v1/webhook/razorpay</code>
              </div>

              <h2 style={{ fontSize: 20, fontWeight: 500, marginTop: 40, marginBottom: 16, borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: 8 }}>Sample Payload</h2>
              <pre style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: 16, overflowX: "auto", fontSize: 13, color: "rgba(255,255,255,0.85)", fontFamily: "monospace" }}>
{`{
  "event": "payment.failed",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_xyz",
        "amount": 50000,
        "currency": "INR",
        "status": "failed",
        "error_code": "BAD_REQUEST_ERROR",
        "error_description": "Payment failed due to insufficient funds"
      }
    }
  }
}`}
              </pre>
            </div>
          )}

          {/* Placeholder for other pages */}
          {activePage !== "intro" && activePage !== "webhooks" && (
            <div className="doc-content" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "80px 0", color: "#8f8f93" }}>
              <BookOpen size={48} color="rgba(255,255,255,0.1)" style={{ marginBottom: 16 }} />
              <h2 style={{ fontSize: 20, fontWeight: 400, color: "rgba(255,255,255,0.5)" }}>Documentation section in development</h2>
              <p style={{ fontSize: 14, marginTop: 8 }}>This API reference is actively being written by the engineering team.</p>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
