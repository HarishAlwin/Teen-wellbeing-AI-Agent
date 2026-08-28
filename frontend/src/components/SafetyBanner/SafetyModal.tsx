"use client";

interface HelplineResource {
  name: string;
  number: string;
  availability: string;
  type: string;
}

interface SafetyModalProps {
  riskLevel: "NORMAL" | "CONCERNING" | "HIGH_CONCERN" | "IMMEDIATE_SAFETY";
  guidance?: {
    headline: string;
    message: string;
    action: string;
    show_helplines: boolean;
    urgency: string;
  };
  helplines?: {
    country: string;
    emergency: string;
    resources: HelplineResource[];
  };
  isOpen: boolean;
  onClose: () => void;
}

export default function SafetyModal({
  riskLevel,
  guidance,
  helplines,
  isOpen,
  onClose,
}: SafetyModalProps) {
  if (!isOpen) return null;

  const isEmergency = riskLevel === "IMMEDIATE_SAFETY";
  const isHighConcern = riskLevel === "HIGH_CONCERN";

  const defaultIndiaResources: HelplineResource[] = [
    {
      name: "CHILDLINE (National Youth Outreach)",
      number: "1098",
      availability: "24/7 Toll-Free Call",
      type: "Youth & Teen Support",
    },
    {
      name: "Tele-MANAS (Govt. of India Helpline)",
      number: "14416 / 1800-891-4416",
      availability: "24/7 Multilingual Support (20+ langs)",
      type: "National Mental Health",
    },
    {
      name: "Vandrevala Foundation Helpline",
      number: "+91 9999 666 555",
      availability: "24/7 Free Support & WhatsApp",
      type: "Confidential Counseling",
    },
    {
      name: "iCall Psychosocial Helpline (TISS)",
      number: "+91 9152987821",
      availability: "Mon-Sat 8:00 AM - 10:00 PM",
      type: "Student & Youth Support",
    },
  ];

  const resources = helplines?.resources || defaultIndiaResources;
  const emergencyNumber = helplines?.emergency || "112";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xl animate-fadeIn">
      <div
        className={`w-full max-w-xl rounded-3xl p-6 sm:p-8 border shadow-2xl transition-all ${
          isEmergency
            ? "bg-gradient-to-b from-rose-950/95 to-slate-950/95 border-rose-500/50 shadow-rose-900/30"
            : isHighConcern
            ? "bg-gradient-to-b from-amber-950/95 to-slate-950/95 border-amber-500/50 shadow-amber-900/30"
            : "bg-gradient-to-b from-slate-900/95 to-slate-950/95 border-indigo-500/40 shadow-indigo-900/30"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center text-2xl shrink-0">
              {isEmergency ? "🚨" : isHighConcern ? "🛡️" : "🌱"}
            </div>
            <div>
              <span
                className={`text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full ${
                  isEmergency
                    ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                    : isHighConcern
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                    : "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                }`}
              >
                {riskLevel.replace("_", " ")} Support Notice
              </span>
              <h2 className="text-lg font-bold text-white mt-1">
                {guidance?.headline || "We're Here With You"}
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-white/5 hover:bg-white/15 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Message */}
        <div className="my-5 space-y-3">
          <p className="text-slate-200 text-sm leading-relaxed">
            {guidance?.message ||
              "You don't have to carry heavy moments all by yourself. Reaching out to someone who cares makes a real difference."}
          </p>

          <div className="p-3.5 rounded-xl bg-white/5 border border-white/10 text-xs text-slate-300 flex items-start gap-2.5">
            <span className="text-base">💡</span>
            <div>
              <strong className="text-white font-semibold">Recommended Next Step: </strong>
              <span>
                {guidance?.action ||
                  "Talk with a trusted parent, school counselor, or connect with confidential support below."}
              </span>
            </div>
          </div>
        </div>

        {/* Emergency Dial for Urgent Safety */}
        {isEmergency && (
          <div className="p-4 mb-4 rounded-2xl bg-rose-600/20 border border-rose-500/40 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-rose-200 text-sm">Immediate Emergency Care</h3>
              <p className="text-xs text-rose-300">National 24/7 Police & Ambulance</p>
            </div>
            <a
              href={`tel:${emergencyNumber}`}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-xl flex items-center gap-2 shadow-lg shadow-rose-600/30 transition-all"
            >
              <span>📞 Dial {emergencyNumber}</span>
            </a>
          </div>
        )}

        {/* Free Helpline List */}
        <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
          <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Free, Confidential Resources (India)
          </h4>
          {resources.map((res, i) => (
            <div
              key={i}
              className="p-3 rounded-xl bg-slate-950/70 border border-white/5 flex items-center justify-between gap-3 hover:border-white/20 transition-all"
            >
              <div>
                <h5 className="font-semibold text-xs text-white">{res.name}</h5>
                <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                  <span className="text-indigo-400 font-semibold">{res.number}</span>
                  <span>•</span>
                  <span>{res.availability}</span>
                </div>
              </div>
              <a
                href={`tel:${res.number.split("/")[0].trim()}`}
                className="shrink-0 px-3 py-1.5 bg-indigo-600/25 hover:bg-indigo-600 text-indigo-200 hover:text-white border border-indigo-500/30 rounded-lg text-xs font-semibold transition-all"
              >
                Call
              </a>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between">
          <p className="text-[10px] text-slate-400">
            Aura is an AI companion for preventive support, not a clinical emergency service.
          </p>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-semibold transition-colors"
          >
            I understand
          </button>
        </div>
      </div>
    </div>
  );
}
