"use client";

import VoiceInterface from "@/components/VoiceChat/VoiceInterface";

export default function ChatPage() {
  return (
    <div className="max-w-5xl mx-auto px-3 sm:px-6 py-3 space-y-3 font-mono-hud">
      {/* Top Banner */}
      <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 bg-cyan-400 rounded-sm shadow-[0_0_8px_#00f0ff] animate-pulse"></span>
          <h1 className="text-cyan-300 font-extrabold tracking-widest text-sm sm:text-base">
            JARVIS // VOICE REASONING CORE
          </h1>
        </div>

        <div className="flex items-center gap-2 text-[10px]">
          <span className="px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 font-bold">
            ENCRYPTION: QUANTUM_SECURE
          </span>
        </div>
      </div>

      <VoiceInterface />
    </div>
  );
}
