"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

export default function Navbar() {
  const pathname = usePathname();
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
        setIsFullscreen(false);
      }
    }
  };

  return (
    <header className="sticky top-0 z-50 px-4 sm:px-8 py-3 bg-black/80 backdrop-blur-md transition-all">
      <div className="max-w-[1700px] mx-auto flex items-center justify-between">
        {/* Left Branding */}
        <Link href="/" className="flex items-center gap-2 group">
          <span className="font-extrabold text-sm sm:text-base tracking-wider text-white group-hover:text-cyan-400 transition-colors font-mono-hud uppercase">
            FRIDAY
          </span>
        </Link>

        {/* Center Tabs */}
        <nav className="flex items-center gap-1.5 sm:gap-3 bg-slate-950/70 border border-white/10 px-2 py-1 rounded-xl shadow-[0_0_15px_rgba(0,0,0,0.5)]">
          {/* Home Tab */}
          <Link
            href="/"
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              pathname === "/"
                ? "bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 shadow-[0_0_12px_rgba(0,240,255,0.25)]"
                : "text-slate-400 hover:text-white hover:bg-white/5 border border-transparent"
            }`}
          >
            {/* Home Icon */}
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z" />
            </svg>
            <span>Home</span>
          </Link>





          {/* Helplines Link */}
          <Link
            href="/helplines"
            className={`hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              pathname === "/helplines"
                ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                : "text-slate-500 hover:text-rose-300 hover:bg-white/5"
            }`}
          >
            <span>SOS</span>
          </Link>
        </nav>

        {/* Right Window Controls (matching screenshot style) */}
        <div className="flex items-center gap-2">
          {/* Hide / Minimize */}
          <button
            onClick={() => {}}
            title="HIDE LOGS"
            className="px-3 py-1 rounded border border-cyan-500/30 text-[10px] font-bold text-cyan-300 hover:text-white hover:bg-cyan-500/20 transition-colors flex items-center gap-1.5 font-mono-hud"
          >
            <span>HIDE LOGS</span>
            <div className="w-1.5 h-1.5 rounded-full bg-white"></div>
          </button>

          {/* Terminate */}
          <button
            onClick={() => {}}
            title="TERMINATE"
            className="px-3 py-1 rounded border border-rose-500/30 text-[10px] font-bold text-rose-400 hover:text-white hover:bg-rose-500/20 transition-colors flex items-center gap-1.5 font-mono-hud ml-1"
          >
            <span>TERMINATE</span>
            <span className="text-rose-500">✕</span>
          </button>

          {/* Close / Status */}
          <button
            onClick={() => {}}
            title="Active Core"
            className="w-6 h-6 rounded bg-rose-500/20 hover:bg-rose-500/40 text-rose-400 hover:text-white flex items-center justify-center transition-colors text-xs font-bold"
          >
            ✕
          </button>
        </div>
      </div>
    </header>
  );
}
