"use client";

import { useState } from "react";

interface TrendPoint {
  timestamp: string;
  social: number;
  family: number;
  academic: number;
  digital: number;
  lifestyle: number;
  emotions: string[];
}

interface TrendHistoryProps {
  trends: TrendPoint[];
}

const LINE_CONFIG: Record<string, { stroke: string; label: string; icon: string; fillGradient: string }> = {
  social: {
    stroke: "#38bdf8",
    label: "Social",
    icon: "SOC",
    fillGradient: "rgba(56, 189, 248, 0.15)",
  },
  family: {
    stroke: "#c084fc",
    label: "Family",
    icon: "FAM",
    fillGradient: "rgba(192, 132, 252, 0.15)",
  },
  academic: {
    stroke: "#fb7185",
    label: "Academic",
    icon: "ACG",
    fillGradient: "rgba(251, 113, 133, 0.15)",
  },
  digital: {
    label: "Digital",
    stroke: "#fbbf24",
    icon: "DIG",
    fillGradient: "rgba(251, 191, 36, 0.15)",
  },
  lifestyle: {
    stroke: "#34d399",
    label: "Lifestyle",
    icon: "LST",
    fillGradient: "rgba(52, 211, 153, 0.15)",
  },
};

export default function TrendHistory({ trends }: TrendHistoryProps) {
  const [activeDimension, setActiveDimension] = useState<string | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<{ idx: number; key: string } | null>(null);

  if (!trends || trends.length === 0) {
    return (
      <div className="glass-panel p-8 text-center text-slate-400 text-sm">
        Start speaking with Aura to build your longitudinal wellbeing trajectory!
      </div>
    );
  }

  // Canvas Dimensions
  const width = 720;
  const height = 260;
  const padding = { top: 25, right: 35, bottom: 40, left: 45 };

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const minVal = 20;
  const maxVal = 100;

  const getX = (index: number) => {
    if (trends.length <= 1) return padding.left + plotWidth / 2;
    return padding.left + (index / (trends.length - 1)) * plotWidth;
  };

  const getY = (val: number) => {
    const clamped = Math.max(minVal, Math.min(maxVal, val));
    return padding.top + plotHeight - ((clamped - minVal) / (maxVal - minVal)) * plotHeight;
  };

  // Helper for smooth bezier curve SVG path
  const generateSmoothPath = (key: string) => {
    const points = trends.map((pt, idx) => ({
      x: getX(idx),
      y: getY(pt[key as keyof TrendPoint] as number),
    }));

    if (points.length === 0) return "";
    if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;

    let path = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i];
      const p1 = points[i + 1];
      const cpX = (p0.x + p1.x) / 2;
      path += ` C ${cpX} ${p0.y}, ${cpX} ${p1.y}, ${p1.x} ${p1.y}`;
    }
    return path;
  };

  const generateAreaPath = (key: string) => {
    const linePath = generateSmoothPath(key);
    if (!linePath) return "";
    const firstX = getX(0);
    const lastX = getX(trends.length - 1);
    const bottomY = padding.top + plotHeight;
    return `${linePath} L ${lastX} ${bottomY} L ${firstX} ${bottomY} Z`;
  };

  return (
    <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
      {/* Header & Filter Pills */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-white text-base">Wellbeing Trajectory</h3>
          </div>
          <p className="text-xs text-slate-400">
            Multi-session timeline monitoring shifts across all 5 life dimensions
          </p>
        </div>

        {/* Legend Dimension Filter */}
        <div className="flex flex-wrap items-center gap-1.5">
          {Object.entries(LINE_CONFIG).map(([key, cfg]) => {
            const isDimActive = activeDimension === null || activeDimension === key;
            return (
              <button
                key={key}
                onClick={() =>
                  setActiveDimension(activeDimension === key ? null : key)
                }
                className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border transition-all ${
                  isDimActive
                    ? "bg-white/10 text-white border-white/20 shadow-sm"
                    : "opacity-35 text-slate-400 border-transparent hover:opacity-60"
                }`}
              >
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: cfg.stroke }}
                ></span>
                <span>{cfg.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto min-w-[520px]"
        >
          <defs>
            {Object.entries(LINE_CONFIG).map(([key, cfg]) => (
              <linearGradient
                key={`grad-${key}`}
                id={`grad-${key}`}
                x1="0%"
                y1="0%"
                x2="0%"
                y2="100%"
              >
                <stop offset="0%" stopColor={cfg.stroke} stopOpacity="0.25" />
                <stop offset="100%" stopColor={cfg.stroke} stopOpacity="0.0" />
              </linearGradient>
            ))}
          </defs>

          {/* Horizontal Grid lines */}
          {[40, 60, 80, 100].map((score) => {
            const y = getY(score);
            return (
              <g key={score}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke="rgba(255, 255, 255, 0.05)"
                  strokeDasharray="4 4"
                />
                <text
                  x={padding.left - 10}
                  y={y + 3}
                  fill="#64748b"
                  fontSize="10"
                  textAnchor="end"
                  fontFamily="sans-serif"
                >
                  {score}
                </text>
              </g>
            );
          })}

          {/* Area Gradients & Smooth Lines */}
          {Object.entries(LINE_CONFIG).map(([key, cfg]) => {
            const isVisible = activeDimension === null || activeDimension === key;
            if (!isVisible) return null;

            return (
              <g key={key}>
                {/* Area Gradient Fill */}
                <path
                  d={generateAreaPath(key)}
                  fill={`url(#grad-${key})`}
                  className="transition-opacity duration-300"
                />

                {/* Line */}
                <path
                  d={generateSmoothPath(key)}
                  fill="none"
                  stroke={cfg.stroke}
                  strokeWidth={activeDimension === key ? 3.5 : 2.2}
                  strokeLinecap="round"
                  className="transition-all duration-300"
                  style={{
                    filter:
                      activeDimension === key
                        ? `drop-shadow(0 0 8px ${cfg.stroke}80)`
                        : "none",
                  }}
                />

                {/* Point Dots */}
                {trends.map((pt, idx) => {
                  const cx = getX(idx);
                  const cy = getY(pt[key as keyof TrendPoint] as number);
                  const isHovered =
                    hoveredPoint?.idx === idx && hoveredPoint?.key === key;

                  return (
                    <circle
                      key={idx}
                      cx={cx}
                      cy={cy}
                      r={isHovered ? 5.5 : activeDimension === key ? 4 : 3}
                      fill={cfg.stroke}
                      stroke="#070913"
                      strokeWidth="2"
                      className="cursor-pointer transition-all"
                      onMouseEnter={() => setHoveredPoint({ idx, key })}
                      onMouseLeave={() => setHoveredPoint(null)}
                    />
                  );
                })}
              </g>
            );
          })}

          {/* X Axis Timeline Labels */}
          {trends.map((pt, idx) => (
            <text
              key={idx}
              x={getX(idx)}
              y={height - 10}
              fill="#94a3b8"
              fontSize="10"
              fontWeight="500"
              textAnchor="middle"
            >
              {pt.timestamp}
            </text>
          ))}
        </svg>
      </div>

      <div className="mt-2 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-slate-400">
        <span>Tap dimension badges to highlight individual trajectory</span>
        <span>Target Balance: 70+</span>
      </div>
    </div>
  );
}
