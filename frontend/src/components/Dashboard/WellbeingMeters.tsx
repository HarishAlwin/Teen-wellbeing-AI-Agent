"use client";

interface DimensionData {
  current: number;
  baseline: number;
  delta: number;
}

interface WellbeingMetersProps {
  dimensions: {
    social: DimensionData;
    family: DimensionData;
    academic: DimensionData;
    digital: DimensionData;
    lifestyle: DimensionData;
  };
}

const DIMENSION_CONFIG = {
  social: {
    label: "Social",
    subtitle: "Friends & Belonging",
    icon: "👥",
    color: "from-sky-400 to-blue-600",
    glowColor: "rgba(56, 189, 248, 0.4)",
    border: "border-sky-500/30",
    bg: "from-sky-500/10 to-transparent",
    accent: "#38bdf8",
  },
  family: {
    label: "Family",
    subtitle: "Home Peace & Boundaries",
    icon: "🏡",
    color: "from-purple-400 to-pink-600",
    glowColor: "rgba(192, 132, 252, 0.4)",
    border: "border-purple-500/30",
    bg: "from-purple-500/10 to-transparent",
    accent: "#c084fc",
  },
  academic: {
    label: "Academic",
    subtitle: "Exams, Workload & Goals",
    icon: "📚",
    color: "from-rose-400 to-orange-500",
    glowColor: "rgba(251, 113, 133, 0.4)",
    border: "border-rose-500/30",
    bg: "from-rose-500/10 to-transparent",
    accent: "#fb7185",
  },
  digital: {
    label: "Digital",
    subtitle: "Screen Time & Feeds",
    icon: "📱",
    color: "from-amber-400 to-yellow-500",
    glowColor: "rgba(251, 191, 36, 0.4)",
    border: "border-amber-500/30",
    bg: "from-amber-500/10 to-transparent",
    accent: "#fbbf24",
  },
  lifestyle: {
    label: "Lifestyle",
    subtitle: "Sleep, Meals & Energy",
    icon: "🌙",
    color: "from-emerald-400 to-teal-500",
    glowColor: "rgba(52, 211, 153, 0.4)",
    border: "border-emerald-500/30",
    bg: "from-emerald-500/10 to-transparent",
    accent: "#34d399",
  },
};

export default function WellbeingMeters({ dimensions }: WellbeingMetersProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {Object.entries(DIMENSION_CONFIG).map(([key, cfg]) => {
        const data = dimensions[key as keyof typeof dimensions] || {
          current: 70,
          baseline: 70,
          delta: 0,
        };
        const isLow = data.current < 55;
        const isUp = data.delta > 0;
        const deltaFormatted = data.delta > 0 ? `+${data.delta}` : `${data.delta}`;

        return (
          <div
            key={key}
            className={`glass-panel p-5 rounded-2xl border ${cfg.border} bg-gradient-to-b ${cfg.bg} flex flex-col justify-between hover:translate-y-[-2px] transition-all`}
          >
            {/* Header */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center text-xl shadow-md"
                  style={{
                    backgroundColor: `${cfg.accent}15`,
                    border: `1px solid ${cfg.accent}30`,
                  }}
                >
                  {cfg.icon}
                </div>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    isUp
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                      : data.delta < 0
                      ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                      : "bg-slate-500/20 text-slate-300 border border-slate-500/30"
                  }`}
                >
                  {data.delta === 0 ? "At Baseline" : `${deltaFormatted} shift`}
                </span>
              </div>

              {/* Title & Subtitle */}
              <h4 className="font-bold text-white text-base tracking-tight">{cfg.label}</h4>
              <p className="text-[11px] text-slate-400 line-clamp-1 mb-4">{cfg.subtitle}</p>
            </div>

            {/* Metrics & Progress Bar */}
            <div className="space-y-2">
              <div className="flex items-baseline justify-between">
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-extrabold text-white">
                    {data.current.toFixed(0)}
                  </span>
                  <span className="text-xs text-slate-500">/100</span>
                </div>
                <span className="text-[11px] text-slate-400">
                  Base: <strong className="text-slate-300">{data.baseline.toFixed(0)}</strong>
                </span>
              </div>

              {/* Progress Track */}
              <div className="w-full h-2 rounded-full bg-slate-950/80 p-0.5 border border-white/5 overflow-hidden">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${cfg.color} transition-all duration-700`}
                  style={{
                    width: `${Math.min(100, Math.max(10, data.current))}%`,
                    boxShadow: `0 0 12px ${cfg.glowColor}`,
                  }}
                ></div>
              </div>

              {/* Status Footer */}
              <div className="pt-2 flex items-center justify-between text-[10px] text-slate-400">
                <span>Health Index</span>
                <span
                  className={`font-semibold ${
                    isLow ? "text-amber-400" : "text-emerald-400"
                  }`}
                >
                  {isLow ? "⚡ Needs Care" : "🌿 In Harmony"}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
