"use client";

interface PatternItem {
  id: string;
  title: string;
  description: string;
  category: string;
  severity: string;
  dimensions_involved: string[];
  evidence_snippets: string[];
  occurrence_count: number;
}

interface PatternCardsProps {
  patterns: PatternItem[];
}

export default function PatternCards({ patterns }: PatternCardsProps) {
  if (!patterns || patterns.length === 0) {
    return (
      <div className="glass-panel p-6 rounded-2xl text-center text-slate-400 text-sm">
        ✨ No persistent concerning loops detected. Keep chatting naturally with Aura!
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🔄</span>
            <h3 className="font-bold text-white text-base">Identified Life Patterns</h3>
          </div>
          <p className="text-xs text-slate-400">
            Cross-category connections, behavioral loops, and baseline deviations
          </p>
        </div>
        <span className="px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 text-xs font-bold border border-indigo-500/30">
          {patterns.length} Active
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {patterns.map((pat) => {
          const isHigh = pat.severity === "high";

          return (
            <div
              key={pat.id}
              className={`glass-panel p-5 rounded-2xl border flex flex-col justify-between transition-all ${
                isHigh
                  ? "border-rose-500/40 bg-gradient-to-b from-rose-950/20 to-transparent"
                  : "border-indigo-500/30 hover:border-indigo-500/50"
              }`}
            >
              <div>
                {/* Header */}
                <div className="flex items-start justify-between gap-3 mb-2.5">
                  <h4 className="font-bold text-white text-sm leading-snug">{pat.title}</h4>
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full shrink-0 ${
                      isHigh
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                        : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                    }`}
                  >
                    {pat.severity} impact
                  </span>
                </div>

                {/* Description */}
                <p className="text-xs text-slate-300 leading-relaxed mb-3.5">
                  {pat.description}
                </p>

                {/* Connected Dimensions Flow */}
                {pat.dimensions_involved && pat.dimensions_involved.length > 0 && (
                  <div className="mb-3">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1.5">
                      Compounding Chain:
                    </span>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {pat.dimensions_involved.map((dim, i) => (
                        <span key={dim} className="flex items-center gap-1.5">
                          <span className="px-2.5 py-0.5 rounded-md bg-white/10 text-slate-200 text-xs font-semibold capitalize">
                            {dim}
                          </span>
                          {i < pat.dimensions_involved.length - 1 && (
                            <span className="text-indigo-400 text-xs font-bold">→</span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Evidence Snippets */}
              {pat.evidence_snippets && pat.evidence_snippets.length > 0 && (
                <div className="mt-3 p-3 rounded-xl bg-slate-950/80 border border-white/5 space-y-1">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">
                    Observed Indicators:
                  </span>
                  {pat.evidence_snippets.map((snip, i) => (
                    <p key={i} className="text-[11px] text-slate-300 italic">
                      • "{snip}"
                    </p>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
