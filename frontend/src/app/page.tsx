"use client";

import VoiceInterface from "@/components/VoiceChat/VoiceInterface";

export default function HomePage() {
  return (
    <main className="w-full min-h-[calc(100vh-70px)] bg-[#010a12] text-cyan-200">
      <div className="w-full max-w-[1800px] mx-auto h-full px-4 sm:px-6 py-4">
        <VoiceInterface />
      </div>
    </main>
  );
}
