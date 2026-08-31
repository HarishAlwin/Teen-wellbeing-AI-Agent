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
            <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center shrink-0">
              {isEmergency ? (
                <svg className="w-6 h-6 text-rose-400" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
              ) : isHighConcern ? (
                <svg className="w-6 h-6 text-amber-400" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
              ) : (
                <svg className="w-6 h-6 text-indigo-400" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clipRule="evenodd" /></svg>
              )}
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
            <svg className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20"><path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.477.859h4z" /></svg>
            <div>
              <strong className="text-white font-semibold">Recommended Next Step: </strong>
              <span>
                {guidance?.action ||
                  "Talk with a trusted parent, school counselor, or connect with confidential support below."}
              </span>
            </div>
          </div>
        </div>

        {/* Emergency Auto-Call Dispatch Notification */}
        {isEmergency && (
          <div className="p-4 mb-4 rounded-2xl bg-rose-600/25 border border-rose-500/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-[0_0_20px_rgba(244,63,94,0.2)]">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-rose-400 animate-ping"></span>
                <h3 className="font-bold text-rose-100 text-sm">Automated Emergency Dispatch Active</h3>
              </div>
              <p className="text-xs text-rose-200">
                Priority alert & voice call dispatched to your <strong className="text-white">Designated Emergency Guardian</strong>.
              </p>
            </div>
            <a
              href={`tel:${emergencyNumber}`}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-xl flex items-center gap-2 shadow-lg shadow-rose-600/40 transition-all shrink-0"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z" /></svg>
              <span>Emergency Call ({emergencyNumber})</span>
            </a>
          </div>
        )}

        {/* Free Helpline List */}
        <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
          <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Additional 24/7 Crisis Resources
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
