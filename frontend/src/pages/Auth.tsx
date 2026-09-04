import { useEffect, useRef, useState } from "react";
import { API_BASE } from "../hooks/useFetch";

interface Props { onSuccess: () => void; onBack: () => void; }

// ── Ambient network (lightweight version of the landing canvas) ────────────────
type Dot = { x: number; y: number; r: number; ph: number; isHub: boolean };
type Link = { a: number; b: number };

function buildAmbient(W: number, H: number) {
  const rng = (() => { let s = 13; return () => { s = Math.imul(s, 1664525) + 1013904223 | 0; return (s >>> 0) / 0xffffffff; }; })();

  const dots: Dot[] = [];
  const anchors: [number, number][] = [[0.5,0.12],[0.28,0.38],[0.72,0.35],[0.42,0.63],[0.6,0.8]];
  for (const [fx, fy] of anchors) {
    dots.push({ x: fx * W + (rng()-0.5)*W*0.06, y: fy * H + (rng()-0.5)*H*0.05, r: 4+rng()*2, ph: rng()*Math.PI*2, isHub: true });
  }
  for (let i = 0; i < 28; i++) {
    dots.push({ x: rng()*W*0.88+W*0.06, y: rng()*H*0.9+H*0.05, r: 1.2+rng()*2, ph: rng()*Math.PI*2, isHub: false });
  }

  const links: Link[] = [];
  for (let i = 0; i < dots.length; i++) {
    const lim = dots[i].isHub ? 5 : 2;
    let cnt = 0;
    const sorted = dots.map((d, j) => ({ j, d: i===j ? Infinity : Math.hypot(d.x-dots[i].x, d.y-dots[i].y) })).sort((a,b)=>a.d-b.d).slice(1);
    for (const { j, d } of sorted) {
      if (d > W*0.55 || cnt >= lim) break;
      if (!links.some(l=>(l.a===i&&l.b===j)||(l.a===j&&l.b===i))) { links.push({a:i,b:j}); cnt++; }
    }
  }

  type Tv = { link: number; t: number; spd: number };
  const tvs: Tv[] = [];
  links.forEach((_,i) => { if (rng()<0.5) tvs.push({link:i, t:rng(), spd:0.0008+rng()*0.0015}); });

  return { dots, links, tvs };
}

function col(tY: number, a: number) {
  const t = Number.isFinite(tY) ? Math.max(0,Math.min(1,tY)) : 0;
  const al = Number.isFinite(a)  ? Math.max(0,Math.min(1,a))  : 0;
  return `rgba(${Math.round(t*25)},${Math.round(204-t*120)},${Math.round(255-t*19)},${al})`;
}

function AmbientCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current; if (!cv) return;
    const ctx = cv.getContext("2d")!;
    let amb = buildAmbient(cv.offsetWidth, cv.offsetHeight);
    let tick = 0, raf: number;

    const resize = () => { cv.width = cv.offsetWidth; cv.height = cv.offsetHeight; amb = buildAmbient(cv.width, cv.height); };
    resize();

    function draw() {
      if (!cv || cv.width===0 || cv.height===0) { raf = requestAnimationFrame(draw); return; }
      const { dots, links, tvs } = amb;
      ctx.clearRect(0, 0, cv.width, cv.height);

      for (const l of links) {
        const a = dots[l.a], b = dots[l.b];
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = col((a.y+b.y)/2/cv.height, 0.1);
        ctx.lineWidth = 0.6; ctx.stroke();
      }

      for (const tv of tvs) {
        tv.t = (tv.t + tv.spd) % 1;
        const l = links[tv.link], a = dots[l.a], b = dots[l.b];
        const x = a.x + (b.x-a.x)*tv.t, y = a.y + (b.y-a.y)*tv.t;
        const tY = y/cv.height;
        const g = ctx.createRadialGradient(x,y,0,x,y,5);
        g.addColorStop(0, col(tY,0.65)); g.addColorStop(1, col(tY,0));
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x,y,5,0,Math.PI*2); ctx.fill();
        ctx.fillStyle = col(tY,0.9); ctx.beginPath(); ctx.arc(x,y,1.5,0,Math.PI*2); ctx.fill();
      }

      for (const n of dots) {
        const tY = n.y/cv.height, pulse = 0.7+0.3*Math.sin(tick*1.1+n.ph);
        if (n.isHub) {
          ctx.beginPath(); ctx.arc(n.x,n.y,n.r*2.6*pulse,0,Math.PI*2);
          ctx.strokeStyle = col(tY,0.14); ctx.lineWidth=0.7; ctx.stroke();
          const g = ctx.createRadialGradient(n.x,n.y,0,n.x,n.y,n.r*1.4);
          g.addColorStop(0,col(tY,0.45)); g.addColorStop(1,col(tY,0));
          ctx.fillStyle = g; ctx.beginPath(); ctx.arc(n.x,n.y,n.r*1.4,0,Math.PI*2); ctx.fill();
          ctx.fillStyle = col(tY,0.85); ctx.beginPath(); ctx.arc(n.x,n.y,n.r*0.6,0,Math.PI*2); ctx.fill();
        } else {
          const g = ctx.createRadialGradient(n.x,n.y,0,n.x,n.y,n.r*2);
          g.addColorStop(0,col(tY,0.28*pulse)); g.addColorStop(1,col(tY,0));
          ctx.fillStyle = g; ctx.beginPath(); ctx.arc(n.x,n.y,n.r*2,0,Math.PI*2); ctx.fill();
          ctx.fillStyle = col(tY,0.6*pulse); ctx.beginPath(); ctx.arc(n.x,n.y,n.r*0.55,0,Math.PI*2); ctx.fill();
        }
      }

      tick += 0.014;
      raf = requestAnimationFrame(draw);
    }

    draw();
    const ro = new ResizeObserver(resize); ro.observe(cv);
    return () => { cancelAnimationFrame(raf); ro.disconnect(); };
  }, []);

  return <canvas ref={ref} style={{ display: "block", width: "100%", height: "100%" }} />;
}

// ── Auth form ──────────────────────────────────────────────────────────────────
type Field = "email" | "password";

export default function Auth({ onSuccess, onBack }: Props) {
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");
  const [focus,    setFocus]    = useState<Field | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) { setError("Merchant email is required."); return; }
    if (!password)     { setError("Password is required."); return; }
    setError("");
    setLoading(true);
    fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    })
      .then(res => res.json())
      .then(data => {
        setLoading(false);
        if (data.success) {
          const parts = email.split('@');
          let mName = "Merchant";
          if (parts.length > 1) {
            const domain = parts[1].split('.')[0];
            mName = domain.charAt(0).toUpperCase() + domain.slice(1);
          }
          localStorage.setItem('merchantName', mName);
          localStorage.setItem('merchantEmail', email);
          onSuccess();
        } else {
          setError(data.error || "Invalid credentials");
        }
      })
      .catch(() => {
        setLoading(false);
        setError("🛜 - Network Error - 🛜!");
      });
  };

  const inputStyle = (f: Field): React.CSSProperties => ({
    width: "100%", padding: "13px 0",
    background: "none",
    border: "none",
    borderBottom: `1px solid ${focus === f ? "#1954ec" : "rgba(255,255,255,0.2)"}`,
    color: "#fff",
    fontSize: 14, fontWeight: 300,
    fontFamily: "Inter, sans-serif",
    outline: "none",
    transition: "border-color 0.2s",
    letterSpacing: "0.01em",
  });

  return (
    <div style={{ display: "flex", height: "100vh", background: "#070708", color: "#fff", overflow: "hidden" }}>

      {/* ── LEFT: form column ── */}
      <div style={{ flex: "0 0 56%", display: "flex", flexDirection: "column", padding: "27px 80px", overflowY: "auto" }}>

        {/* Nav row */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <svg width={10} height={10} viewBox="0 0 10 10">
              <polygon points="5,0 10,5 5,10 0,5" fill="none" stroke="#1954ec" strokeWidth={1} />
            </svg>
            <span style={{ fontSize: 10, fontWeight: 400, letterSpacing: "0.4em", fontFamily: "Inter, sans-serif" }}>ARTHRAKSHA</span>
          </div>
          <button onClick={onBack} style={{
            fontSize: 10, letterSpacing: "0.3em", color: "#8f8f93",
            background: "none", border: "none", cursor: "pointer",
            fontFamily: "Inter, sans-serif", textTransform: "uppercase",
          }}>
            ← Back
          </button>
        </div>

        {/* Form body */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", maxWidth: 400, paddingBottom: 60 }}>

          <div style={{ marginBottom: 12 }}>
            <span style={{ fontSize: 10, letterSpacing: "0.4em", color: "#8f8f93", fontFamily: "Inter, sans-serif", textTransform: "uppercase" }}>
              Merchant Access
            </span>
          </div>

          <h1 className="serif" style={{ fontSize: 52, fontWeight: 300, lineHeight: 1.1, margin: "0 0 48px", letterSpacing: "-0.01em" }}>
            Welcome<br />back.
          </h1>

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 36 }}>

            {/* Email */}
            <div>
              <label style={{ fontSize: 9, letterSpacing: "0.3em", color: "#8f8f93", fontFamily: "Inter, sans-serif", textTransform: "uppercase", display: "block", marginBottom: 10 }}>
                Merchant Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                onFocus={() => setFocus("email")}
                onBlur={() => setFocus(null)}
                placeholder="you@merchant.com"
                style={inputStyle("email")}
                autoComplete="email"
              />
            </div>

            {/* Password */}
            <div>
              <label style={{ fontSize: 9, letterSpacing: "0.3em", color: "#8f8f93", fontFamily: "Inter, sans-serif", textTransform: "uppercase", display: "block", marginBottom: 10 }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                onFocus={() => setFocus("password")}
                onBlur={() => setFocus(null)}
                placeholder="••••••••••••"
                style={{ ...inputStyle("password"), letterSpacing: password ? "0.2em" : "0.01em" }}
                autoComplete="current-password"
              />
            </div>

            {/* Error */}
            {error && (
              <div style={{ fontSize: 11, color: "#ef4444", fontFamily: "Inter, sans-serif", marginTop: -20 }}>
                {error}
              </div>
            )}

            {/* Submit */}
            <div style={{ paddingTop: 8, display: "flex", flexDirection: "column", gap: 14 }}>
              <button type="submit" disabled={loading} style={{
                padding: "14px 0",
                border: `1px solid ${loading ? "rgba(255,255,255,0.15)" : "rgba(255,255,255,0.45)"}`,
                background: "none", color: loading ? "rgba(255,255,255,0.35)" : "#fff",
                fontSize: 12, fontWeight: 400, letterSpacing: "0.12em",
                fontFamily: "Inter, sans-serif", cursor: loading ? "not-allowed" : "pointer",
                textTransform: "uppercase", transition: "all 0.2s",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
              }}>
                {loading ? (
                  <>
                    <Spinner />
                    Authenticating
                  </>
                ) : (
                  "Enter Dashboard"
                )}
              </button>

              <button type="button" style={{
                background: "none", border: "none", color: "#8f8f93",
                fontSize: 11, fontFamily: "Inter, sans-serif", cursor: "pointer",
                letterSpacing: "0.05em", alignSelf: "flex-start",
              }}>
                Forgot password?
              </button>
            </div>
          </form>

          {/* Demo hint */}
          <div style={{
            marginTop: 48,
            paddingTop: 24,
            borderTop: "1px solid rgba(255,255,255,0.08)",
          }}>
            <div style={{ fontSize: 9, letterSpacing: "0.25em", color: "#8f8f93", fontFamily: "Inter, sans-serif", textTransform: "uppercase", marginBottom: 8 }}>
              Demo mode
            </div>
            <div style={{ fontSize: 12, fontWeight: 300, color: "#8f8f93", fontFamily: "Inter, sans-serif", lineHeight: 1.6 }}>
              Enter any email and password to access the demo dashboard. All data shown is mock — no real API connection required.
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{ display: "flex", justifyContent: "space-between", paddingTop: 20 }}>
          <span style={{ fontSize: 9, color: "#8f8f93", fontFamily: "Inter, sans-serif", letterSpacing: "0.1em" }}>
            © 2026 ARTHRAKSHA
          </span>
          <span style={{ fontSize: 9, color: "#8f8f93", fontFamily: "Inter, sans-serif", letterSpacing: "0.1em" }}>
            RAZORPAY ECOSYSTEM
          </span>
        </div>
      </div>

      {/* ── RIGHT: ambient blockchain network ── */}
      <div style={{ flex: 1, position: "relative", borderLeft: "1px solid rgba(255,255,255,0.06)" }}>
        {/* Vignette so it blends with the left column edge */}
        <div style={{
          position: "absolute", inset: 0, zIndex: 1, pointerEvents: "none",
          background: "linear-gradient(to right, #070708 0%, transparent 12%)",
        }} />
        <AmbientCanvas />

        {/* Floating status card */}
        <div style={{
          position: "absolute", bottom: 48, left: "50%", transform: "translateX(-50%)",
          zIndex: 2, textAlign: "center",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "center", marginBottom: 8 }}>
            <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#22c55e", animation: "pulse-dot 2s infinite" }} />
            <span style={{ fontSize: 9, letterSpacing: "0.3em", color: "#8f8f93", fontFamily: "Inter, sans-serif", textTransform: "uppercase" }}>
              Recovery network active
            </span>
          </div>
          <div style={{ fontSize: 9, color: "rgba(255,255,255,0.2)", fontFamily: "Inter, sans-serif", letterSpacing: "0.1em" }}>
            6 nodes · 42 merchants · live
          </div>
        </div>
      </div>

    </div>
  );
}

// ── Tiny spinner ───────────────────────────────────────────────────────────────
function Spinner() {
  return (
    <svg width={12} height={12} viewBox="0 0 12 12" style={{ animation: "spin 0.8s linear infinite" }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <circle cx={6} cy={6} r={4.5} fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth={1.2} />
      <path d="M6 1.5 A4.5 4.5 0 0 1 10.5 6" fill="none" stroke="#fff" strokeWidth={1.2} strokeLinecap="round" />
    </svg>
  );
}
