import { useEffect, useRef } from "react";

interface Props { onEnter: () => void; }

// ── Blockchain payment network ─────────────────────────────────────────────────

type NetNode = {
  x: number; y: number;
  r: number;          // display radius
  phase: number;      // for pulse animation
  isHub: boolean;     // hub = larger, more connections
  label?: string;     // optional label (Razorpay, Bank, etc.)
};
type NetEdge  = { a: number; b: number };
type Traveler = { edge: number; t: number; spd: number; glow: boolean };

// Seeded PRNG for stable layout across resizes
function mkRng(seed: number) {
  let s = seed;
  return () => { s = Math.imul(s, 1664525) + 1013904223 | 0; return (s >>> 0) / 0xffffffff; };
}

function buildNetwork(W: number, H: number) {
  const rng   = mkRng(7);
  const nodes: NetNode[] = [];

  // Named hub nodes — payment ecosystem anchors
  const hubs: [number, number, string][] = [
    [0.50, 0.11, "RZRPAY"],
    [0.25, 0.32, "BANK"],
    [0.72, 0.28, "UPI"],
    [0.38, 0.54, "WALLET"],
    [0.65, 0.58, "NODAL"],
    [0.50, 0.78, "RECOVER"],
  ];
  for (const [fx, fy, label] of hubs) {
    nodes.push({
      x: fx * W + (rng() - 0.5) * W * 0.06,
      y: fy * H + (rng() - 0.5) * H * 0.04,
      r: 5 + rng() * 2.5,
      phase: rng() * Math.PI * 2,
      isHub: true,
      label,
    });
  }

  // Merchant / wallet satellite nodes
  for (let i = 0; i < 38; i++) {
    nodes.push({
      x: rng() * W * 0.88 + W * 0.06,
      y: rng() * H * 0.92 + H * 0.04,
      r: 1.4 + rng() * 2.2,
      phase: rng() * Math.PI * 2,
      isHub: false,
    });
  }

  // Edges — connect by proximity; hubs get more connections
  const edges: NetEdge[] = [];
  const connCount = new Array(nodes.length).fill(0);
  for (let i = 0; i < nodes.length; i++) {
    const limit = nodes[i].isHub ? 7 : 3;
    const sorted = nodes
      .map((n, j) => {
        if (i === j) return { j, d: Infinity };
        const dx = nodes[i].x - n.x, dy = nodes[i].y - n.y;
        return { j, d: Math.hypot(dx, dy) };
      })
      .sort((a, b) => a.d - b.d)
      .slice(1);

    for (const { j, d } of sorted) {
      if (d > W * 0.52) break;
      if (connCount[i] >= limit) break;
      if (edges.some(e => (e.a === i && e.b === j) || (e.a === j && e.b === i))) continue;
      edges.push({ a: i, b: j });
      connCount[i]++;
      connCount[j]++;
    }
  }

  // Transaction travelers — particles that ride the edges
  const travelers: Traveler[] = [];
  edges.forEach((_, i) => {
    if (rng() < 0.55) {
      travelers.push({ edge: i, t: rng(), spd: 0.0007 + rng() * 0.0018, glow: rng() > 0.55 });
    }
    if (rng() < 0.25) {
      travelers.push({ edge: i, t: (rng() + 0.5) % 1, spd: 0.0007 + rng() * 0.0018, glow: rng() > 0.7 });
    }
  });

  return { nodes, edges, travelers };
}

// Interpolate cyan (#00CCFF) → cobalt (#1954EC) by y fraction
function nodeColor(tY: number, alpha: number): string {
  const t = Number.isFinite(tY) ? Math.max(0, Math.min(1, tY)) : 0;
  const r = Math.round(t * 25);
  const g = Math.round(204 - t * 120);
  const b = Math.round(255 - t * 19);
  const a = Number.isFinite(alpha) ? Math.max(0, Math.min(1, alpha)) : 0;
  return `rgba(${r},${g},${b},${a})`;
}

function ParticleCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;

    let net = buildNetwork(canvas.offsetWidth, canvas.offsetHeight);
    let t = 0, raf: number;

    const resize = () => {
      canvas.width  = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      net = buildNetwork(canvas.width, canvas.height);
    };
    resize();

    function draw() {
      if (!canvas || canvas.width === 0 || canvas.height === 0) { raf = requestAnimationFrame(draw); return; }
      const { nodes, edges, travelers } = net;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // ── Edges ──
      for (const e of edges) {
        const na = nodes[e.a], nb = nodes[e.b];
        const tY = (na.y + nb.y) / 2 / canvas.height;
        ctx.beginPath();
        ctx.moveTo(na.x, na.y);
        ctx.lineTo(nb.x, nb.y);
        ctx.strokeStyle = nodeColor(tY, 0.12);
        ctx.lineWidth   = 0.7;
        ctx.stroke();
      }

      // ── Travelers (transaction particles) ──
      for (const tv of travelers) {
        tv.t = (tv.t + tv.spd) % 1;
        const e  = edges[tv.edge];
        const na = nodes[e.a], nb = nodes[e.b];
        const x  = na.x + (nb.x - na.x) * tv.t;
        const y  = na.y + (nb.y - na.y) * tv.t;
        const tY = y / canvas.height;

        if (tv.glow) {
          // Glow corona
          const grd = ctx.createRadialGradient(x, y, 0, x, y, 6);
          grd.addColorStop(0, nodeColor(tY, 0.7));
          grd.addColorStop(1, nodeColor(tY, 0));
          ctx.fillStyle = grd;
          ctx.beginPath();
          ctx.arc(x, y, 6, 0, Math.PI * 2);
          ctx.fill();
        }

        ctx.fillStyle = nodeColor(tY, tv.glow ? 1 : 0.75);
        ctx.beginPath();
        ctx.arc(x, y, tv.glow ? 1.8 : 1.2, 0, Math.PI * 2);
        ctx.fill();
      }

      // ── Nodes ──
      for (const n of nodes) {
        const tY    = n.y / canvas.height;
        const pulse = 0.7 + 0.3 * Math.sin(t * 1.1 + n.phase);

        if (n.isHub) {
          // Outer ring
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r * 2.8 * pulse, 0, Math.PI * 2);
          ctx.strokeStyle = nodeColor(tY, 0.18);
          ctx.lineWidth   = 0.8;
          ctx.stroke();

          // Mid ring
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r * 1.7, 0, Math.PI * 2);
          ctx.strokeStyle = nodeColor(tY, 0.35);
          ctx.lineWidth   = 0.7;
          ctx.stroke();

          // Glow fill
          const grd = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 1.5);
          grd.addColorStop(0, nodeColor(tY, 0.55));
          grd.addColorStop(1, nodeColor(tY, 0));
          ctx.fillStyle = grd;
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r * 1.5, 0, Math.PI * 2);
          ctx.fill();

          // Core
          ctx.fillStyle = nodeColor(tY, 0.9);
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r * 0.65, 0, Math.PI * 2);
          ctx.fill();

          // Label
          if (n.label) {
            ctx.fillStyle   = nodeColor(tY, 0.55);
            ctx.font        = `200 8px 'Inter', sans-serif`;
            ctx.textAlign   = "center";
            ctx.letterSpacing = "0.15em";
            ctx.fillText(n.label, n.x, n.y + n.r * 3.2);
            ctx.letterSpacing = "0px";
          }
        } else {
          // Satellite glow
          const grd = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 2);
          grd.addColorStop(0, nodeColor(tY, 0.35 * pulse));
          grd.addColorStop(1, nodeColor(tY, 0));
          ctx.fillStyle = grd;
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r * 2, 0, Math.PI * 2);
          ctx.fill();

          // Core dot
          ctx.fillStyle = nodeColor(tY, 0.7 * pulse);
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r * 0.6, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      t += 0.014;
      raf = requestAnimationFrame(draw);
    }

    draw();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    return () => { cancelAnimationFrame(raf); ro.disconnect(); };
  }, []);

  return <canvas ref={ref} style={{ display: "block", width: "100%", height: "100%" }} />;
}

// ── SVG Circle Stat ────────────────────────────────────────────────────────────
function CircleStat({ value, caption, arc = 0.72 }: { value: string; caption: string; arc?: number }) {
  const R    = 84;
  const circ = 2 * Math.PI * R;
  const fill = circ * arc;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 16 }}>
      <svg width={190} height={190} viewBox="0 0 190 190" style={{ overflow: "visible" }}>
        <circle cx={95} cy={95} r={R} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={1} />
        <circle cx={95} cy={95} r={R} fill="none"
          stroke="#1954ec" strokeWidth={1}
          strokeDasharray={`${fill} ${circ}`}
          strokeLinecap="butt"
          transform="rotate(-90 95 95)"
        />
        <text x={95} y={95} textAnchor="middle" dominantBaseline="middle"
          style={{ fill: "#ffffff", fontSize: 44, fontWeight: 300, fontFamily: "'Inter', sans-serif" }}>
          {value}
        </text>
      </svg>
      <div style={{ fontSize: 10, color: "#8f8f93", letterSpacing: "0.2em", textTransform: "uppercase" as const, lineHeight: 1.55, maxWidth: 148, fontFamily: "Inter, sans-serif" }}>
        {caption}
      </div>
    </div>
  );
}

// ── Hairline divider ───────────────────────────────────────────────────────────
function Hr() {
  return <div style={{ width: "55%", height: 1, background: "rgba(255,255,255,0.11)", margin: "59px 0" }} />;
}

// ── Caption label ──────────────────────────────────────────────────────────────
function Cap({ children }: { children: string }) {
  return (
    <div style={{ fontSize: 10, letterSpacing: "0.4em", color: "#8f8f93", fontFamily: "Inter, sans-serif", marginBottom: 23, textTransform: "uppercase" as const }}>
      {children}
    </div>
  );
}

// ── Landing ────────────────────────────────────────────────────────────────────
export default function Landing({ onEnter, onViewDocs }: { onEnter: () => void, onViewDocs: () => void }) {
  return (
    <div style={{ position: "relative", background: "#070708", minHeight: "100vh", color: "#fff", overflowX: "hidden" }}>

      {/* Persistent particle field — right 44% */}
      <div style={{ position: "fixed", top: 0, right: 0, width: "44%", height: "100vh", zIndex: 0, pointerEvents: "none" }}>
        <ParticleCanvas />
      </div>

      {/* Scrollable content */}
      <div style={{ position: "relative", zIndex: 1 }}>

        {/* ── NAV ── */}
        <nav style={{
          position: "fixed", top: 0, left: 0, right: 0, zIndex: 50,
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "27px 40px", pointerEvents: "none",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, pointerEvents: "auto" }}>
            <svg width={10} height={10} viewBox="0 0 10 10">
              <polygon points="5,0 10,5 5,10 0,5" fill="none" stroke="#1954ec" strokeWidth={1} />
            </svg>
            <span style={{ fontSize: 10, fontWeight: 400, letterSpacing: "0.4em", color: "#fff", fontFamily: "Inter, sans-serif" }}>
              ARTHRAKSHA
            </span>
          </div>
          <button onClick={onEnter} style={{
            display: "flex", alignItems: "center", gap: 8,
            fontSize: 10, fontWeight: 400, letterSpacing: "0.4em", color: "#fff",
            background: "none", border: "none", cursor: "pointer",
            fontFamily: "Inter, sans-serif", pointerEvents: "auto",
          }}>
            ENTER DASHBOARD
            <svg width={10} height={10} viewBox="0 0 10 10">
              <polygon points="5,0 10,5 5,10 0,5" fill="none" stroke="#fff" strokeWidth={0.8} />
            </svg>
          </button>
        </nav>

        {/* ── HERO ── */}
        <section style={{ position: "relative", minHeight: "100vh", display: "flex", flexDirection: "column", justifyContent: "center", padding: "120px 80px 180px 80px" }}>
          
          <div style={{ position: "absolute", inset: 0, opacity: 0.15 }}>
            <div style={{ width: "100%", height: "100%", backgroundImage: "radial-gradient(circle at 100% 0%, #1954ec 0%, transparent 40%)" }} />
          </div>

          <div style={{ position: "relative", zIndex: 2, maxWidth: 580 }}>
            <Cap>Enterprise Payment Recovery · India</Cap>

            <h1 className="serif" style={{ fontSize: 68, fontWeight: 300, lineHeight: 1.1, margin: "0 0 32px", letterSpacing: "-0.01em" }}>
              Intelligent<br />
              Revenue<br />
              <span style={{ color: "#1954ec" }}>Recovery</span><br />
              for Enterprise<br />
              India.
            </h1>

            <p style={{ fontSize: 15, fontWeight: 300, lineHeight: 1.6, color: "#8f8f93", maxWidth: 460, margin: 0, fontFamily: "Inter, sans-serif" }}>
              Stop losing revenue to failed transactions. ArthRaksha combines deterministic routing, conversational AI, and human-in-the-loop workflows to recover dropped payments at scale—while preserving customer trust.
            </p>

            <div style={{ marginTop: 39, display: "flex", gap: 20, alignItems: "center" }}>
              <button onClick={onEnter} style={{
                fontSize: 13, fontWeight: 400, color: "#fff",
                border: "1px solid rgba(255,255,255,0.45)", background: "none",
                padding: "11px 28px", cursor: "pointer",
                fontFamily: "Inter, sans-serif", letterSpacing: "0.05em",
              }}>
                Enter Dashboard
              </button>
              <button onClick={onViewDocs} style={{
                fontSize: 13, fontWeight: 300, color: "#8f8f93",
                border: "none", background: "none", cursor: "pointer",
                fontFamily: "Inter, sans-serif",
              }}>
                View Documentation →
              </button>
            </div>
          </div>

          {/* Scroll prompt */}
          <div style={{ position: "absolute", bottom: 48, left: 80, display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 12 }}>
            <span style={{ fontSize: 10, letterSpacing: "0.4em", color: "#fff", fontFamily: "Inter, sans-serif", textTransform: "uppercase" }}>
              Scroll to Explore
            </span>
            <div style={{ width: 1, height: 60, background: "rgba(255,255,255,0.4)" }} />
          </div>
        </section>

        {/* ── STATS ── */}
        <section style={{ padding: "0 80px 99px" }}>
          <Hr />
          <Cap>Platform Performance Metrics</Cap>
          <div style={{ display: "flex", gap: 63, flexWrap: "wrap" }}>
            <CircleStat value="65%"  caption="Average recovery rate across all agent tiers"    arc={0.65} />
            <CircleStat value="3.7L" caption="Crore rupees recovered per enterprise batch"     arc={0.82} />
            <CircleStat value="10K+" caption="Failed payment cases processed and closed"        arc={0.91} />
          </div>
        </section>

        {/* ── ENGINE INTRO ── */}
        <section style={{ padding: "0 80px 99px" }}>
          <Hr />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 59, maxWidth: "55%" }}>
            <h2 className="serif" style={{ fontSize: 48, fontWeight: 300, lineHeight: 1.13, margin: 0 }}>
              Revenue<br />
              recovery,<br />
              engineered<br />
              for scale.
            </h2>
            <div style={{ paddingTop: 6 }}>
              <p style={{ fontSize: 14, fontWeight: 300, lineHeight: 1.6, color: "#8f8f93", margin: "0 0 23px", fontFamily: "Inter, sans-serif" }}>
                Every failed transaction is unique. ArthRaksha intelligently routes failures through a dynamic decision matrix. From instant retries to culturally-calibrated conversational negotiations, we ensure every salvageable payment is captured.
              </p>
              <p style={{ fontSize: 14, fontWeight: 300, lineHeight: 1.6, color: "#8f8f93", margin: 0, fontFamily: "Inter, sans-serif" }}>
                Our infrastructure learns continuously, optimizing recovery paths and reducing operational overhead with every processed batch.
              </p>
            </div>
          </div>
        </section>

        {/* ── TIERS ── */}
        {([
          {
            stage: "T1", name: "Deterministic.", tag: "Automated Retry Engine",
            body: "Instantly processes low-complexity failures like insufficient funds or temporary gateway timeouts. Resolves standard declines with zero latency and high precision. 40% of standard drops are recovered instantly.",
            rate: "42%", rcap: "Recovery rate, T1 tier",
          },
          {
            stage: "T2", name: "Conversational.", tag: "AI Voice & Chat Agents",
            body: "Deploys empathetic, context-aware AI agents that engage customers in natural Hinglish. By understanding the context behind the drop, our agents negotiate alternative payment methods securely. 78% resolution on first contact.",
            rate: "78%", rcap: "Resolution on first contact",
          },
          {
            stage: "T3", name: "Specialist.", tag: "Human-in-the-Loop",
            body: "Seamlessly escalates high-ticket or high-risk transactions to human specialists. Specialists inherit full conversation context, intent analysis, and recommended negotiation strategies to close the loop securely.",
            rate: "₹12L", rcap: "Average case value at T3",
          },
        ] as const).map(tier => (
          <section key={tier.stage} style={{ padding: "0 80px 99px" }}>
            <Hr />
            <div style={{ display: "flex", gap: 59, maxWidth: "55%" }}>
              <div style={{ flex: 1 }}>
                <Cap>{tier.tag}</Cap>
                <h2 className="serif" style={{ fontSize: 45, fontWeight: 300, lineHeight: 1.13, margin: "0 0 0" }}>
                  {tier.stage} /
                  <br />
                  <span>{tier.name}</span>
                </h2>
              </div>
              <div style={{ flex: 1, paddingTop: 46 }}>
                <p style={{ fontSize: 14, fontWeight: 300, lineHeight: 1.6, color: "#8f8f93", margin: "0 0 32px", fontFamily: "Inter, sans-serif" }}>
                  {tier.body}
                </p>
                <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
                  <span style={{ fontSize: 52, fontWeight: 300, lineHeight: 1, fontFamily: "Inter, sans-serif", fontVariantNumeric: "tabular-nums" }}>
                    {tier.rate}
                  </span>
                  <span style={{ fontSize: 10, color: "#8f8f93", letterSpacing: "0.2em", textTransform: "uppercase", maxWidth: 120, lineHeight: 1.4, fontFamily: "Inter, sans-serif" }}>
                    {tier.rcap}
                  </span>
                </div>
              </div>
            </div>
          </section>
        ))}

        {/* ── HINGLISH ── */}
        <section style={{ padding: "0 80px 99px" }}>
          <Hr />
          <Cap>Conversational Recovery · Language</Cap>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 59, maxWidth: "55%" }}>
            <h2 className="serif" style={{ fontSize: 48, fontWeight: 300, lineHeight: 1.13, margin: 0 }}>
              The language<br />
              of trust.
            </h2>
            <div>
              <p style={{ fontSize: 14, fontWeight: 300, lineHeight: 1.6, color: "#8f8f93", margin: "0 0 27px", fontFamily: "Inter, sans-serif" }}>
                Recovery is a trust transaction. ArthRaksha's LLM agent writes in the register the customer actually reads — Hinglish, the natural blend of Hindi and English spoken by 300 million urban Indians.
              </p>
              {/* Sample conversation */}
              <div style={{ borderLeft: "1px solid rgba(255,255,255,0.12)", paddingLeft: 20 }}>
                {[
                  { who: "ArthRaksha AI", text: "Namaste! 🙏 Aapka ₹5,000 ka payment fail ho gaya. Koi baat nahi — yeh link try karein: pay.arthraksha.io/r/jkl" },
                  { who: "Customer",      text: "Oh no — kya hua? Main sochti thi ho gaya tha." },
                  { who: "ArthRaksha AI", text: "Bank gateway issue tha, aapka paisa safe hai. Sirf 2 click mein ho jayega ✓" },
                  { who: "Customer",      text: "Done! Paid ho gaya" },
                ].map((msg, i) => (
                  <div key={i} style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 9, letterSpacing: "0.2em", color: msg.who === "ArthRaksha AI" ? "#1954ec" : "#8f8f93", textTransform: "uppercase", marginBottom: 4, fontFamily: "Inter, sans-serif" }}>
                      {msg.who}
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 300, lineHeight: 1.55, color: msg.who === "ArthRaksha AI" ? "rgba(255,255,255,0.82)" : "#8f8f93", fontFamily: "Inter, sans-serif" }}>
                      {msg.text}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── CACHE INTELLIGENCE ── */}
        <section style={{ padding: "0 80px 99px" }}>
          <Hr />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 59, maxWidth: "55%" }}>
            <h2 className="serif" style={{ fontSize: 48, fontWeight: 300, lineHeight: 1.13, margin: 0 }}>
              Intelligence<br />
              that<br />
              compounds.
            </h2>
            <div>
              <p style={{ fontSize: 14, fontWeight: 300, lineHeight: 1.6, color: "#8f8f93", margin: "0 0 32px", fontFamily: "Inter, sans-serif" }}>
                Each batch warms a semantic cache. Error patterns learned in one run reduce LLM cost in the next. At 45% cache hit rate, ArthRaksha saves 15,000 tokens per batch — compounding across every merchant in the ecosystem.
              </p>
              <div style={{ display: "flex", gap: 39 }}>
                {[
                  { n: "45%", label: "Cache hit rate" },
                  { n: "15K", label: "Tokens saved / batch" },
                ].map(s => (
                  <div key={s.n}>
                    <div style={{ fontSize: 38, fontWeight: 300, lineHeight: 1, fontFamily: "Inter, sans-serif", fontVariantNumeric: "tabular-nums" }}>{s.n}</div>
                    <div style={{ fontSize: 10, color: "#8f8f93", letterSpacing: "0.2em", textTransform: "uppercase", marginTop: 8, fontFamily: "Inter, sans-serif" }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── CTA ── */}
        <section style={{ padding: "0 80px 119px" }}>
          <Hr />
          <h2 className="serif" style={{ fontSize: 58, fontWeight: 300, lineHeight: 1.13, margin: "0 0 39px", maxWidth: 480 }}>
            Begin recovery<br />
            intelligence.
          </h2>
          <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
            <button onClick={onEnter} style={{
              fontSize: 13, fontWeight: 400, color: "#fff",
              border: "1px solid rgba(255,255,255,0.45)", background: "none",
              padding: "13px 32px", cursor: "pointer",
              fontFamily: "Inter, sans-serif", letterSpacing: "0.08em",
            }}>
              Enter Dashboard
            </button>
            <span style={{ fontSize: 13, color: "#8f8f93", fontFamily: "Inter, sans-serif", fontWeight: 300 }}>
              Powered by Advanced Razorpay Intelligence
            </span>
          </div>
        </section>

        {/* ── FOOTER ── */}
        <footer style={{ padding: "39px 80px 54px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 20 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 9 }}>
                <svg width={8} height={8} viewBox="0 0 10 10">
                  <polygon points="5,0 10,5 5,10 0,5" fill="none" stroke="#1954ec" strokeWidth={1} />
                </svg>
                <span style={{ fontSize: 10, letterSpacing: "0.4em", color: "#fff", fontFamily: "Inter, sans-serif" }}>ARTHRAKSHA</span>
              </div>
              <div style={{ fontSize: 10, color: "#8f8f93", fontFamily: "Inter, sans-serif", lineHeight: 1.6 }}>
                AI-powered payment recovery for India's digital economy.<br />
                Built on Razorpay webhook intelligence.
              </div>
            </div>
            <div style={{ display: "flex", gap: 32 }}>
              {["Documentation", "API Reference", "Recovery Engine", "Contact"].map(link => (
                <button key={link} style={{
                  fontSize: 10, color: "#8f8f93", background: "none",
                  border: "none", cursor: "pointer",
                  fontFamily: "Inter, sans-serif", letterSpacing: "0.05em", padding: 0,
                }}>
                  {link}
                </button>
              ))}
            </div>
          </div>
          <div style={{ marginTop: 39, fontSize: 9, color: "#8f8f93", fontFamily: "Inter, sans-serif", letterSpacing: "0.1em" }}>
            © 2026 ARTHRAKSHA · RECOVERY INTELLIGENCE PLATFORM · INDIA
          </div>
        </footer>

      </div>
    </div>
  );
}
