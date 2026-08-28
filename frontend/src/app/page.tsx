"use client";

import { useEffect, useState } from "react";
import VoiceInterface from "@/components/VoiceChat/VoiceInterface";
import { getDashboardData, DashboardData, ChatResponse } from "@/lib/api";
import Link from "next/link";

export default function HomePage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);

  const fetchMetrics = async () => {
    try {
      const uid = localStorage.getItem("teen_user_id") || "demo-alex";
      const res = await getDashboardData(uid);
      setDashboard(res);
    } catch {
      // Fallback telemetry defaults
      setDashboard({
        user: { id: "demo-alex", display_name: "Alex", country_code: "IN", age_group: "teen", session_count: 6 },
        dimensions: {
          social: { current: 68, baseline: 72, delta: -4 },
          family: { current: 74, baseline: 70, delta: +4 },
          academic: { current: 58, baseline: 68, delta: -10 },
          digital: { current: 52, baseline: 65, delta: -13 },
          lifestyle: { current: 56, baseline: 70, delta: -14 },
        },
        trends: [],
        patterns: [
          {
            id: "pat-1",
            title: "ACADEMIC_PRESSURE -> SLEEP_DEBT",
            description: "High study load compounds with late-night phone browsing, disrupting sleep and daytime energy.",
            category: "cross_dimensional",
            severity: "high",
            dimensions_involved: ["academic", "digital", "lifestyle"],
            evidence_snippets: ["Exam stress surge", "Doomscrolling past 2 AM"],
            occurrence_count: 3,
          },
          {
            id: "pat-2",
            title: "FATIGUE -> PEER_WITHDRAWAL",
            description: "Sleep deprivation correlates directly with lunchtime isolation and social battery drain.",
            category: "cross_dimensional",
            severity: "medium",
            dimensions_involved: ["lifestyle", "social"],
            evidence_snippets: ["Low morning stamina"],
            occurrence_count: 2,
          },
        ],
        graph: { nodes: [], edges: [] },
        interventions: [
          {
            id: "int-1",
            type: "routine_suggestion",
            title: "BUFFER_ZONE_20MIN",
            content: "Place phone on charge across the room 20 minutes before sleeping.",
            risk_level: "CONCERNING",
            date: "RECENT",
          },
          {
            id: "int-2",
            type: "coping_strategy",
            title: "POMODORO_MICRO_SPRINT",
            content: "25-min focused study sprints with 5-min mindful breathing breaks.",
            risk_level: "NORMAL",
            date: "3D AGO",
          },
        ],
        safety: {
          risk_level: "CONCERNING",
          guidance: { headline: "Active Monitoring", message: "Normal variance", action: "Engage mentor", show_helplines: false, urgency: "low" },
          helplines: {},
        },
      });
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const handleVoiceUpdate = (res: ChatResponse) => {
    if (res.dimension_scores) {
      setDashboard((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          dimensions: {
            social: { current: res.dimension_scores.social, baseline: 70, delta: res.score_deltas?.social || 0 },
            family: { current: res.dimension_scores.family, baseline: 70, delta: res.score_deltas?.family || 0 },
            academic: { current: res.dimension_scores.academic, baseline: 70, delta: res.score_deltas?.academic || 0 },
            digital: { current: res.dimension_scores.digital, baseline: 70, delta: res.score_deltas?.digital || 0 },
            lifestyle: { current: res.dimension_scores.lifestyle, baseline: 70, delta: res.score_deltas?.lifestyle || 0 },
          },
          patterns: res.active_patterns ? (res.active_patterns as any) : prev.patterns,
        };
      });
    }
  };

  const dimConfig = [
    { key: "social", label: "SOCIAL_LINK", icon: "👥", color: "#38bdf8" },
    { key: "family", label: "FAMILY_ENV", icon: "🏡", color: "#c084fc" },
    { key: "academic", label: "ACADEMIC_LOAD", icon: "📚", color: "#fb7185" },
    { key: "digital", label: "DIGITAL_HABIT", icon: "📱", color: "#fbbf24" },
    { key: "lifestyle", label: "LIFESTYLE_REST", icon: "🌙", color: "#34d399" },
  ];

  return (
    <div className="max-w-[1540px] mx-auto px-3 sm:px-6 py-3 space-y-4 font-mono-hud">
      {/* Top Telemetry Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-cyan-500/20 pb-2.5 text-xs text-slate-400">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-cyan-400 rounded-sm shadow-[0_0_8px_#00f0ff] animate-pulse"></span>
            <span className="text-cyan-300 font-extrabold tracking-widest text-sm sm:text-base">
              AURA // WELLBEING COMMAND HUD
            </span>
          </div>
          <span className="hidden md:inline text-slate-600">|</span>
          <span className="hidden md:inline text-[11px] text-slate-400">
            AUTONOMOUS 5-DIMENSION NEURAL REASONING
          </span>
        </div>

        <div className="flex items-center gap-3 text-[11px]">
          <span className="px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/30 text-cyan-300">
            DIAGNOSTICS: NOMINAL
          </span>
          <button
            onClick={fetchMetrics}
            className="px-2.5 py-0.5 rounded bg-white/5 hover:bg-cyan-500/20 border border-white/10 text-slate-300 hover:text-cyan-300 transition-all cursor-pointer"
          >
            REFRESH 🔄
          </button>
        </div>
      </div>

      {/* Main 3-Column Jarvis HUD Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Left Column: 5-Dimension Life Telemetry Matrix */}
        <div className="lg:col-span-3 space-y-3">
          <div className="hud-panel p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2 text-[11px]">
              <span className="text-cyan-300 font-bold tracking-wider">[01] BIOMETRIC TELEMETRY</span>
              <span className="text-slate-500">LIVE GAUGES</span>
            </div>

            <div className="space-y-3.5 pt-1">
              {dimConfig.map((cfg) => {
                const dimData = dashboard?.dimensions?.[cfg.key] || { current: 70, baseline: 70, delta: 0 };
                const isLow = dimData.current < 55;
                const deltaStr = dimData.delta > 0 ? `+${dimData.delta}` : `${dimData.delta}`;

                return (
                  <div key={cfg.key} className="space-y-1.5 p-2 rounded-lg bg-slate-950/60 border border-white/5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="flex items-center gap-1.5 text-slate-200 font-bold">
                        <span>{cfg.icon}</span>
                        <span>{cfg.label}</span>
                      </span>
                      <span className={`text-[10px] font-bold ${isLow ? "text-rose-400" : "text-emerald-400"}`}>
                        {dimData.current.toFixed(0)}/100
                      </span>
                    </div>

                    {/* Gauge Track */}
                    <div className="w-full h-1.5 rounded-full bg-slate-900 border border-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{
                          width: `${Math.min(100, Math.max(10, dimData.current))}%`,
                          backgroundColor: cfg.color,
                          boxShadow: `0 0 8px ${cfg.color}`,
                        }}
                      ></div>
                    </div>

                    <div className="flex items-center justify-between text-[9px] text-slate-500">
                      <span>BASE: {dimData.baseline}</span>
                      <span className={dimData.delta < 0 ? "text-rose-400" : "text-emerald-400"}>
                        VAR: {deltaStr}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Quick HUD Navigation Teaser */}
          <div className="hud-panel p-4 space-y-2 text-xs">
            <span className="text-[10px] text-cyan-400 font-bold uppercase tracking-wider block">
              [DEEP TOPOLOGY LINK]
            </span>
            <p className="text-[11px] font-sans text-slate-400">
              Explore multi-session node graphs and predictive timeline trajectories.
            </p>
            <Link
              href="/dashboard"
              className="w-full py-2 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-400/40 text-cyan-300 text-[11px] font-bold flex items-center justify-center gap-1.5 transition-all shadow-[0_0_10px_rgba(0,240,255,0.15)]"
            >
              <span>OPEN TELEMETRY HUB</span>
              <span>→</span>
            </Link>
          </div>
        </div>

        {/* Center Column: The Jarvis Holographic Voice Core */}
        <div className="lg:col-span-6">
          <VoiceInterface onDataUpdate={handleVoiceUpdate} />
        </div>

        {/* Right Column: Neural Pattern Engine & Protocol Stream */}
        <div className="lg:col-span-3 space-y-3">
          {/* Active Cross-Category Stress Loops */}
          <div className="hud-panel p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2 text-[11px]">
              <span className="text-cyan-300 font-bold tracking-wider">[02] NEURAL PATTERNS</span>
              <span className="text-rose-400 font-bold animate-pulse">
                {dashboard?.patterns?.length || 0} LOOPS
              </span>
            </div>

            <div className="space-y-2.5 pt-1">
              {dashboard?.patterns?.map((pat) => (
                <div
                  key={pat.id}
                  className="p-3 rounded-lg bg-slate-950/80 border border-rose-500/30 space-y-1.5"
                >
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="font-bold text-rose-300 truncate max-w-[170px]">{pat.title}</span>
                    <span className="px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[9px] font-bold uppercase">
                      {pat.severity}
                    </span>
                  </div>
                  <p className="text-[11px] font-sans text-slate-300 leading-tight">
                    {pat.description}
                  </p>
                  {pat.dimensions_involved && (
                    <div className="text-[9px] text-cyan-400 font-bold pt-0.5">
                      LINK: {pat.dimensions_involved.join(" → ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Active Guidance Protocols */}
          <div className="hud-panel p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2 text-[11px]">
              <span className="text-cyan-300 font-bold tracking-wider">[03] MITIGATION PROTOCOLS</span>
              <span className="text-emerald-400 font-bold">READY</span>
            </div>

            <div className="space-y-2 pt-1">
              {dashboard?.interventions?.map((item) => (
                <div
                  key={item.id}
                  className="p-2.5 rounded-lg bg-slate-950/60 border border-cyan-500/20 space-y-1 text-xs"
                >
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="font-bold text-cyan-300">🛡️ {item.title}</span>
                    <span className="text-slate-500">{item.date}</span>
                  </div>
                  <p className="font-sans text-[11px] text-slate-300 leading-snug">
                    {item.content}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Emergency Safety Protocol Button */}
          <Link
            href="/helplines"
            className="w-full p-3 rounded-xl bg-rose-950/60 hover:bg-rose-900/80 border border-rose-500/40 text-rose-200 text-xs font-bold flex items-center justify-between transition-all shadow-[0_0_15px_rgba(244,63,94,0.2)]"
          >
            <div className="flex items-center gap-2">
              <span className="text-base animate-pulse">🚨</span>
              <span>24/7 CRISIS HELPLINE PROTOCOLS</span>
            </div>
            <span>→</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
