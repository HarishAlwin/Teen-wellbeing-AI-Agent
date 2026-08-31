"use client";

export default function ResponsibleAINotice() {
  return (
    <div className="glass-panel p-6 sm:p-7 rounded-2xl border border-indigo-500/20 bg-gradient-to-r from-indigo-950/30 via-slate-950/40 to-purple-950/20 space-y-3">
      <div className="flex items-center gap-2 text-indigo-300">
        <svg className="w-5 h-5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
        <h4 className="font-bold text-sm uppercase tracking-wider">
          Responsible AI &amp; Teen Safety Architecture
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
