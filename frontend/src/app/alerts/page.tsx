"use client";

import { useState, useEffect, useCallback } from "react";
import { getAlerts, acknowledgeAlert, AlertItem } from "@/lib/api";

function getRiskColor(level: string) {
  if (level === "IMMEDIATE_SAFETY") return "#ff2d55";
  if (level === "HIGH_CONCERN") return "#ff9500";
  if (level === "CONCERNING") return "#ffd60a";
  return "#00d4ff";
}

function getStatusColor(status: string) {
  if (status === "acknowledged" || status === "resolved") return "#34c759";
  if (status === "notified") return "#00d4ff";
  if (status === "failed") return "#ff2d55";
  return "#ff9500"; // triggered / pending
}

function formatTime(iso: string) {
  if (!iso) return "Unknown";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return iso;
  }
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
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
      const data = await getAlerts();
      setAlerts(data.alerts || []);
      setError(null);
    } catch (e: unknown) {
      setError(`Failed to load alerts: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 15000); // auto-refresh every 15s
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const handleAcknowledge = async (alertId: string) => {
    setUpdatingId(alertId);
    try {
      await acknowledgeAlert(alertId);
      await fetchAlerts();
    } catch (e: unknown) {
      console.error("Acknowledge failed:", e);
    } finally {
      setUpdatingId(null);
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (filter === "all") return true;
    return a.risk_level === filter;
  });

  const pendingCount = alerts.filter((a) => a.status === "triggered" || a.status === "notified").length;
  const immediateCount = alerts.filter((a) => a.risk_level === "IMMEDIATE_SAFETY").length;
  const calleCallsCount = alerts.filter((a) => a.calle_call_id || a.notified_channel === "calle").length;

  return (
    <div style={{ minHeight: "100vh", background: "#000d1a", color: "#e0f4ff", fontFamily: "'Inter', sans-serif" }}>
      {/* ── Top Bar ── */}
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
            AURA COUNSELOR & SAFETY ALERTS
          </span>
          <span style={{ color: "#4a9eff", fontSize: 11, opacity: 0.7 }}>
            // AUDIT & ESCALATION LOGS
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 24, fontSize: 11, color: "#4a9eff" }}>
          {immediateCount > 0 && (
            <span style={{ color: "#ff2d55", fontWeight: 700, letterSpacing: 1 }}>
              [!] {immediateCount} IMMEDIATE SAFETY
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
            { label: "TOTAL ESCALATIONS", value: alerts.length, color: "#00d4ff" },
            { label: "IMMEDIATE SAFETY", value: immediateCount, color: "#ff2d55" },
            { label: "HIGH CONCERN", value: alerts.filter(a => a.risk_level === "HIGH_CONCERN").length, color: "#ff9500" },
            { label: "CALL-E ESCALATIONS", value: calleCallsCount, color: "#a855f7" },
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
        {loading && alerts.length === 0 ? (
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
        ) : filteredAlerts.length === 0 ? (
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
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {filteredAlerts.map((alert) => (
              <div
                key={alert.id}
                style={{
                  background: "rgba(0,20,45,0.8)",
                  border: `1px solid ${getRiskColor(alert.risk_level)}33`,
                  borderLeft: `4px solid ${getRiskColor(alert.risk_level)}`,
                  borderRadius: 8,
                  padding: "20px 24px",
                  transition: "all 0.2s",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
                  {/* Left info */}
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
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
                      <span style={{
                        background: alert.notified_channel === "calle" ? "rgba(168,85,247,0.2)" : "rgba(74,158,255,0.1)",
                        border: alert.notified_channel === "calle" ? "1px solid rgba(168,85,247,0.4)" : "1px solid rgba(74,158,255,0.2)",
                        color: alert.notified_channel === "calle" ? "#c084fc" : "#4a9eff",
                        padding: "3px 10px",
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 600,
                      }}>
                        {alert.notified_channel === "calle" ? "📞 CALL-E AI Call" : `via ${alert.notified_channel}`}
                      </span>
                    </div>

                    <p style={{
                      margin: "0 0 12px",
                      fontSize: 13,
                      color: "#c8e6ff",
                      lineHeight: 1.6,
                      maxWidth: 700,
                    }}>
                      {alert.reasons}
                    </p>

                    {/* CALL-E Structured Result Box */}
                    {alert.calle_structured_result && (
                      <div style={{
                        background: "rgba(168,85,247,0.08)",
                        border: "1px solid rgba(168,85,247,0.3)",
                        borderRadius: 6,
                        padding: "12px 16px",
                        marginBottom: 12,
                        fontSize: 12,
                      }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, color: "#c084fc", fontWeight: 700 }}>
                          <span>🎙️ CALL-E Agent Structured Briefing</span>
                          {alert.calle_task_completed && (
                            <span style={{ background: "rgba(52,199,89,0.2)", color: "#34c759", padding: "2px 6px", borderRadius: 4, fontSize: 10 }}>
                              ✓ Task Completed
                            </span>
                          )}
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 16px", color: "#e0f4ff" }}>
                          <span style={{ color: "#a855f7" }}>Counselor Reached:</span>
                          <span style={{ fontWeight: 600 }}>{alert.calle_structured_result.counselor_reached || "unknown"}</span>
                          <span style={{ color: "#a855f7" }}>Acknowledged:</span>
                          <span style={{ fontWeight: 600 }}>{alert.calle_structured_result.acknowledged || "unknown"}</span>
                          <span style={{ color: "#a855f7" }}>Recommended Next Step:</span>
                          <span style={{ color: "#38bdf8", fontWeight: 700 }}>{alert.calle_structured_result.recommended_next_step || "unknown"}</span>
                          {alert.calle_structured_result.notes && (
                            <>
                              <span style={{ color: "#a855f7" }}>Notes:</span>
                              <span style={{ color: "#cbd5e1", fontStyle: "italic" }}>{alert.calle_structured_result.notes}</span>
                            </>
                          )}
                        </div>
                      </div>
                    )}

                    <div style={{ fontSize: 11, color: "#4a9eff", display: "flex", gap: 20, flexWrap: "wrap" }}>
                      <span>⏱ {formatTime(alert.triggered_at)}</span>
                      <span style={{ opacity: 0.6 }}>USER: {alert.user_display_name || alert.user_id.slice(0, 8)}</span>
                      {alert.calle_call_id && (
                        <span style={{ color: "#c084fc" }}>CALL ID: {alert.calle_call_id}</span>
                      )}
                      {alert.delivery_error && (
                        <span style={{ color: "#ff2d55" }}>⚠️ {alert.delivery_error}</span>
                      )}
                    </div>
                  </div>

                  {/* Right: action buttons */}
                  {alert.status !== "acknowledged" && alert.status !== "resolved" ? (
                    <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                      <button
                        onClick={() => handleAcknowledge(alert.id)}
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
                    </div>
                  ) : (
                    <span style={{ color: "#34c759", fontSize: 11, letterSpacing: 1 }}>✓ ACKNOWLEDGED</span>
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

