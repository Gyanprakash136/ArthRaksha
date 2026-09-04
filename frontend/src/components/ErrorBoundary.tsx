import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ArthRaksha Uncaught Frontend Error:", error, errorInfo);
  }

  private handleReset = () => {
    localStorage.clear();
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#070708",
          color: "#fff",
          padding: 24,
          fontFamily: "Inter, sans-serif"
        }}>
          <div style={{
            maxWidth: 520,
            width: "100%",
            background: "#111827",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: 16,
            padding: 32,
            boxShadow: "0 20px 50px rgba(0,0,0,0.5)"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
              <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: "rgba(239, 68, 68, 0.15)",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "#EF4444", fontSize: 20
              }}>
                ⚠️
              </div>
              <div>
                <div style={{ fontSize: 17, fontWeight: 700, color: "#fff" }}>Rendering Error Detected</div>
                <div style={{ fontSize: 12, color: "rgba(255,255,255,0.4)" }}>ArthRaksha UI encountered an issue</div>
              </div>
            </div>

            <div style={{
              background: "rgba(0,0,0,0.4)",
              borderRadius: 8,
              padding: 14,
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 12,
              color: "#FCA5A5",
              marginBottom: 20,
              overflowX: "auto"
            }}>
              {this.state.error?.message || "Unknown rendering exception"}
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={() => window.location.reload()}
                style={{
                  flex: 1,
                  padding: "10px 16px",
                  borderRadius: 8,
                  background: "#3B82F6",
                  color: "#fff",
                  border: "none",
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: "pointer"
                }}
              >
                Reload Dashboard
              </button>
              <button
                onClick={this.handleReset}
                style={{
                  padding: "10px 16px",
                  borderRadius: 8,
                  background: "rgba(255,255,255,0.08)",
                  color: "rgba(255,255,255,0.7)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  fontWeight: 500,
                  fontSize: 13,
                  cursor: "pointer"
                }}
              >
                Reset Session
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
