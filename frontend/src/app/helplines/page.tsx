"use client";

import Link from "next/link";

export default function HelplinesPage() {
  const helplineGroups = [
    {
      category: "LEVEL_1: IMMEDIATE EMERGENCY (INDIA)",
      urgency: "critical",
      icon: "🚨",
      badge: "24/7 PRIORITY LINK",
      items: [
        {
          name: "NATIONAL EMERGENCY DIRECT LINK",
          number: "112",
          timing: "24/7 Immediate Response",
          desc: "All-in-one national emergency dispatch for medical assistance, police, and rapid protection.",
          type: "Emergency 24/7",
        },
        {
          name: "CHILDLINE YOUTH OUTREACH",
          number: "1098",
          timing: "24/7 Toll-Free Priority",
          desc: "National emergency outreach dedicated specifically for children, teenagers, and student welfare.",
          type: "Teen Outreach",
        },
      ],
    },
    {
      category: "LEVEL_2: PSYCHOLOGICAL & MENTAL SUPPORT",
      urgency: "support",
      icon: "🌱",
      badge: "FREE & CONFIDENTIAL",
      items: [
        {
          name: "Tele-MANAS (Govt. of India)",
          number: "14416 / 1800-891-4416",
          timing: "24/7 Free • Multilingual (20+ Indian languages)",
          desc: "Comprehensive national mental health care network staffed by clinical counselors and psychiatrists.",
          type: "Govt Network",
        },
        {
          name: "Vandrevala Foundation Helpline",
          number: "+91 9999 666 555",
          timing: "24/7 Free Support • Voice & WhatsApp",
          desc: "Confidential crisis intervention and emotional counseling for acute anxiety, academic pressure, and family strain.",
          type: "Crisis Counseling",
        },
        {
          name: "iCall Helpline (TISS)",
          number: "+91 9152987821",
          timing: "Mon-Sat 08:00 - 22:00",
          desc: "Psychosocial counseling operated by Tata Institute of Social Sciences for students and youth.",
          type: "Youth Support",
        },
        {
          name: "KIRAN Mental Health Network",
          number: "1800-599-0019",
          timing: "24/7 Toll-Free",
          desc: "Ministry of Social Justice 24/7 national mental health first-aid and counseling helpline.",
          type: "National Helpline",
        },
      ],
    },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 space-y-8 font-mono-hud">
      {/* Top Header */}
      <div className="border-b border-cyan-500/20 pb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 bg-rose-500 rounded-sm shadow-[0_0_8px_#f43f5e] animate-pulse"></span>
          <h1 className="text-xl sm:text-2xl font-extrabold text-rose-300 tracking-widest">
            HUMAN ESCALATION PROTOCOLS
          </h1>
        </div>
        <div className="text-[11px] text-slate-400">
          CONFIDENTIAL &bull; DIRECT DISPATCH &bull; ZERO COST
        </div>
      </div>

      {/* Return to Core Banner */}
      <div className="hud-panel p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-cyan-300 text-sm tracking-wider">&gt; NEED VOCAL DE-ESCALATION?</h3>
          <p className="text-xs font-sans text-slate-300 mt-0.5">
            You can return to the Voice AI Core anytime, or dial the verified human crisis helplines below.
          </p>
        </div>
        <Link
          href="/"
          className="px-4 py-2 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/50 text-cyan-300 font-bold text-xs shrink-0 transition-all shadow-[0_0_12px_rgba(0,240,255,0.2)]"
        >
          RETURN TO AI CORE &rarr;
        </Link>
      </div>

      {/* Helplines Groups */}
      <div className="space-y-6">
        {helplineGroups.map((grp) => (
          <div key={grp.category} className="space-y-3">
            <div className="flex items-center justify-between border-b border-white/10 pb-1.5">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                <span>{grp.icon}</span>
                <span>{grp.category}</span>
              </div>
              <span className="text-[10px] text-cyan-400 font-bold">{grp.badge}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {grp.items.map((item, idx) => (
                <div
                  key={idx}
                  className={`hud-panel p-4 flex flex-col justify-between ${
                    grp.urgency === "critical"
                      ? "border-rose-500/40 bg-rose-950/20"
                      : "border-cyan-500/20"
                  }`}
                >
                  <div className="space-y-2 mb-3">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-bold text-white text-xs">{item.name}</h3>
                      <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-white/10 text-slate-300">
                        {item.type}
                      </span>
                    </div>
                    <p className="text-xs font-sans text-slate-300 leading-relaxed">{item.desc}</p>
                    <div className="text-[10px] text-cyan-400 font-medium">
                      ⏰ {item.timing}
                    </div>
                  </div>

                  <a
                    href={`tel:${item.number.split("/")[0].trim()}`}
                    className={`w-full py-2 rounded-lg font-bold text-xs flex items-center justify-center gap-1.5 transition-all shadow-md ${
                      grp.urgency === "critical"
                        ? "bg-rose-600 hover:bg-rose-500 text-white shadow-rose-600/40"
                        : "bg-cyan-500/20 hover:bg-cyan-500/40 border border-cyan-400/50 text-cyan-300 hover:text-white"
                    }`}
                  >
                    <span>📞 DIAL: {item.number}</span>
                  </a>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Safety Notice */}
      <div className="p-4 rounded-xl bg-slate-950 border border-white/10 text-center text-[11px] text-slate-400 space-y-1 font-sans">
        <p className="font-bold text-slate-300 font-mono-hud uppercase">
          &gt; RESPONSIBLE AI GOVERNANCE NOTICE:
        </p>
        <p>
          Aura is an autonomous AI agent for preventive pattern recognition. It does not provide medical diagnoses.
          In critical emergencies, dial 112 or contact trusted parents and guardians immediately.
        </p>
      </div>
    </div>
  );
}
