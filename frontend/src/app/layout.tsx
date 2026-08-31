import type { Metadata } from "next";
import { Oxanium, Space_Grotesk } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navigation/Navbar";

const oxanium = Oxanium({
  subsets: ["latin"],
  variable: "--font-hud",
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Jarvis AI • Neural Voice Wellbeing Core",
  description:
    "An empathetic voice-first AI companion that listens, understands 5 core life dimensions, detects subtle patterns early, and communicates seamlessly using speech alone.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${oxanium.variable} ${spaceGrotesk.variable}`}>
      <body className="font-sans antialiased min-h-screen bg-black text-slate-100 flex flex-col justify-between overflow-x-hidden selection:bg-cyan-500/30 selection:text-cyan-200">
        <div className="relative z-10 w-full flex-1 flex flex-col">
          <Navbar />
          <main className="flex-1 flex flex-col">{children}</main>
        </div>
      </body>
    </html>
  );
}
