"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

export default function Navbar() {
  const pathname = usePathname();
  const [timeStr, setTimeStr] = useState<string>("");

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const navLinks = [
    { href: "/", label: "AI CORE HUD", code: "01" },
    { href: "/dashboard", label: "TELEMETRY", code: "02" },
    { href: "/helplines", label: "CRISIS PROTOCOLS", code: "03" },
  ];

  return (
    <header className="sticky top-0 z-50 px-4 sm:px-6 pt-3 pb-2 transition-all">
      <div className="max-w-[1500px] mx-auto flex items-center justify-between gap-4 px-4 py-2.5 rounded-xl bg-slate-950/80 backdrop-blur-xl border border-cyan-500/30 shadow-[0_0_20px_rgba(0,240,255,0.15)] font-mono-hud text-xs">
        {/* Brand / Core Identity */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="relative w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-400/50 flex items-center justify-center shadow-[0_0_12px_rgba(0,240,255,0.4)] group-hover:scale-105 transition-transform">
            <span className="text-sm animate-pulse text-cyan-400">⚡</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold tracking-widest text-cyan-300 text-sm">
                AURA // NEURAL CORE
              </span>
              <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-cyan-500/20 text-cyan-400 border border-cyan-400/40">
                v3.4 ONLINE
              </span>
            </div>
            <span className="text-[10px] text-slate-400 tracking-wider hidden sm:inline">
              PREVENTIVE TEEN INTELLIGENCE
            </span>
          </div>
        </Link>

        {/* HUD Navigation Tabs */}
        <nav className="flex items-center gap-1.5 sm:gap-2">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all tracking-wider ${
                  isActive
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-400/60 shadow-[0_0_15px_rgba(0,240,255,0.3)] font-bold"
                    : "text-slate-400 hover:text-cyan-300 hover:bg-white/5 border border-transparent"
                }`}
              >
                <span className="text-[10px] text-cyan-500 font-bold opacity-75">[{link.code}]</span>
                <span className="text-xs">{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Live Diagnostics HUD */}
        <div className="hidden lg:flex items-center gap-4 text-[11px] text-slate-400">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">SYNC:</span>
            <span className="text-emerald-400 font-bold">12ms</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span className="text-emerald-400 font-bold">STT/TTS LINKED</span>
          </div>

          {timeStr && (
            <div className="px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 font-bold">
              {timeStr}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
