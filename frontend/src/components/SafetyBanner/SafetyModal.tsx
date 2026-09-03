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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-md rounded-3xl p-6 sm:p-7 bg-white border border-slate-100 shadow-xl">
        {/* Header */}
        <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
          <div className="w-11 h-11 rounded-2xl bg-teal-50 flex items-center justify-center text-xl shrink-0">
            {isEmergency ? "💛" : "🌱"}
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-800">
              {guidance?.headline || "We're Here With You"}
            </h2>
          </div>
        </div>

        {/* Message */}
        <div className="my-4 space-y-3">
          <p className="text-slate-600 text-sm leading-relaxed">
            {guidance?.message ||
              "You don't have to carry heavy moments all by yourself. Reaching out to someone who cares makes a real difference."}
          </p>

          <div className="p-3.5 rounded-2xl bg-slate-50 text-xs text-slate-600 leading-relaxed">
            <strong className="text-slate-700 font-medium">Next step: </strong>
            {guidance?.action ||
              "Talk with a trusted parent, school counselor, or connect with confidential support below."}
          </div>
        </div>

        {/* Emergency Dial */}
        {isEmergency && (
          <div className="p-4 mb-4 rounded-2xl bg-amber-50 border border-amber-100 flex items-center justify-between">
            <div>
              <h3 className="font-medium text-slate-700 text-sm">Immediate emergency care</h3>
              <p className="text-xs text-slate-500">24/7 police & ambulance</p>
            </div>
            <a
              href={`tel:${emergencyNumber}`}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white font-medium text-xs rounded-full transition-colors"
            >
              Call {emergencyNumber}
            </a>
          </div>
        )}

        {/* Helpline List */}
        <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
          <h4 className="text-[11px] font-medium text-slate-400 uppercase tracking-wide">
            Free, confidential support
          </h4>
          {resources.map((res, i) => (
            <div
              key={i}
              className="p-3 rounded-2xl bg-slate-50 flex items-center justify-between gap-3"
            >
              <div>
                <h5 className="font-medium text-xs text-slate-700">{res.name}</h5>
                <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                  <span className="text-teal-700 font-medium">{res.number}</span>
                  <span>•</span>
                  <span>{res.availability}</span>
                </div>
              </div>
              <a
                href={`tel:${res.number.split("/")[0].trim()}`}
                className="shrink-0 px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-full text-xs font-medium transition-colors"
              >
                Call
              </a>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between gap-3">
          <p className="text-[11px] text-slate-400">
            Aura offers supportive listening, not clinical care.
          </p>
          <button
            onClick={onClose}
            className="shrink-0 px-4 py-2 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-medium transition-colors"
          >
            I understand
          </button>
        </div>
      </div>
    </div>
  );
}
