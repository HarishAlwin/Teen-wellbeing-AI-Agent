import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navigation/Navbar";

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-heading",
  weight: ["500", "600", "700", "800"],
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Aura Teen • Voice AI Wellbeing Intelligence",
  description:
    "An empathetic voice-first AI companion that listens, understands 5 core life dimensions, detects subtle patterns early, and guides teenagers toward healthy balances.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${plusJakartaSans.variable} ${inter.variable}`}>
      <body className="font-sans antialiased min-h-screen flex flex-col justify-between selection:bg-indigo-500/30 selection:text-indigo-200">
        <div className="relative z-10">
          <Navbar />
          <main className="pb-16">{children}</main>
        </div>

        <footer className="relative z-10 border-t border-white/5 bg-slate-950/40 backdrop-blur-md py-8 px-6 text-center text-xs text-slate-500">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-indigo-500 to-pink-500 flex items-center justify-center text-[10px] text-white font-bold">
                A
              </div>
              <span className="font-semibold text-slate-300">Aura Teen Wellbeing Intelligence</span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-400">Preventive Voice AI Companion</span>
            </div>

            <p className="text-[11px] text-slate-400 max-w-lg text-center md:text-right">
              Designed for supportive listening and early pattern awareness, not clinical diagnosis.
              If in distress or emergency, dial <strong className="text-indigo-300">112</strong> or <strong className="text-indigo-300">1098</strong>.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
