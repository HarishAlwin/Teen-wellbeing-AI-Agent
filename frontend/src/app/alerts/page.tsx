"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface Alert {
  id: string;
  user_id: string;
  conversation_id: string | null;
  risk_level: "HIGH_CONCERN" | "IMMEDIATE_SAFETY";
  reason: string;
  triggered_at: string;
  notified_channel: string;
  status: "pending" | "notified" | "acknowledged" | "resolved";
}

interface AlertsResponse {
  total: number;
  offset: number;
  limit: number;
  alerts: Alert[];
}

function getRiskColor(level: string) {
  if (level === "IMMEDIATE_SAFETY") return "#ff2d55";
  if (level === "HIGH_CONCERN") return "#ff9500";
  return "#00d4ff";
}

function getStatusColor(status: string) {
  if (status === "resolved") return "#34c759";
  if (status === "acknowledged") return "#00d4ff";
  if (status === "notified") return "#ff9500";
  return "#ff2d55"; // pending
}

function formatTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const tick = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(tick);
  }, []);

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({ limit: "50", offset: "0" });
      if (filter !== "all") params.set("risk_level", filter);
      const res = await fetch(`${API_BASE}/alerts?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: AlertsResponse = await res.json();
      setAlerts(data.alerts);
      setTotal(data.total);
      setError(null);
    } catch (e: unknown) {
      setError(`Failed to load alerts: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000); // auto-refresh every 30s
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const updateStatus = async (alertId: string, newStatus: string) => {
    setUpdatingId(alertId);
    try {
      const res = await fetch(
        `${API_BASE}/alerts/${alertId}/status?new_status=${newStatus}`,
        { method: "PATCH" }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchAlerts();
    } catch (e: unknown) {
      console.error("Status update failed:", e);
    } finally {
      setUpdatingId(null);
    }
  };

  const pendingCount = alerts.filter((a) => a.status === "pending").length;
  const immediateCount = alerts.filter((a) => a.risk_level === "IMMEDIATE_SAFETY").length;

  return (
    <div style={{ minHeight: "100vh", background: "#000d1a", color: "#e0f4ff", fontFamily: "'Inter', monospace" }}>
      {/* ── HUD Top Bar ── */}
      <div style={{
        borderBottom: "1px solid rgba(0,212,255,0.2)",
        background: "rgba(0,10,25,0.95)",
        padding: "16px 32px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        zIndex: 100,
        backdropFilter: "blur(12px)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{
            width: 10, height: 10, borderRadius: "50%",
            background: pendingCount > 0 ? "#ff2d55" : "#34c759",
            boxShadow: `0 0 12px ${pendingCount > 0 ? "#ff2d55" : "#34c759"}`,
            animation: pendingCount > 0 ? "pulse 1s infinite" : "none",
          }} />
          <span style={{ color: "#00d4ff", fontWeight: 700, letterSpacing: 2, fontSize: 13 }}>
            COUNSELOR ALERT DASHBOARD
          </span>
          <span style={{ color: "#4a9eff", fontSize: 11, opacity: 0.7 }}>
            // RESTRICTED ACCESS — NOT FOR TEEN USERS
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 24, fontSize: 11, color: "#4a9eff" }}>
          {immediateCount > 0 && (
            <span style={{ color: "#ff2d55", fontWeight: 700, letterSpacing: 1 }}>
              ⚠ {immediateCount} IMMEDIATE SAFETY
            </span>
          )}
          <span>{pendingCount} PENDING</span>
          <span>{now.toLocaleTimeString("en-IN")}</span>
          <button
            onClick={fetchAlerts}
            style={{
              background: "rgba(0,212,255,0.1)",
              border: "1px solid rgba(0,212,255,0.3)",
              color: "#00d4ff",
              padding: "4px 12px",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 11,
              letterSpacing: 1,
            }}
          >
            REFRESH
          </button>
        </div>
      </div>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>
        {/* ── Stats Row ── */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
          {[
            { label: "TOTAL ALERTS", value: total, color: "#00d4ff" },
            { label: "IMMEDIATE SAFETY", value: alerts.filter(a => a.risk_level === "IMMEDIATE_SAFETY").length, color: "#ff2d55" },
            { label: "HIGH CONCERN", value: alerts.filter(a => a.risk_level === "HIGH_CONCERN").length, color: "#ff9500" },
            { label: "PENDING REVIEW", value: pendingCount, color: "#ff2d55" },
          ].map((stat) => (
            <div key={stat.label} style={{
              background: "rgba(0,20,45,0.8)",
              border: `1px solid ${stat.color}33`,
              borderRadius: 8,
              padding: "20px 24px",
              textAlign: "center",
            }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: stat.color, fontFamily: "monospace" }}>
                {stat.value}
              </div>
              <div style={{ fontSize: 10, color: "#4a9eff", letterSpacing: 1.5, marginTop: 4 }}>
                {stat.label}
              </div>
            </div>
          ))}
        </div>

        {/* ── Filter Row ── */}
        <div style={{ display: "flex", gap: 8, marginBottom: 24, alignItems: "center" }}>
          <span style={{ fontSize: 11, color: "#4a9eff", letterSpacing: 1, marginRight: 8 }}>FILTER:</span>
          {[
            { value: "all", label: "ALL" },
            { value: "IMMEDIATE_SAFETY", label: "IMMEDIATE SAFETY" },
            { value: "HIGH_CONCERN", label: "HIGH CONCERN" },
          ].map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              style={{
                background: filter === f.value ? "rgba(0,212,255,0.15)" : "transparent",
                border: `1px solid ${filter === f.value ? "#00d4ff" : "rgba(0,212,255,0.2)"}`,
                color: filter === f.value ? "#00d4ff" : "#4a9eff",
                padding: "6px 16px",
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 11,
                letterSpacing: 1,
                transition: "all 0.2s",
              }}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* ── Alert List ── */}
        {loading ? (
          <div style={{ textAlign: "center", padding: 64, color: "#4a9eff", fontSize: 13 }}>
            LOADING ALERTS...
          </div>
        ) : error ? (
          <div style={{
            background: "rgba(255,45,85,0.1)",
            border: "1px solid rgba(255,45,85,0.3)",
            borderRadius: 8,
            padding: 24,
            color: "#ff2d55",
            fontSize: 13,
          }}>
            {error}
          </div>
        ) : alerts.length === 0 ? (
          <div style={{
            textAlign: "center",
            padding: 64,
            color: "#34c759",
            fontSize: 13,
            letterSpacing: 1,
          }}>
            ✓ NO ALERTS — ALL CLEAR
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {alerts.map((alert) => (
              <div
                key={alert.id}
                style={{
                  background: "rgba(0,20,45,0.8)",
                  border: `1px solid ${getRiskColor(alert.risk_level)}33`,
                  borderLeft: `3px solid ${getRiskColor(alert.risk_level)}`,
                  borderRadius: 8,
                  padding: "20px 24px",
                  transition: "all 0.2s",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
                  {/* Left: info */}
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
                      <span style={{
                        background: `${getRiskColor(alert.risk_level)}22`,
                        border: `1px solid ${getRiskColor(alert.risk_level)}55`,
                        color: getRiskColor(alert.risk_level),
                        padding: "3px 10px",
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 700,
                        letterSpacing: 1.5,
                      }}>
                        {alert.risk_level.replace("_", " ")}
                      </span>
                      <span style={{
                        background: `${getStatusColor(alert.status)}22`,
                        border: `1px solid ${getStatusColor(alert.status)}55`,
                        color: getStatusColor(alert.status),
                        padding: "3px 10px",
                        borderRadius: 4,
                        fontSize: 10,
                        letterSpacing: 1,
                      }}>
                        {alert.status.toUpperCase()}
                      </span>
                      <span style={{ fontSize: 11, color: "#4a9eff", opacity: 0.7 }}>
                        via {alert.notified_channel}
                      </span>
                    </div>

                    <p style={{
                      margin: "0 0 10px",
                      fontSize: 13,
                      color: "#c8e6ff",
                      lineHeight: 1.6,
                      maxWidth: 640,
                    }}>
                      {alert.reason}
                    </p>

                    <div style={{ fontSize: 11, color: "#4a9eff", display: "flex", gap: 20 }}>
                      <span>⏱ {formatTime(alert.triggered_at)}</span>
                      <span style={{ opacity: 0.5 }}>USER {alert.user_id.slice(0, 8).toUpperCase()}</span>
                      {alert.conversation_id && (
                        <span style={{ opacity: 0.5 }}>CONV {alert.conversation_id.slice(0, 8).toUpperCase()}</span>
                      )}
                    </div>
                  </div>

                  {/* Right: action buttons */}
                  {(alert.status === "pending" || alert.status === "notified") && (
                    <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                      <button
                        onClick={() => updateStatus(alert.id, "acknowledged")}
                        disabled={updatingId === alert.id}
                        style={{
                          background: "rgba(0,212,255,0.1)",
                          border: "1px solid rgba(0,212,255,0.3)",
                          color: "#00d4ff",
                          padding: "8px 16px",
                          borderRadius: 4,
                          cursor: "pointer",
                          fontSize: 11,
                          letterSpacing: 1,
                          opacity: updatingId === alert.id ? 0.5 : 1,
                        }}
                      >
                        ACKNOWLEDGE
                      </button>
                      <button
                        onClick={() => updateStatus(alert.id, "resolved")}
                        disabled={updatingId === alert.id}
                        style={{
                          background: "rgba(52,199,89,0.1)",
                          border: "1px solid rgba(52,199,89,0.3)",
                          color: "#34c759",
                          padding: "8px 16px",
                          borderRadius: 4,
                          cursor: "pointer",
                          fontSize: 11,
                          letterSpacing: 1,
                          opacity: updatingId === alert.id ? 0.5 : 1,
                        }}
                      >
                        RESOLVE
                      </button>
                    </div>
                  )}
                  {alert.status === "resolved" && (
                    <span style={{ color: "#34c759", fontSize: 11, letterSpacing: 1 }}>✓ RESOLVED</span>
                  )}
                  {alert.status === "acknowledged" && (
                    <button
                      onClick={() => updateStatus(alert.id, "resolved")}
                      disabled={updatingId === alert.id}
                      style={{
                        background: "rgba(52,199,89,0.1)",
                        border: "1px solid rgba(52,199,89,0.3)",
                        color: "#34c759",
                        padding: "8px 16px",
                        borderRadius: 4,
                        cursor: "pointer",
                        fontSize: 11,
                        letterSpacing: 1,
                      }}
                    >
                      MARK RESOLVED
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}
