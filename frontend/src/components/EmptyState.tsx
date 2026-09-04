import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: string;
  onAction?: () => void;
}

export default function EmptyState({ icon: Icon, title, description, action, onAction }: EmptyStateProps) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      height: "100%", minHeight: 300, padding: 32, textAlign: "center",
      background: "var(--card)", borderRadius: "var(--radius)",
      border: "1px solid var(--border)", boxShadow: "var(--shadow)",
    }}>
      <div style={{
        width: 56, height: 56, borderRadius: "50%",
        background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.2)",
        display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 20
      }}>
        <Icon size={24} color="#3B82F6" />
      </div>
      <h3 className="jakarta" style={{ fontSize: 18, fontWeight: 700, color: "var(--fg)", marginBottom: 8, marginTop: 0 }}>
        {title}
      </h3>
      <p style={{ fontSize: 13, color: "var(--fg-2)", lineHeight: 1.6, maxWidth: 340, margin: "0 0 24px" }}>
        {description}
      </p>
      {action && onAction && (
        <button onClick={onAction} style={{
          padding: "10px 18px", borderRadius: 8,
          background: "linear-gradient(135deg, #3B82F6, #1D4ED8)",
          border: "none", color: "white", fontSize: 13, fontWeight: 600,
          cursor: "pointer", display: "flex", alignItems: "center", gap: 6,
          boxShadow: "0 2px 10px rgba(59,130,246,0.35)",
        }}>
          {action}
        </button>
      )}
    </div>
  );
}
