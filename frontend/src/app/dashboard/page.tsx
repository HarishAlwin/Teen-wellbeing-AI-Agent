"use client";

import { useEffect, useState } from "react";
import { getDashboardData, DashboardData } from "@/lib/api";
import WellbeingMeters from "@/components/Dashboard/WellbeingMeters";
import TrendHistory from "@/components/Dashboard/TrendHistory";
import PatternCards from "@/components/Dashboard/PatternCards";
import InterventionList from "@/components/Dashboard/InterventionList";
import GraphVisualizer from "@/components/WellbeingGraph/GraphVisualizer";
import ResponsibleAINotice from "@/components/Dashboard/ResponsibleAINotice";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const userId = localStorage.getItem("teen_user_id") || "demo-user";
      const res = await getDashboardData(userId);
      setData(res);
    } catch (err) {
      console.error("Error loading dashboard data:", err);
      // Realistic demo dataset fallback
      setData({
        user: {
          id: "demo-alex",
          display_name: "Alex",
          country_code: "IN",
          age_group: "teen",
          session_count: 5,
        },
        dimensions: {
          social: { current: 65, baseline: 72, delta: -7 },
          family: { current: 70, baseline: 70, delta: 0 },
          academic: { current: 58, baseline: 68, delta: -10 },
          digital: { current: 52, baseline: 65, delta: -13 },
          lifestyle: { current: 56, baseline: 70, delta: -14 },
        },
        trends: [
          { timestamp: "T-4", social: 75, family: 72, academic: 70, digital: 68, lifestyle: 74, emotions: ["calm"] },
          { timestamp: "T-3", social: 72, family: 70, academic: 65, digital: 62, lifestyle: 68, emotions: ["hopeful"] },
          { timestamp: "T-2", social: 68, family: 70, academic: 60, digital: 55, lifestyle: 60, emotions: ["tired"] },
          { timestamp: "T-1", social: 65, family: 70, academic: 58, digital: 52, lifestyle: 56, emotions: ["anxious", "exhausted"] },
        ],
        patterns: [
          {
            id: "pat-1",
            title: "ACADEMIC_LOAD -> MIDNIGHT_SCREEN -> SLEEP_LOSS",
            description: "High study workload correlates with late-night phone browsing, disrupting sleep and compounding daytime fatigue.",
            category: "cross_dimensional",
            severity: "high",
            dimensions_involved: ["academic", "digital", "lifestyle"],
            evidence_snippets: ["Study workload causing anxiety", "Compulsive late-night screen scrolling", "Sleep disruption and morning exhaustion"],
            occurrence_count: 3,
          },
          {
            id: "pat-2",
            title: "FATIGUE -> SOCIAL_ISOLATION",
            description: "Physical tiredness and low energy levels appear linked to pulling away from friends and group interactions.",
            category: "cross_dimensional",
            severity: "medium",
            dimensions_involved: ["lifestyle", "social"],
            evidence_snippets: ["Low energy in morning routines", "Decreased social interaction during lunch"],
            occurrence_count: 2,
          },
        ],
        graph: {
          nodes: [
            { id: "academic_pressure", type: "wellbeingNode", position: { x: 50, y: 80 }, data: { label: "Academic Pressure", category: "academic", val_score: 75, colorStyle: { bg: "rgba(251, 113, 133, 0.15)", border: "#fb7185", text: "#fca5a5" } } },
            { id: "screen_time", type: "wellbeingNode", position: { x: 300, y: 80 }, data: { label: "Late Screen Time", category: "digital", val_score: 70, colorStyle: { bg: "rgba(251, 191, 36, 0.15)", border: "#fbbf24", text: "#fde68a" } } },
            { id: "sleep_quality", type: "wellbeingNode", position: { x: 550, y: 80 }, data: { label: "Sleep Quality", category: "lifestyle", val_score: 45, colorStyle: { bg: "rgba(52, 211, 153, 0.15)", border: "#34d399", text: "#a7f3d0" } } },
            { id: "daily_energy", type: "wellbeingNode", position: { x: 550, y: 260 }, data: { label: "Daily Energy", category: "lifestyle", val_score: 48, colorStyle: { bg: "rgba(52, 211, 153, 0.15)", border: "#34d399", text: "#a7f3d0" } } },
            { id: "emotional_state", type: "wellbeingNode", position: { x: 300, y: 260 }, data: { label: "Emotional Balance", category: "emotion", val_score: 55, colorStyle: { bg: "rgba(192, 132, 252, 0.15)", border: "#c084fc", text: "#e9d5ff" } } },
            { id: "social_connection", type: "wellbeingNode", position: { x: 50, y: 260 }, data: { label: "Social Connections", category: "social", val_score: 62, colorStyle: { bg: "rgba(56, 189, 248, 0.15)", border: "#38bdf8", text: "#bae6fd" } } },
          ],
          edges: [
            { id: "e1", source: "academic_pressure", target: "screen_time", animated: true, label: "triggers", style: { stroke: "#fb7185", strokeWidth: 3.5, opacity: 0.9 }, data: { weight: 0.85 } },
            { id: "e2", source: "screen_time", target: "sleep_quality", animated: true, label: "disrupts", style: { stroke: "#fb7185", strokeWidth: 3.5, opacity: 0.9 }, data: { weight: 0.9 } },
            { id: "e3", source: "sleep_quality", target: "daily_energy", animated: true, label: "depletes", style: { stroke: "#fb7185", strokeWidth: 3, opacity: 0.85 }, data: { weight: 0.88 } },
            { id: "e4", source: "daily_energy", target: "emotional_state", animated: false, label: "strains", style: { stroke: "#818cf8", strokeWidth: 2, opacity: 0.75 }, data: { weight: 0.75 } },
            { id: "e5", source: "emotional_state", target: "social_connection", animated: false, label: "leads to withdrawal", style: { stroke: "#818cf8", strokeWidth: 2, opacity: 0.7 }, data: { weight: 0.7 } },
          ],
        },
        interventions: [
          {
            id: "int-1",
            type: "routine_suggestion",
            title: "BUFFER_ZONE_20MIN",
            content: "Charge your phone across the room 25 minutes before bedtime to prevent midnight doomscrolling.",
            risk_level: "CONCERNING",
            date: "T-1",
          },
          {
            id: "int-2",
            type: "coping_strategy",
            title: "POMODORO_MICRO_SPRINT",
            content: "Study in 25-minute sprints followed by 5 minutes of mindful stretching and water hydration.",
            risk_level: "NORMAL",
            date: "T-3",
          },
        ],
        safety: {
          risk_level: "CONCERNING",
          guidance: {
            headline: "Elevated Variance Detected",
            message: "Life dimensions indicate compounded fatigue.",
            action: "Engage trusted mentor",
            show_helplines: false,
            urgency: "medium",
          },
          helplines: {},
        },
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  if (loading && !data) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-24 text-center space-y-4 font-mono-hud">
        <div className="w-10 h-10 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
        <p className="text-xs text-cyan-300 tracking-widest">&gt; SYNCHRONIZING TELEMETRY STREAM...</p>
      </div>
    );
  }

  return (
    <div className="max-w-[1540px] mx-auto px-3 sm:px-6 py-4 space-y-6 font-mono-hud">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-cyan-500/20">
        <div>
          <div className="flex items-center gap-3">
            <span className="w-2.5 h-2.5 bg-cyan-400 rounded-sm shadow-[0_0_8px_#00f0ff] animate-pulse"></span>
            <h1 className="text-xl sm:text-2xl font-extrabold text-cyan-300 tracking-widest">
              TELEMETRY & TOPOLOGY INTELLIGENCE
            </h1>
            <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-bold border border-emerald-500/20">
              STREAM: ACTIVE
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-sans">
            Longitudinal biometrics, causal strain network mapping, and cross-category pattern recognition
          </p>
        </div>

        <button
          onClick={fetchDashboard}
          className="px-3.5 py-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/30 text-cyan-300 text-xs font-bold flex items-center gap-1.5 self-start sm:self-auto transition-all shadow-[0_0_10px_rgba(0,240,255,0.15)] cursor-pointer"
        >
          <span>🔄</span>
          <span>RE-SYNC</span>
        </button>
      </div>

      {/* 5 Core Life Dimension Meters */}
      {data && <WellbeingMeters dimensions={data.dimensions as any} />}

      {/* Middle Grid: Trend History & Personal Wellbeing Graph */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-6">
          {data && <TrendHistory trends={data.trends} />}
        </div>
        <div className="lg:col-span-6">
          {data && <GraphVisualizer graph={data.graph} />}
        </div>
      </div>

      {/* Patterns & Interventions Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-7">
          {data && <PatternCards patterns={data.patterns} />}
        </div>
        <div className="lg:col-span-5">
          {data && <InterventionList interventions={data.interventions} />}
        </div>
      </div>

      {/* Responsible AI Principles Notice */}
      <ResponsibleAINotice />
    </div>
  );
}
