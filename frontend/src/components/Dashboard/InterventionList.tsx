"use client";

interface InterventionItem {
  id: string;
  type: string;
  title: string;
  content: string;
  risk_level: string;
  date: string;
}

interface InterventionListProps {
  interventions: InterventionItem[];
}

export default function InterventionList({ interventions }: InterventionListProps) {
  if (!interventions || interventions.length === 0) {
    return (
      <div className="glass-panel p-6 rounded-2xl text-center text-slate-400 text-sm">
        No past recommendations yet. Coping techniques appear automatically as you speak with Aura.
      </div>
    );
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "routine_suggestion":
        return "RTN";
      case "coping_strategy":
        return "COP";
      case "trusted_human_referral":
        return "REF";
      case "emergency_helpline":
        return "SOS";
      default:
        return "TIP";
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-white text-base">Personal Guidance History</h3>
          </div>
          <p className="text-xs text-slate-400">
            Tailored micro-actions, coping techniques & support steps
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {interventions.map((item) => (
          <div
            key={item.id}
            className="p-4 rounded-xl bg-slate-950/70 border border-white/5 hover:border-white/15 transition-all flex items-start gap-3.5"
          >
            <div className="w-9 h-9 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[10px] font-bold font-mono-hud text-cyan-400 shrink-0">
              {getTypeIcon(item.type)}
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between gap-2 mb-1">
                <h4 className="font-bold text-white text-sm">{item.title}</h4>
                <span className="text-[10px] text-slate-400 font-medium">{item.date}</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">{item.content}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
