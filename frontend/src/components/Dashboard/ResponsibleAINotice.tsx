"use client";

export default function ResponsibleAINotice() {
  return (
    <div className="glass-panel p-6 sm:p-7 rounded-2xl border border-indigo-500/20 bg-gradient-to-r from-indigo-950/30 via-slate-950/40 to-purple-950/20 space-y-3">
      <div className="flex items-center gap-2 text-indigo-300">
        <span className="text-xl">🛡️</span>
        <h4 className="font-bold text-sm uppercase tracking-wider">
          Responsible AI & Teen Safety Architecture
        </h4>
      </div>

      <p className="text-xs text-slate-300 leading-relaxed max-w-3xl">
        Aura is designed strictly as a <strong>preventive voice companion and early pattern awareness tool</strong>.
        It does not diagnose psychological disorders or replace parents, doctors, therapists, or emergency responders.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
        <div className="p-3.5 rounded-xl bg-slate-950/70 border border-white/5 text-[11px] text-slate-300">
          <strong className="text-white block mb-0.5 font-bold">Non-Diagnostic</strong>
          Identifies behavioral stress patterns and balance shifts without clinical labels.
        </div>
        <div className="p-3.5 rounded-xl bg-slate-950/70 border border-white/5 text-[11px] text-slate-300">
          <strong className="text-white block mb-0.5 font-bold">Privacy & Trust</strong>
          Built with data minimization and secure storage to safeguard teenager confidence.
        </div>
        <div className="p-3.5 rounded-xl bg-slate-950/70 border border-white/5 text-[11px] text-slate-300">
          <strong className="text-white block mb-0.5 font-bold">Human Connection First</strong>
          Always guides teens toward trusted parents, school mentors, or free 24/7 helplines.
        </div>
      </div>
    </div>
  );
}
