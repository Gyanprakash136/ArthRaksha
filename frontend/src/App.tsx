import { useState, useEffect } from "react";
import { API_BASE } from "./hooks/useFetch";
import { LayoutDashboard, FileText, MessageCircle, Lightbulb, Settings, ChevronRight, Zap } from "lucide-react";
import Overview      from "./pages/Overview";
import Cases         from "./pages/Cases";
import Landing       from "./pages/Landing";
import Auth          from "./pages/Auth";
import Docs          from "./pages/Docs";
import Hinglish      from "./pages/Hinglish";
import Insights      from "./pages/Insights";

type Tab = "overview" | "cases" | "conversations" | "insights";

const NAV: { id: Tab; label: string; icon: React.ElementType; sub: string }[] = [
  { id: "overview",      label: "Overview",      icon: LayoutDashboard, sub: "Metrics & KPIs"  },
  { id: "cases",         label: "Case Explorer", icon: FileText,        sub: "Audit Trail"     },
  { id: "conversations", label: "Conversations", icon: MessageCircle,   sub: "Hinglish AI"     },
  { id: "insights",      label: "Insights",      icon: Lightbulb,       sub: "AI Intelligence" },
];

function NavBtn({ item, active, onClick }: { item: typeof NAV[0]; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: 10,
      padding: "9px 11px", borderRadius: 10,
      border: "none", cursor: "pointer", width: "100%", textAlign: "left",
      background: active ? "rgba(59,130,246,0.13)" : "transparent",
      transition: "background 0.15s",
    }}>
      <item.icon size={15} color={active ? "#60A5FA" : "rgba(255,255,255,0.38)"} />
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12.5, fontWeight: active ? 600 : 400, color: active ? "#fff" : "rgba(255,255,255,0.58)", lineHeight: 1.2 }}>{item.label}</div>
        <div style={{ fontSize: 9, color: "rgba(255,255,255,0.24)", marginTop: 1 }}>{item.sub}</div>
      </div>
      {active && <ChevronRight size={10} color="rgba(96,165,250,0.55)" />}
    </button>
  );
}

export default function App() {
  const [page, setPage] = useState<"landing" | "auth" | "dashboard" | "docs">("landing");
  const [tab, setTab] = useState<Tab>("overview");
  const [batchStatus, setBatchStatus] = useState<"idle" | "running" | "complete" | "error">("idle");
  const [batchProgress, setBatchProgress] = useState("");
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    if (batchStatus !== "running") return;
    const interval = setInterval(() => {
      fetch(`${API_BASE}/dashboard/batch/status`)
        .then(r => r.json())
        .then(d => {
          setBatchProgress(d.progress);
          if (d.status !== "running") {
            setBatchStatus(d.status);
            if (d.status === "complete") {
              setRefreshTick(t => t + 1);
            }
          }
        }).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [batchStatus]);

  const startBatch = async () => {
    if (batchStatus === "running") return;
    setBatchStatus("running");
    setBatchProgress("Starting...");
    try {
      const res = await fetch(`${API_BASE}/dashboard/batch/run`, { method: "POST" });
      if (!res.ok) setBatchStatus("error");
    } catch {
      setBatchStatus("error");
    }
  };

  const merchantName = localStorage.getItem("merchantName") || "Acme Corp";
  const merchantInitial = merchantName.charAt(0).toUpperCase();

  if (page === "landing") {
    return <Landing onEnter={() => setPage("auth")} onViewDocs={() => setPage("docs")} />;
  }

  if (page === "docs") {
    return <Docs onBack={() => setPage("landing")} />;
  }

  if (page === "auth") {
    return <Auth onSuccess={() => setPage("dashboard")} onBack={() => setPage("landing")} />;
  }

  const now     = new Date();
  const dayNum  = now.getDate();
  const dayName = now.toLocaleDateString("en-US", { weekday: "short" }).toUpperCase();
  const monthYr = now.toLocaleDateString("en-US", { month: "long", year: "numeric" });

  const active = NAV.find(n => n.id === tab)!;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>

      {/* ── SIDEBAR ─────────────────────────────────────────────────── */}
      <aside style={{
        width: "var(--sidebar-w)", flexShrink: 0,
        background: "var(--sidebar)",
        display: "flex", flexDirection: "column",
        overflow: "hidden",
      }}>

        {/* Logo */}
        <div style={{ padding: "18px 14px 14px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
            <div style={{
              width: 30, height: 30, borderRadius: 8, flexShrink: 0,
              background: "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <Zap size={14} color="white" fill="white" />
            </div>
            <div>
              <div className="jakarta" style={{ color: "#fff", fontWeight: 700, fontSize: 13.5, letterSpacing: "-0.02em" }}>ArthRaksha</div>
              <div className="mono" style={{ color: "rgba(255,255,255,0.28)", fontSize: 8.5 }}>Recovery AI · v2</div>
            </div>
          </div>
        </div>

        {/* Date widget */}
        <div style={{ padding: "12px 14px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 9, flexShrink: 0,
              background: "rgba(59,130,246,0.12)",
              border: "1px solid rgba(59,130,246,0.24)",
              display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            }}>
              <span className="jakarta" style={{ color: "#60A5FA", fontSize: 15, fontWeight: 800, lineHeight: 1 }}>{dayNum}</span>
              <span className="mono" style={{ color: "rgba(96,165,250,0.55)", fontSize: 7, lineHeight: 1 }}>{dayName}</span>
            </div>
            <div>
              <div style={{ color: "rgba(255,255,255,0.75)", fontSize: 11, fontWeight: 500 }}>{monthYr}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 2 }}>
                <div className="pulse" style={{ width: 5, height: 5, borderRadius: "50%", backgroundColor: "#22C55E" }} />
                <span style={{ color: "rgba(255,255,255,0.28)", fontSize: 9 }}>Batch active</span>
              </div>
            </div>
          </div>
        </div>

        {/* Nav items */}
        <nav style={{ flex: 1, padding: "10px 8px", display: "flex", flexDirection: "column", gap: 2, overflowY: "auto" }}>
          {NAV.map(item => (
            <NavBtn key={item.id} item={item} active={tab === item.id} onClick={() => setTab(item.id)} />
          ))}
        </nav>

        {/* Merchant card */}
        <div style={{ padding: "8px 8px 14px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 9,
            padding: "9px 10px", borderRadius: 10,
            background: "rgba(255,255,255,0.04)",
          }}>
            <div style={{
              width: 27, height: 27, borderRadius: 7, flexShrink: 0,
              background: "linear-gradient(135deg, #F97316, #EF4444)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <span style={{ color: "white", fontWeight: 700, fontSize: 11 }}>{merchantInitial}</span>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.72)", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{merchantName}</div>
              <div className="mono" style={{ fontSize: 8, color: "rgba(255,255,255,0.24)" }}>xyz_001</div>
            </div>
            <Settings size={11} color="rgba(255,255,255,0.24)" />
          </div>
        </div>
      </aside>

      {/* ── MAIN ────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 }}>

        {/* Top bar */}
        <div style={{
          height: 52, flexShrink: 0,
          background: "var(--card)",
          borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center",
          padding: "0 22px", gap: 12,
        }}>
          <div style={{ flex: 1, display: "flex", alignItems: "baseline", gap: 8 }}>
            <span className="jakarta" style={{ fontSize: 15, fontWeight: 700, color: "var(--fg)", letterSpacing: "-0.025em" }}>{active.label}</span>
            <span style={{ fontSize: 11, color: "var(--fg-3)" }}>{active.sub}</span>
          </div>
          <button onClick={startBatch} disabled={batchStatus === "running"} style={{
            padding: "6px 14px", borderRadius: 7,
            background: "linear-gradient(135deg, #3B82F6, #1D4ED8)",
            border: "none", color: "white", fontSize: 11.5, fontWeight: 600,
            cursor: batchStatus === "running" ? "not-allowed" : "pointer", 
            display: "flex", alignItems: "center", gap: 5,
            boxShadow: "0 2px 8px rgba(59,130,246,0.35)", opacity: batchStatus === "running" ? 0.8 : 1
          }}>
            {batchStatus === "running" ? (
              <>
                <div style={{ width: 10, height: 10, border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "#fff", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
                {batchProgress}
              </>
            ) : (
              <>
                <Zap size={11} fill="white" />
                Run Batch
              </>
            )}
            <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
          </button>
        </div>

        {/* Page */}
        <div style={{ flex: 1, overflow: "auto" }}>
          {tab === "overview"      && <Overview refreshTick={refreshTick} startBatch={startBatch} batchStatus={batchStatus} setTab={setTab} />}
          {tab === "cases"         && <Cases />}
          {tab === "conversations" && <Hinglish />}
          {tab === "insights"      && <Insights />}
        </div>
      </div>
    </div>
  );
}
