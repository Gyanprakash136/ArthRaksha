import React from "react";

// ── Skeleton shimmer block ───────────────────────────────────────────────────
export function Skel({ w, h, r = 6 }: { w?: string | number; h: number; r?: number }) {
  return (
    <div
      className="skeleton"
      style={{ width: w ?? "100%", height: h, borderRadius: r, flexShrink: 0 }}
    />
  );
}

// ── API token badge ──────────────────────────────────────────────────────────
export function Tok({
  name,
  size = 13,
  style,
}: {
  name: string;
  size?: number;
  style?: React.CSSProperties;
}) {
  return (
    <span
      className="mono"
      style={{
        backgroundColor: "rgba(0,82,255,0.07)",
        color: "#0052FF",
        fontSize: size,
        padding: "1px 6px",
        borderRadius: 4,
        letterSpacing: "-0.01em",
        fontWeight: 500,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {`{{${name}}}`}
    </span>
  );
}

// ── Standard card ────────────────────────────────────────────────────────────
export function Card({
  children,
  style,
  topBorder,
  hover,
}: {
  children: React.ReactNode;
  style?: React.CSSProperties;
  topBorder?: string;
  hover?: boolean;
}) {
  return (
    <div
      style={{
        backgroundColor: "#FFFFFF",
        border: "1px solid #E2E8F0",
        borderRadius: 12,
        padding: 24,
        boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
        borderTop: topBorder ? `3px solid ${topBorder}` : undefined,
        transition: hover ? "box-shadow 0.2s, transform 0.2s" : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

// ── Inverted (dark) section ───────────────────────────────────────────────────
export function InvertedSection({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className="dot-pattern"
      style={{
        backgroundColor: "#0F172A",
        borderRadius: 20,
        padding: 40,
        border: "1px solid rgba(255,255,255,0.08)",
        position: "relative",
        overflow: "hidden",
        ...style,
      }}
    >
      {/* Radial glow */}
      <div
        style={{
          position: "absolute",
          top: -80,
          right: -80,
          width: 320,
          height: 320,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(0,82,255,0.12) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <div style={{ position: "relative", zIndex: 1 }}>{children}</div>
    </div>
  );
}

// ── Section label badge ───────────────────────────────────────────────────────
export function SectionBadge({
  label,
  dark,
  pulse,
  color,
}: {
  label: string;
  dark?: boolean;
  pulse?: boolean;
  color?: string;
}) {
  const bg   = dark ? "rgba(0,82,255,0.15)" : "rgba(0,82,255,0.07)";
  const text = dark ? "#7BA7FF"             : "#0052FF";
  const dot  = color || (dark ? "#7BA7FF" : "#0052FF");
  return (
    <div
      className="mono"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        backgroundColor: bg,
        border: `1px solid ${dark ? "rgba(0,82,255,0.3)" : "rgba(0,82,255,0.15)"}`,
        borderRadius: 20,
        padding: "3px 10px",
        fontSize: 10,
        fontWeight: 600,
        color: text,
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        userSelect: "none",
      }}
    >
      <div
        className={pulse ? "pulse" : undefined}
        style={{ width: 5, height: 5, borderRadius: "50%", backgroundColor: dot, flexShrink: 0 }}
      />
      {label}
    </div>
  );
}

// ── Semantic pill badge ───────────────────────────────────────────────────────
type BadgeVariant = "success" | "warning" | "danger" | "accent" | "muted";
const BADGE_MAP: Record<BadgeVariant, { bg: string; text: string; dot: string }> = {
  success: { bg: "#F0FDF4", text: "#27AE60", dot: "#27AE60" },
  warning: { bg: "#FFF7ED", text: "#F2994A", dot: "#F2994A" },
  danger:  { bg: "#FFF5F5", text: "#EB5757", dot: "#EB5757" },
  accent:  { bg: "rgba(0,82,255,0.07)", text: "#0052FF", dot: "#0052FF" },
  muted:   { bg: "#F1F5F9", text: "#64748B", dot: "#94A3B8" },
};

export function Badge({
  variant,
  children,
  pulse,
  mono,
}: {
  variant: BadgeVariant;
  children: React.ReactNode;
  pulse?: boolean;
  mono?: boolean;
}) {
  const m = BADGE_MAP[variant];
  return (
    <span
      className={mono ? "mono" : undefined}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        backgroundColor: m.bg,
        color: m.text,
        fontSize: mono ? 10 : 12,
        fontWeight: 500,
        padding: "2px 9px",
        borderRadius: 20,
        letterSpacing: mono ? "0.06em" : 0,
        textTransform: mono ? "uppercase" : undefined,
        whiteSpace: "nowrap",
      }}
    >
      {pulse && (
        <span
          className="pulse"
          style={{ width: 5, height: 5, borderRadius: "50%", backgroundColor: m.dot, flexShrink: 0 }}
        />
      )}
      {children}
    </span>
  );
}

// ── Gradient button ───────────────────────────────────────────────────────────
export function GradBtn({
  children,
  icon,
  pulse,
  onClick,
  small,
}: {
  children: React.ReactNode;
  icon?: React.ReactNode;
  pulse?: boolean;
  onClick?: () => void;
  small?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        background: "linear-gradient(135deg, #0052FF 0%, #4D7CFF 100%)",
        border: "none",
        borderRadius: 8,
        height: small ? 34 : 40,
        padding: small ? "0 14px" : "0 18px",
        color: "#FFFFFF",
        fontSize: small ? 13 : 14,
        fontWeight: 500,
        cursor: "pointer",
        fontFamily: "'Inter', sans-serif",
        boxShadow: "0 2px 8px rgba(0,82,255,0.35)",
        transition: "opacity 0.15s, box-shadow 0.15s",
      }}
      onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.opacity = "0.9")}
      onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.opacity = "1")}
    >
      {icon}
      {children}
      {pulse && (
        <span
          className="pulse"
          style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "rgba(255,255,255,0.7)" }}
        />
      )}
    </button>
  );
}

// ── Outline button ────────────────────────────────────────────────────────────
export function OutlineBtn({
  children,
  icon,
  variant,
  onClick,
  dark,
  small,
}: {
  children: React.ReactNode;
  icon?: React.ReactNode;
  variant?: BadgeVariant;
  onClick?: () => void;
  dark?: boolean;
  small?: boolean;
}) {
  const color = variant
    ? BADGE_MAP[variant].text
    : dark ? "rgba(255,255,255,0.7)" : "#64748B";
  const border = variant
    ? BADGE_MAP[variant].text
    : dark ? "rgba(255,255,255,0.15)" : "#E2E8F0";

  return (
    <button
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        backgroundColor: "transparent",
        border: `1px solid ${border}`,
        borderRadius: 8,
        height: small ? 32 : 38,
        padding: small ? "0 12px" : "0 16px",
        color,
        fontSize: small ? 12 : 13,
        fontWeight: 500,
        cursor: "pointer",
        fontFamily: "'Inter', sans-serif",
        transition: "background-color 0.15s",
        whiteSpace: "nowrap",
      }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.backgroundColor = variant ? `${BADGE_MAP[variant].bg}` : "rgba(0,0,0,0.03)"; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.backgroundColor = "transparent"; }}
    >
      {icon}
      {children}
    </button>
  );
}

// ── Progress bar ──────────────────────────────────────────────────────────────
export function ProgressBar({
  pct,
  color,
  loading,
  height = 6,
}: {
  pct?: number;
  color: string;
  loading?: boolean;
  height?: number;
}) {
  if (loading) {
    return <Skel h={height} r={height} />;
  }
  return (
    <div style={{ height, backgroundColor: "#F1F5F9", borderRadius: height, overflow: "hidden" }}>
      <div
        style={{
          height: "100%",
          width: `${pct ?? 0}%`,
          background: color === "accent"
            ? "linear-gradient(135deg, #0052FF 0%, #4D7CFF 100%)"
            : color,
          borderRadius: height,
          transition: "width 0.8s ease",
        }}
      />
    </div>
  );
}

// ── Avatar circle ─────────────────────────────────────────────────────────────
export function Avatar({ initials, size = 36, loading }: { initials?: string; size?: number; loading?: boolean }) {
  if (loading) return <Skel w={size} h={size} r={size} />;
  return (
    <div
      style={{
        width: size, height: size, borderRadius: "50%",
        background: "linear-gradient(135deg, #0052FF 0%, #4D7CFF 100%)",
        color: "#fff",
        fontSize: Math.round(size * 0.35),
        fontFamily: "'Calistoga', serif",
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0,
      }}
    >
      {initials}
    </div>
  );
}
