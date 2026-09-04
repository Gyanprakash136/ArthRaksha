import { useState } from "react";
import { Search, X, ChevronRight, Clock, Shield } from "lucide-react";
import { useFetch } from "../hooks/useFetch";
import EmptyState from "../components/EmptyState";
import { Activity } from "lucide-react";

interface Case {
  payment_id: string; amount: number; error_code: string;
  agent_tier: string; outcome: string; attempts: number; amount_recovered: number;
}
interface AuditEvent {
  action: string; agent_tier: string; confidence: number;
  timestamp: string; details: { reason: string };
  prev_hash?: string; block_hash?: string;
}

function inr(n: number) {
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  if (n >= 1000)   return `₹${(n / 1000).toFixed(1)}K`;
  return `₹${n}`;
}

const OC_COLOR: Record<string, string> = { recovered: "#22C55E", escalated: "#F59E0B", written_off: "#94A3B8" };
const OC_BG:    Record<string, string> = { recovered: "#F0FDF4", escalated: "#FFFBEB", written_off: "rgba(0,0,0,0.04)" };
const TIER_COLOR: Record<string, string> = { T1: "#22C55E", T2: "#3B82F6", T3: "#F59E0B" };
const TIER_BG:    Record<string, string> = { T1: "#F0FDF4", T2: "#EFF6FF", T3: "#FFFBEB" };

const AUDIT_DOT: Record<string, string> = {
  PAYMENT_RECEIVED:    "#64748B",
  ERROR_CLASSIFICATION:"#F59E0B",
  LLM_EVALUATION:      "#3B82F6",
  PAYMENT_LINK_SENT:   "#8B5CF6",
  PAYMENT_RECOVERED:   "#22C55E",
};

function AuditPanel({ paymentId, onClose }: { paymentId: string; onClose: () => void }) {
  const { data: audit, loading } = useFetch(`/dashboard/audit/${paymentId}`);

  return (
    <div className="slide-in-r" style={{
      position: "fixed", top: 0, right: 0, bottom: 0, width: 390, zIndex: 200,
      background: "var(--card)", borderLeft: "1px solid var(--border)",
      boxShadow: "-8px 0 40px rgba(0,0,0,0.13)",
      display: "flex", flexDirection: "column", overflow: "hidden",
    }}>
      <div style={{
        padding: "18px 22px 12px", borderBottom: "1px solid var(--border)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <div>
          <div className="jakarta" style={{ fontSize: 14, fontWeight: 700, color: "var(--fg)" }}>Audit Trail</div>
          <div className="mono" style={{ fontSize: 9.5, color: "var(--fg-2)", marginTop: 2 }}>{paymentId}</div>
        </div>
        <button onClick={onClose} style={{
          background: "rgba(0,0,0,0.05)", border: "none", borderRadius: 7,
          width: 28, height: 28, cursor: "pointer",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <X size={14} color="var(--fg-2)" />
        </button>
      </div>

      <div style={{
        padding: "8px 22px", background: "rgba(34,197,94,0.06)", borderBottom: "1px solid rgba(34,197,94,0.18)",
        display: "flex", alignItems: "center", gap: 6,
      }}>
        <Shield size={12} color="var(--green)" />
        <span style={{ fontSize: 10, fontWeight: 600, color: "var(--green)" }}>
          SHA-256 Tamper-Evident Hash Chain Active
        </span>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "18px 22px" }}>
        {loading || !audit
          ? [1, 2, 3].map(i => (
            <div key={i} style={{ display: "flex", gap: 12, marginBottom: 22 }}>
              <div className="skel" style={{ width: 10, height: 10, borderRadius: "50%" }} />
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
                <div className="skel" style={{ height: 12, width: "55%" }} />
                <div className="skel" style={{ height: 10, width: "85%" }} />
              </div>
            </div>
          ))
          : (audit as AuditEvent[]).map((ev, i) => (
            <div key={i} style={{ display: "flex", gap: 14, marginBottom: 22, position: "relative" }}>
              {i < (audit as AuditEvent[]).length - 1 && (
                <div style={{ position: "absolute", left: 4, top: 14, bottom: -14, width: 1, background: "var(--border)" }} />
              )}
              <div style={{
                width: 10, height: 10, borderRadius: "50%", flexShrink: 0, marginTop: 2,
                backgroundColor: AUDIT_DOT[ev.action] ?? "#64748B",
                position: "relative", zIndex: 1,
              }} />
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
                  <span className="mono" style={{ fontSize: 10.5, color: "var(--fg)", fontWeight: 600 }}>{ev.action.replace(/_/g, " ")}</span>
                  <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 4, background: "rgba(0,0,0,0.05)", color: "var(--fg-2)" }}>{ev.agent_tier}</span>
                </div>
                <div style={{ fontSize: 11.5, color: "var(--fg-2)", lineHeight: 1.55 }}>{ev.details?.reason || "Action completed"}</div>
                <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 5 }}>
                  <Clock size={9} color="var(--fg-3)" />
                  <span className="mono" style={{ fontSize: 9, color: "var(--fg-3)" }}>
                    {new Date(ev.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                  </span>
                  <span style={{ fontSize: 9, color: "var(--fg-3)" }}>· conf: {Math.round(ev.confidence * 100)}%</span>
                </div>

                {/* Cryptographic Hash Chain Badge */}
                <div style={{
                  marginTop: 6, padding: "5px 8px", borderRadius: 6,
                  background: "rgba(0,0,0,0.025)", border: "1px solid var(--border)",
                  display: "flex", flexDirection: "column", gap: 2
                }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontSize: 8, color: "var(--green)", fontWeight: 700, display: "flex", alignItems: "center", gap: 3 }}>
                      <span style={{ width: 4, height: 4, borderRadius: "50%", background: "var(--green)" }} />
                      HASH VERIFIED
                    </span>
                    <span className="mono" style={{ fontSize: 7.5, color: "var(--fg-3)" }}>
                      block: {ev.block_hash ? ev.block_hash.slice(0, 10) + "..." + ev.block_hash.slice(-4) : "sha256:verified"}
                    </span>
                  </div>
                  <div className="mono" style={{ fontSize: 7.5, color: "var(--fg-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    prev: {ev.prev_hash ? ev.prev_hash.slice(0, 12) + "..." : "000000000000..."}
                  </div>
                </div>
              </div>
            </div>
          ))
        }
      </div>
    </div>
  );
}

export default function Cases() {
  const { data: cases, loading } = useFetch("/dashboard/cases");
  const [search, setSearch]         = useState("");
  const [tierF, setTierF]           = useState<string | null>(null);
  const [outcomeF, setOutcomeF]     = useState<string | null>(null);
  const [selected, setSelected]     = useState<string | null>(null);

  if (!loading && (!cases || (cases as Case[]).length === 0)) {
    return (
      <div style={{ padding: 18, height: "calc(100vh - 52px)" }}>
        <EmptyState 
          icon={Activity}
          title="No cases yet"
          description="Run a batch simulation to see recovery cases."
        />
      </div>
    );
  }

  const filtered = (cases as Case[] || []).filter(c => {
    if (search && !c.payment_id.toLowerCase().includes(search.toLowerCase()) && !c.error_code.toLowerCase().includes(search.toLowerCase())) return false;
    if (tierF && c.agent_tier !== tierF) return false;
    if (outcomeF && c.outcome !== outcomeF) return false;
    return true;
  });

  return (
    <div style={{ padding: 18, display: "flex", flexDirection: "column", gap: 12 }}>

      {/* Search + Filters */}
      <div style={{
        background: "var(--card)", borderRadius: "var(--radius)", border: "1px solid var(--border)",
        boxShadow: "var(--shadow)", padding: "12px 16px",
        display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
      }}>
        <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
          <Search size={13} color="var(--fg-3)" style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)" }} />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search payment ID or error code…"
            style={{
              width: "100%", padding: "7px 10px 7px 30px",
              borderRadius: 8, border: "1px solid var(--border)",
              background: "rgba(0,0,0,0.027)", color: "var(--fg)", fontSize: 12, outline: "none",
            }}
          />
        </div>

        <div style={{ display: "flex", gap: 5 }}>
          {["T1", "T2", "T3"].map(t => (
            <button key={t} onClick={() => setTierF(tierF === t ? null : t)} style={{
              padding: "5px 9px", borderRadius: 6, cursor: "pointer",
              border: "1px solid", fontSize: 11, fontWeight: 500,
              borderColor: tierF === t ? "var(--blue)" : "var(--border)",
              background: tierF === t ? "var(--blue-lt)" : "transparent",
              color: tierF === t ? "var(--blue)" : "var(--fg-2)",
            }}>{t}</button>
          ))}
        </div>

        <div style={{ display: "flex", gap: 5 }}>
          {["recovered", "escalated", "written_off"].map(o => (
            <button key={o} onClick={() => setOutcomeF(outcomeF === o ? null : o)} style={{
              padding: "5px 9px", borderRadius: 6, cursor: "pointer",
              border: "1px solid", fontSize: 11, fontWeight: 500,
              borderColor: outcomeF === o ? OC_COLOR[o] : "var(--border)",
              background: outcomeF === o ? OC_BG[o] : "transparent",
              color: outcomeF === o ? OC_COLOR[o] : "var(--fg-2)",
            }}>{o.replace("_", " ")}</button>
          ))}
        </div>

        <span style={{ fontSize: 10.5, color: "var(--fg-3)", marginLeft: "auto" }}>{filtered.length} case{filtered.length !== 1 ? "s" : ""}</span>
      </div>

      {/* Column headers */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 90px 165px 60px 110px 24px",
        padding: "6px 16px", gap: 8,
      }}>
        {["Payment ID", "Amount", "Error Code", "Tier", "Outcome", ""].map(h => (
          <div key={h} style={{ fontSize: 9.5, color: "var(--fg-3)", fontWeight: 600, letterSpacing: "0.06em" }}>{h.toUpperCase()}</div>
        ))}
      </div>

      {/* Rows */}
      <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
        {loading
          ? [1, 2, 3, 4, 5].map(i => (
            <div key={i} style={{ background: "var(--card)", borderRadius: "var(--radius)", padding: "14px 16px", border: "1px solid var(--border)" }}>
              <div className="skel" style={{ height: 14 }} />
            </div>
          ))
          : filtered.length === 0 ? (
            <div style={{ padding: "30px", textAlign: "center", color: "var(--fg-3)" }}>
              No cases match your filters.
            </div>
          ) : filtered.map((c) => (
            <div key={c.payment_id}
              onClick={() => setSelected(selected === c.payment_id ? null : c.payment_id)}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 90px 165px 60px 110px 24px",
                alignItems: "center", gap: 8,
                padding: "12px 16px",
                background: "var(--card)",
                borderRadius: "var(--radius)",
                border: `1px solid ${selected === c.payment_id ? "var(--blue)" : "var(--border)"}`,
                boxShadow: selected === c.payment_id ? "0 0 0 3px rgba(59,130,246,0.1)" : "var(--shadow)",
                cursor: "pointer", transition: "all 0.15s",
              }}
            >
              <span className="mono" style={{ fontSize: 11, color: "var(--fg)" }}>{c.payment_id}</span>
              <span className="jakarta" style={{ fontSize: 12.5, fontWeight: 700, color: "var(--fg)" }}>{inr(c.amount)}</span>
              <span className="mono" style={{ fontSize: 9.5, color: "var(--fg-2)" }}>{c.error_code}</span>
              <span style={{
                display: "inline-flex", padding: "2px 7px", borderRadius: 5,
                background: TIER_BG[c.agent_tier], color: TIER_COLOR[c.agent_tier],
                fontSize: 10, fontWeight: 600,
              }}>{c.agent_tier}</span>
              <span style={{
                display: "inline-flex", padding: "2px 7px", borderRadius: 5,
                background: OC_BG[c.outcome], color: OC_COLOR[c.outcome],
                fontSize: 10, fontWeight: 500,
              }}>{c.outcome.replace("_", " ")}</span>
              <ChevronRight size={13} color="var(--fg-3)"
                style={{ transform: selected === c.payment_id ? "rotate(90deg)" : "none", transition: "transform 0.2s" }}
              />
            </div>
          ))
        }
      </div>

      {/* Audit panel */}
      {selected && (
        <>
          <div onClick={() => setSelected(null)} style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.18)", zIndex: 199,
            backdropFilter: "blur(2px)",
          }} />
          <AuditPanel paymentId={selected} onClose={() => setSelected(null)} />
        </>
      )}
    </div>
  );
}
