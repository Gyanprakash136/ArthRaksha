import { useState, useEffect } from "react";
import { useFetch, API_BASE } from "../hooks/useFetch";
import EmptyState from "../components/EmptyState";
import { Wifi, WifiOff, Sparkles, Route, ArrowUpRight, MessageSquare, TrendingUp, Activity, CheckCircle2, AlertTriangle, Shield } from "lucide-react";

function inr(n: number) {
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(1)}Cr`;
  if (n >= 100000)   return `₹${(n / 100000).toFixed(1)}L`;
  if (n >= 1000)     return `₹${(n / 1000).toFixed(1)}K`;
  return `₹${n}`;
}

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: "var(--card)", borderRadius: "var(--radius)",
      border: "1px solid var(--border)", boxShadow: "var(--shadow)",
      overflow: "hidden",
      ...style,
    }}>
      {children}
    </div>
  );
}

function Sk({ w, h }: { w?: string | number; h: number }) {
  return <div className="skel" style={{ width: w ?? "100%", height: h }} />;
}

function RecoveryRing({ rate, loading }: { rate: number; loading: boolean }) {
  const sz = 108;
  const R = 41;
  const cx = sz / 2;
  const cy = sz / 2;
  const sw = 9;
  const circ = 2 * Math.PI * R;
  const fill = circ * rate;

  if (loading) return <div className="skel" style={{ width: sz, height: sz, borderRadius: "50%" }} />;

  return (
    <svg width={sz} height={sz} style={{ display: "block", overflow: "visible" }}>
      <defs>
        <linearGradient id="rg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#3B82F6" />
          <stop offset="100%" stopColor="#60A5FA" />
        </linearGradient>
      </defs>
      <circle cx={cx} cy={cy} r={R} fill="none" stroke="#E2DFDA" strokeWidth={sw} />
      <circle cx={cx} cy={cy} r={R} fill="none"
        stroke="url(#rg)" strokeWidth={sw}
        strokeDasharray={`${fill} ${circ}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: "stroke-dasharray 1.4s cubic-bezier(0.16,1,0.3,1)" }}
      />
      <text x={cx} y={cy + 1} textAnchor="middle" dominantBaseline="middle"
        style={{ fill: "var(--fg)", fontSize: 20, fontWeight: 800, fontFamily: "Plus Jakarta Sans, sans-serif" }}>
        {Math.round(rate * 100)}%
      </text>
    </svg>
  );
}

const DEFAULT_COLORS = ["#3B82F6", "#8B5CF6", "#F97316"];

function BubbleChart({ details }: { details: any[] }) {
  if (!details || details.length === 0) return null;
  // Dynamic coordinates based on index for bubble placement
  const c = [
    { cx: 64, cy: 72, r: 50 },
    { cx: 152, cy: 58, r: 35 },
    { cx: 168, cy: 127, r: 25 },
  ];
  return (
    <svg width="205" height="150" style={{ display: "block", flexShrink: 0 }}>
      {details.slice(0, 3).map((b, i) => (
        <g key={i}>
          <circle cx={c[i]?.cx} cy={c[i]?.cy} r={c[i]?.r} fill={b.color} opacity={0.1} />
          <circle cx={c[i]?.cx} cy={c[i]?.cy} r={c[i]?.r} fill="none" stroke={b.color} strokeWidth={1.5} opacity={0.32} />
          <text x={c[i]?.cx} y={c[i]?.cy - 3} textAnchor="middle"
            style={{ fill: b.color, fontSize: Math.max(c[i]?.r * 0.38, 11), fontWeight: 800, fontFamily: "Plus Jakarta Sans, sans-serif" }}>
            {b.pct}%
          </text>
          <text x={c[i]?.cx} y={c[i]?.cy + c[i]?.r * 0.45} textAnchor="middle"
            style={{ fill: "#94A3B8", fontSize: Math.max(c[i]?.r * 0.26, 8), fontFamily: "JetBrains Mono, monospace" }}>
            {b.short}
          </text>
        </g>
      ))}
    </svg>
  );
}

const OC_COLOR: Record<string, string> = { recovered: "#22C55E", escalated: "#F59E0B", written_off: "#94A3B8" };
const OC_BG:    Record<string, string> = { recovered: "#F0FDF4", escalated: "#FFFBEB", written_off: "rgba(0,0,0,0.04)" };

export default function Overview({ refreshTick, startBatch, batchStatus, setTab }: any) {
  const { data: m, loading, live, refetch, error } = useFetch("/dashboard/metrics");
  const { data: recentCasesData, loading: casesLoading } = useFetch("/dashboard/cases");
  
  const [actionLoading, setActionLoading] = useState<"recovering" | "escalating" | null>(null);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  const recentCases = (recentCasesData || []).slice(0, 5);

  useEffect(() => {
    if (refreshTick > 0) refetch();
  }, [refreshTick, refetch]);

  const handleRecoverAll = async () => {
    if (actionLoading) return;
    setActionLoading("recovering");
    try {
      const res = await fetch(`${API_BASE}/dashboard/recover-all`, { method: "POST" });
      const data = await res.json();
      setActionFeedback(data.message || "Recovered pending cases");
      refetch();
      setTimeout(() => setActionFeedback(null), 5000);
    } catch {
      setActionFeedback("Failed to trigger recovery");
      setTimeout(() => setActionFeedback(null), 3000);
    } finally {
      setActionLoading(null);
    }
  };

  const handleEscalateAll = async () => {
    if (actionLoading) return;
    setActionLoading("escalating");
    try {
      const res = await fetch(`${API_BASE}/dashboard/escalate-all`, { method: "POST" });
      const data = await res.json();
      setActionFeedback(data.message || "Escalated to Tier 3 human queue");
      refetch();
      setTimeout(() => setActionFeedback(null), 5000);
    } catch {
      setActionFeedback("Failed to trigger escalation");
      setTimeout(() => setActionFeedback(null), 3000);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 40, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "50vh", gap: 12 }}>
        <div style={{ width: 26, height: 26, border: "3px solid rgba(59,130,246,0.2)", borderTopColor: "#3B82F6", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
        <div style={{ color: "var(--fg-2)", fontSize: 13, fontWeight: 500 }}>Loading recovery dashboard...</div>
        <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "40px", color: "var(--red)" }}>
        Error loading dashboard: {error}
      </div>
    );
  }

  const metrics = {
    total_at_risk: m?.total_at_risk ?? 0,
    total_recovered: m?.total_recovered ?? 0,
    total_escalated: m?.total_escalated ?? 0,
    total_written_off: m?.total_written_off ?? 0,
    total_pending: m?.total_pending ?? 0,
    total_cases: m?.total_cases ?? 0,
    recovery_rate: m?.recovery_rate ?? 0,
    cache_hit_rate: m?.cache_hit_rate ?? 0,
    tokens_saved: m?.tokens_saved ?? 0,
    fail_details: m?.fail_details ?? [],
    agent_performance: m?.agent_performance ?? [],
    top_recovery_path: m?.top_recovery_path ?? "payment_link",
    top_recovery_channel: m?.top_recovery_channel ?? "Payment Link",
    top_recovery_rate: m?.top_recovery_rate ?? 76
  };

  if (!metrics.total_at_risk || metrics.total_at_risk === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="No data yet"
        description="Run a batch simulation to see recovery metrics"
        action="Run Batch"
        onAction={startBatch}
      />
    );
  }

  const merchantName = localStorage.getItem("merchantName") || "Acme Corp";

  return (
    <div style={{ padding: 18, display: "flex", flexDirection: "column", gap: 12 }}>

      {/* Greeting */}
      <Card style={{ padding: "18px 22px", display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 20 }}>👋</span>
            <h1 className="jakarta" style={{ margin: 0, fontSize: 18, fontWeight: 800, letterSpacing: "-0.03em", color: "var(--fg)" }}>
              Hey, {merchantName} — welcome back!
            </h1>
          </div>
          <p style={{ margin: 0, fontSize: 12.5, color: "var(--fg-2)" }}>
            Your AI recovery engine is running.{" "}
            {loading ? "Loading metrics…" : `${inr(metrics.total_recovered)} recovered so far this batch.`}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: live ? "var(--green)" : "var(--amber)", ...(live ? { animation: "pulse-dot 2s infinite" } : {}) }} />
            <span className="mono" style={{ fontSize: 9, color: live ? "var(--green)" : "var(--amber)" }}>{live ? "LIVE" : "DEMO"}</span>
            {live ? <Wifi size={9} color="var(--green)" /> : <WifiOff size={9} color="var(--amber)" />}
          </div>
          <button onClick={startBatch} disabled={batchStatus === "running"} style={{
            padding: "7px 15px", borderRadius: 8,
            background: "linear-gradient(135deg, #3B82F6, #1D4ED8)",
            border: "none", color: "white", fontSize: 12, fontWeight: 600,
            cursor: batchStatus === "running" ? "not-allowed" : "pointer", 
            display: "flex", alignItems: "center", gap: 5,
            boxShadow: "0 2px 10px rgba(59,130,246,0.35)", opacity: batchStatus === "running" ? 0.8 : 1
          }}>
            <Sparkles size={12} />
            {batchStatus === "running" ? "Running..." : "Run AI Batch"}
          </button>
        </div>
      </Card>

      {/* Widget mosaic */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gridTemplateAreas: `
          "atRisk atRisk recov  ring"
          "atRisk atRisk cache  path"
          "bubble bubble feed   feed"
          "ai     ai     tiers  tiers"
        `,
        gap: 12,
      }}>

        {/* ── At-Risk Payment Card ── */}
        <Card style={{ gridArea: "atRisk", padding: 0 }}>
          <div style={{
            background: "linear-gradient(140deg, #0F172A 0%, #1E3A5F 55%, #1D4ED8 100%)",
            padding: "26px 26px 22px", position: "relative",
          }}>
            {/* decorative bg circles */}
            <div style={{ position: "absolute", top: -28, right: -28, width: 150, height: 150, borderRadius: "50%", background: "rgba(255,255,255,0.03)", pointerEvents: "none" }} />
            <div style={{ position: "absolute", top: 20, right: 30, width: 80, height: 80, borderRadius: "50%", background: "rgba(255,255,255,0.04)", pointerEvents: "none" }} />

            <div className="mono" style={{ fontSize: 8.5, color: "rgba(255,255,255,0.38)", letterSpacing: "0.15em", marginBottom: 14 }}>TOTAL AT RISK · THIS BATCH</div>
            <div className="jakarta" style={{ fontSize: loading ? 32 : 42, fontWeight: 800, color: "#fff", letterSpacing: "-0.04em", lineHeight: 1, marginBottom: 6 }}>
              {loading ? <div className="skel" style={{ width: 140, height: 42 }} /> : inr(metrics.total_at_risk)}
            </div>
            {!loading && <div style={{ fontSize: 11.5, color: "rgba(255,255,255,0.42)" }}>Exposure across {metrics.total_cases || (recentCasesData?.length || 50)} failed payments</div>}

            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 22, flexWrap: "wrap" }}>
              <button
                onClick={handleRecoverAll}
                disabled={actionLoading !== null}
                style={{
                  padding: "8px 16px", borderRadius: 8,
                  border: "none",
                  background: actionLoading === "recovering" ? "rgba(34,197,94,0.4)" : "#22C55E",
                  color: "white", fontSize: 12, fontWeight: 600, cursor: actionLoading ? "not-allowed" : "pointer",
                  display: "flex", alignItems: "center", gap: 6,
                  boxShadow: "0 2px 10px rgba(34,197,94,0.35)", transition: "all 0.15s"
                }}
              >
                {actionLoading === "recovering" ? (
                  <>
                    <div style={{ width: 11, height: 11, border: "2px solid rgba(255,255,255,0.4)", borderTopColor: "#fff", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                    Recovering...
                  </>
                ) : (
                  <>⚡ Recover All</>
                )}
              </button>

              <button
                onClick={handleEscalateAll}
                disabled={actionLoading !== null}
                style={{
                  padding: "8px 16px", borderRadius: 8,
                  border: "1px solid rgba(255,255,255,0.2)",
                  background: actionLoading === "escalating" ? "rgba(245,158,11,0.3)" : "rgba(255,255,255,0.1)",
                  color: "white", fontSize: 12, fontWeight: 600, cursor: actionLoading ? "not-allowed" : "pointer",
                  display: "flex", alignItems: "center", gap: 6, transition: "all 0.15s"
                }}
              >
                {actionLoading === "escalating" ? (
                  <>
                    <div style={{ width: 11, height: 11, border: "2px solid rgba(255,255,255,0.4)", borderTopColor: "#fff", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                    Escalating...
                  </>
                ) : (
                  <>⚠️ Escalate</>
                )}
              </button>

              {actionFeedback && (
                <div style={{
                  padding: "6px 14px", borderRadius: 7, background: "rgba(255,255,255,0.16)",
                  color: "#fff", fontSize: 11.5, fontWeight: 500, display: "flex", alignItems: "center", gap: 6,
                  border: "1px solid rgba(255,255,255,0.15)"
                }}>
                  <CheckCircle2 size={12} color="#22C55E" />
                  {actionFeedback}
                </div>
              )}
            </div>
          </div>

          <div style={{ padding: "16px 26px", display: "grid", gridTemplateColumns: "repeat(3, 1fr)" }}>
            {[
              { label: "Recovered",   val: metrics.total_recovered,   color: "var(--green)" },
              { label: "Escalated",   val: metrics.total_escalated,   color: "var(--amber)" },
              { label: "Written Off", val: metrics.total_written_off, color: "var(--fg-3)"  },
            ].map((s, i) => (
              <div key={s.label} style={{ padding: "0 14px", borderLeft: i > 0 ? "1px solid var(--border)" : "none" }}>
                <div style={{ fontSize: 9.5, color: "var(--fg-2)", marginBottom: 3 }}>{s.label}</div>
                {loading
                  ? <Sk h={18} w="80%" />
                  : <div className="jakarta" style={{ fontSize: 17, fontWeight: 700, color: s.color }}>{inr(s.val)}</div>
                }
              </div>
            ))}
          </div>
        </Card>

        {/* ── Recovery Rate Ring ── */}
        <Card style={{ gridArea: "ring", padding: "18px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10 }}>
          <div style={{ fontSize: 10.5, color: "var(--fg-2)", fontWeight: 500, alignSelf: "flex-start" }}>Recovery Rate</div>
          <RecoveryRing rate={metrics.recovery_rate} loading={loading} />
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 10.5, color: "var(--fg-2)" }}>of at-risk amount</div>
            <div style={{ fontSize: 10.5, color: "var(--green)", fontWeight: 600, marginTop: 2 }}>↑ Strong this batch</div>
          </div>
        </Card>

        {/* ── AI Efficiency / Cache ── */}
        <Card style={{ gridArea: "cache", padding: "18px" }}>
          <div style={{ fontSize: 10.5, color: "var(--fg-2)", fontWeight: 500, marginBottom: 10 }}>AI Efficiency</div>
          {loading
            ? <><Sk h={26} w="55%" /><div style={{ marginTop: 8 }}><Sk h={10} w="80%" /></div></>
            : (
              <>
                <div className="jakarta" style={{ fontSize: 26, fontWeight: 800, color: "var(--blue)", letterSpacing: "-0.04em", lineHeight: 1 }}>
                  {(metrics.tokens_saved / 1000).toFixed(0)}K
                </div>
                <div style={{ fontSize: 10.5, color: "var(--fg-2)", marginTop: 3 }}>tokens saved via cache</div>
                <div style={{ marginTop: 10, height: 4, background: "rgba(59,130,246,0.1)", borderRadius: 4 }}>
                  <div style={{ height: "100%", width: `${metrics.cache_hit_rate * 100}%`, background: "var(--blue)", borderRadius: 4 }} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                  <span style={{ fontSize: 9, color: "var(--fg-3)" }}>Cache hit rate</span>
                  <span className="mono" style={{ fontSize: 9, color: "var(--blue)", fontWeight: 600 }}>{Math.round(metrics.cache_hit_rate * 100)}%</span>
                </div>
              </>
            )
          }
        </Card>

        {/* ── Top Recovery Path ── */}
        <Card style={{ gridArea: "path", padding: "18px" }}>
          <div style={{ fontSize: 10.5, color: "var(--fg-2)", fontWeight: 500, marginBottom: 10 }}>Top Recovery Path</div>
          {loading
            ? <><Sk h={20} w="70%" /><div style={{ marginTop: 8 }}><Sk h={10} w="90%" /></div></>
            : (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 6 }}>
                  <Route size={15} color="var(--blue)" />
                  <span className="mono" style={{ fontSize: 12, color: "var(--blue)", fontWeight: 600 }}>
                    {metrics.top_recovery_channel?.toUpperCase() || metrics.top_recovery_path?.replace(/_/g, " ").toUpperCase() || "PAYMENT LINK"}
                  </span>
                </div>
                <div style={{ fontSize: 10.5, color: "var(--fg-2)" }}>Highest conversion channel</div>
                <div style={{ marginTop: 9, padding: "5px 9px", borderRadius: 6, background: "var(--blue-lt)", fontSize: 10, color: "var(--blue)", fontWeight: 500 }}>
                  {metrics.top_recovery_channel || "Payment Link"} · {metrics.top_recovery_rate || 76}% success rate
                </div>
              </>
            )
          }
        </Card>

        {/* ── Failure Bubbles ── */}
        <Card style={{ gridArea: "bubble", padding: "18px 20px" }}>
          <div style={{ marginBottom: 10 }}>
            <div className="jakarta" style={{ fontSize: 13.5, fontWeight: 700, color: "var(--fg)" }}>Failure Distribution</div>
            <div style={{ fontSize: 10.5, color: "var(--fg-2)", marginTop: 2 }}>Why payments failed this batch</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {loading ? <Sk h={150} w={205} /> : <BubbleChart details={metrics.fail_details?.map((f: any, i: number) => ({ ...f, color: DEFAULT_COLORS[i % DEFAULT_COLORS.length] }))} />}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 9 }}>
              {loading ? <Sk h={150} /> : (metrics.fail_details || []).map((f: any, i: number) => {
                const color = DEFAULT_COLORS[i % DEFAULT_COLORS.length];
                return (
                <div key={f.label}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                    <div style={{ display: "flex", alignItems: "baseline", gap: 5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      <span style={{ fontSize: 11, color: "var(--fg)", fontWeight: 500 }}>{f.label}</span>
                      <span style={{ fontSize: 9.5, color: "var(--fg-3)" }}>({f.count || 0} cases · {inr(f.amount || 0)})</span>
                    </div>
                    <span style={{ fontSize: 11, color: color, fontWeight: 600, flexShrink: 0 }}>{f.pct}%</span>
                  </div>
                  <div style={{ height: 5, background: "rgba(0,0,0,0.06)", borderRadius: 4 }}>
                    <div style={{ height: "100%", width: `${f.pct}%`, background: color, borderRadius: 4, transition: "width 1s ease" }} />
                  </div>
                </div>
                )
              })}
            </div>
          </div>
        </Card>

        {/* ── Recent Cases Feed ── */}
        <Card style={{ gridArea: "feed", padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div className="jakarta" style={{ fontSize: 13.5, fontWeight: 700, color: "var(--fg)" }}>Recent Cases</div>
            <button onClick={() => setTab("cases")} style={{ fontSize: 11, color: "var(--blue)", background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: 3, fontWeight: 500 }}>
              View all <ArrowUpRight size={11} />
            </button>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
            {casesLoading ? <Sk h={38} /> : recentCases.map(c => (
              <div key={c.payment_id} style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "9px 11px", borderRadius: 9,
                background: "rgba(0,0,0,0.024)", border: "1px solid var(--border)",
              }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", backgroundColor: OC_COLOR[c?.outcome] ?? "var(--fg-3)", flexShrink: 0 }} />
                <span className="mono" style={{ fontSize: 10.5, color: "var(--fg-2)", flex: 1 }}>{c?.payment_id || "N/A"}</span>
                <span className="jakarta" style={{ fontSize: 12, fontWeight: 700, color: "var(--fg)" }}>{inr(c?.amount || 0)}</span>
                <span style={{
                  fontSize: 9.5, fontWeight: 500, padding: "2px 6px", borderRadius: 5,
                  color: OC_COLOR[c?.outcome] ?? "var(--fg-3)", background: OC_BG[c?.outcome] ?? "rgba(0,0,0,0.04)",
                }}>
                  {c?.outcome ? String(c.outcome).replace("_", " ") : "pending"}
                </span>
                <span style={{ fontSize: 9.5, color: "var(--fg-3)" }}>{c?.agent_tier || "T1"}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* ── AI Insight Teaser ── */}
        <Card style={{ gridArea: "ai", padding: "20px 22px" }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
            <div style={{
              width: 38, height: 38, borderRadius: 10, flexShrink: 0,
              background: "linear-gradient(135deg, #8B5CF6, #6D28D9)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <Sparkles size={18} color="white" />
            </div>
            <div>
              <div className="jakarta" style={{ fontSize: 14, fontWeight: 800, color: "var(--fg)", marginBottom: 5 }}>
                Hey, Need Help? 👋
              </div>
              <div style={{ fontSize: 12, color: "var(--fg-2)", lineHeight: 1.6, maxWidth: 360 }}>
                BAD_REQUEST_ERROR resolves best when a payment link is sent within <strong>2 hours</strong> of the initial failure — conversion drops 61% after that window.
              </div>
              <button onClick={() => setTab("insights")} style={{
                marginTop: 11, padding: "6px 13px", borderRadius: 7,
                background: "linear-gradient(135deg, #8B5CF6, #6D28D9)",
                border: "none", color: "white", fontSize: 11, fontWeight: 500,
                cursor: "pointer", display: "flex", alignItems: "center", gap: 5,
              }}>
                <MessageSquare size={10} />
                View all insights →
              </button>
            </div>
          </div>
        </Card>

        {/* ── Agent Tier Breakdown ── */}
        <Card style={{ gridArea: "tiers", padding: "20px 22px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 14 }}>
            <TrendingUp size={15} color="var(--blue)" />
            <div className="jakarta" style={{ fontSize: 13.5, fontWeight: 700, color: "var(--fg)" }}>Agent Performance</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
            {loading ? <Sk h={150} /> : (metrics.agent_performance || []).map((row: any) => {
              const rowColor = row.tier === "T1" ? "#22C55E" : row.tier === "T2" ? "#3B82F6" : "#F59E0B";
              const desc = row.tier === "T1" ? "Rule-based instant retry" : row.tier === "T2" ? "AI 2-click & Hinglish agent" : "0% recovered by design (Fraud halt)";
              const tierName = row.tier === "T1" ? "T1 · AUTO-RETRY" : row.tier === "T2" ? "T2 · LLM RECOVERY" : "T3 · HUMAN ESCALATION";
              const displayRate = row.tier === "T3" ? "0% (Protected)" : row.rate;
              return (
              <div key={row.tier} style={{
                display: "flex", alignItems: "center", gap: 11,
                padding: "10px 12px", borderRadius: 9,
                background: "rgba(0,0,0,0.024)", border: "1px solid var(--border)",
              }}>
                <div style={{ width: 5, height: 26, borderRadius: 3, background: rowColor, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div className="mono" style={{ fontSize: 10.5, color: "var(--fg)", fontWeight: 600 }}>{tierName}</div>
                  <div style={{ fontSize: 9.5, color: "var(--fg-2)" }}>{desc} · {inr(row.amount || 0)} at risk</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div className="jakarta" style={{ fontSize: 14, fontWeight: 800, color: rowColor }}>{displayRate}</div>
                  <div style={{ fontSize: 9, color: "var(--fg-3)" }}>{row.cases} cases</div>
                </div>
              </div>
              )
            })}
          </div>
        </Card>

      </div>

      {/* ── Compliance & Stopping Rules Active Bar ── */}
      <Card style={{
        padding: "14px 20px",
        background: "linear-gradient(90deg, rgba(15,23,42,0.95), rgba(30,58,95,0.85))",
        border: "1px solid rgba(59,130,246,0.2)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 7,
            background: "rgba(34,197,94,0.15)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Shield size={15} color="var(--green)" />
          </div>
          <div>
            <div className="jakarta" style={{ fontSize: 12, fontWeight: 700, color: "#fff" }}>
              Enterprise Compliance & Guardrail Engine Active
            </div>
            <div style={{ fontSize: 10.5, color: "rgba(255,255,255,0.7)" }}>
              Strict enforcement of RBI TAT Circular (DPSS.629), TRAI TCCCPR 2018 (Max 2/day, 4h cooldown), and SHA-256 tamper-evident audit chaining.
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span className="mono" style={{ fontSize: 9, padding: "3px 7px", borderRadius: 4, background: "rgba(59,130,246,0.2)", color: "#93c5fd", border: "1px solid rgba(59,130,246,0.3)" }}>
            RBI TAT T+1 / T+5
          </span>
          <span className="mono" style={{ fontSize: 9, padding: "3px 7px", borderRadius: 4, background: "rgba(34,197,94,0.2)", color: "#86efac", border: "1px solid rgba(34,197,94,0.3)" }}>
            TRAI DND COMPLIANT
          </span>
          <span className="mono" style={{ fontSize: 9, padding: "3px 7px", borderRadius: 4, background: "rgba(139,92,246,0.2)", color: "#c4b5fd", border: "1px solid rgba(139,92,246,0.3)" }}>
            SHA-256 HASH CHAIN
          </span>
          <span className="mono" style={{ fontSize: 9, padding: "3px 7px", borderRadius: 4, background: "rgba(245,158,11,0.2)", color: "#fde68a", border: "1px solid rgba(245,158,11,0.3)" }}>
            MAX 3 RETRIES
          </span>
        </div>
      </Card>
    </div>
  );
}
