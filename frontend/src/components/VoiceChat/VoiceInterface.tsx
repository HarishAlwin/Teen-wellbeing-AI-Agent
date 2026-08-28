"use client";

import { useState, useEffect, useRef } from "react";
import {
  sendMessage,
  transcribeAudio,
  synthesizeSpeech,
  submitFeedback,
  ChatResponse,
} from "@/lib/api";
import {
  startRecording,
  stopRecording,
  startBrowserSpeechRecognition,
  playSpokenResponse,
  stopAudioPlayback,
} from "@/lib/audio";
import SafetyModal from "@/components/SafetyBanner/SafetyModal";

interface MessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  emotions?: string[];
  riskLevel?: string;
  intervention?: {
    id: string;
    title: string;
    content: string;
  };
}

export default function VoiceInterface({
  onDataUpdate,
}: {
  onDataUpdate?: (data: ChatResponse) => void;
}) {
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "welcome-msg",
      role: "assistant",
      timestamp: "SYSTEM ONLINE",
      content:
        "Greetings. Aura Neural Core is initialized and monitoring your wellbeing baseline. Speak naturally about academic pressure, sleep, social dynamics, or anything on your mind. I am listening.",
      emotions: ["active", "receptive"],
      riskLevel: "NORMAL",
    },
  ]);

  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [textInput, setTextInput] = useState("");
  const [currentTranscript, setCurrentTranscript] = useState("");
  const [userId, setUserId] = useState<string>("");
  const [conversationId, setConversationId] = useState<string>("");
  const [latestResponse, setLatestResponse] = useState<ChatResponse | null>(null);

  // Safety Modal state
  const [isSafetyModalOpen, setIsSafetyModalOpen] = useState(false);
  const [safetyData, setSafetyData] = useState<{
    riskLevel: "NORMAL" | "CONCERNING" | "HIGH_CONCERN" | "IMMEDIATE_SAFETY";
    guidance?: any;
    helplines?: any;
  }>({ riskLevel: "NORMAL" });

  const speechRecognitionRef = useRef<{ stop: () => void } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const savedUserId = localStorage.getItem("teen_user_id") || "teen-alex-01";
    setUserId(savedUserId);
    localStorage.setItem("teen_user_id", savedUserId);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentTranscript]);

  const handleToggleRecord = async () => {
    if (isRecording) {
      setIsRecording(false);
      setIsProcessing(true);

      if (speechRecognitionRef.current) {
        speechRecognitionRef.current.stop();
        speechRecognitionRef.current = null;
      }

      try {
        const audioBlob = await stopRecording();
        let spokenText = currentTranscript.trim();

        if (!spokenText && audioBlob.size > 0) {
          spokenText = await transcribeAudio(audioBlob);
        }

        if (spokenText) {
          await processUserMessage(spokenText);
        } else {
          setIsProcessing(false);
        }
      } catch (err) {
        console.error("Error finalizing audio:", err);
        setIsProcessing(false);
      }
    } else {
      stopAudioPlayback();
      setIsSpeaking(false);
      setCurrentTranscript("");

      try {
        await startRecording();
        setIsRecording(true);

        const recognition = startBrowserSpeechRecognition(
          (liveText) => {
            setCurrentTranscript(liveText);
          },
          (err) => {
            console.warn("Speech recognition notice:", err);
          }
        );
        speechRecognitionRef.current = recognition;
      } catch (err) {
        console.error("Error starting recording:", err);
        setIsRecording(false);
      }
    }
  };

  const processUserMessage = async (userText: string) => {
    if (!userText.trim()) return;

    const timeString = new Date().toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
    });

    const userMsgId = `msg-${Date.now()}`;
    const newMessages: MessageItem[] = [
      ...messages,
      { id: userMsgId, role: "user", content: userText, timestamp: timeString },
    ];
    setMessages(newMessages);
    setCurrentTranscript("");
    setIsProcessing(true);

    try {
      const resp = await sendMessage(
        userText,
        userId || "teen-alex-01",
        conversationId || undefined
      );

      setLatestResponse(resp);
      if (resp.conversation_id) {
        setConversationId(resp.conversation_id);
      }
      if (onDataUpdate) {
        onDataUpdate(resp);
      }

      if (resp.risk_level === "IMMEDIATE_SAFETY" || resp.risk_level === "HIGH_CONCERN") {
        setSafetyData({
          riskLevel: resp.risk_level,
          guidance: resp.safety_guidance,
          helplines: resp.helplines,
        });
        setIsSafetyModalOpen(true);
      }

      const assistantMsg: MessageItem = {
        id: `msg-${Date.now() + 1}`,
        role: "assistant",
        content: resp.response_text,
        timestamp: timeString,
        emotions: resp.emotions_detected,
        riskLevel: resp.risk_level,
        intervention: resp.intervention
          ? {
              id: resp.intervention.id,
              title: resp.intervention.title,
              content: resp.intervention.content,
            }
          : undefined,
      };

      setMessages([...newMessages, assistantMsg]);
      setIsProcessing(false);

      try {
        const audioBlob = await synthesizeSpeech(resp.response_text);
        playSpokenResponse(
          audioBlob,
          resp.response_text,
          () => setIsSpeaking(true),
          () => setIsSpeaking(false)
        );
      } catch (audioErr) {
        playSpokenResponse(
          null,
          resp.response_text,
          () => setIsSpeaking(true),
          () => setIsSpeaking(false)
        );
      }
    } catch (err) {
      console.error("Error communicating with AI Core:", err);
      setIsProcessing(false);
      setMessages([
        ...newMessages,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          timestamp: timeString,
          content:
            "Acoustic feedback loop glitch detected. Neural Core remains ready for input. Please transmit again.",
        },
      ]);
    }
  };

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput.trim() || isProcessing) return;
    const txt = textInput;
    setTextInput("");
    await processUserMessage(txt);
  };

  const quickTelemetryPrompts = [
    { label: "EXAM_ANXIETY", text: "I have exams coming up and I'm feeling overwhelmed with study pressure." },
    { label: "SLEEP_DEBT", text: "I've been doomscrolling on my phone until 3 AM and I can't wake up." },
    { label: "PEER_ISOLATION", text: "I feel left out from my friend group and isolated lately." },
    { label: "PARENT_PRESSURE", text: "My parents are putting extreme pressure on my academic grades." },
  ];

  return (
    <div className="flex flex-col h-full space-y-4 font-mono-hud">
      {/* Safety Protocol Banner (if triggered) */}
      {latestResponse && latestResponse.risk_level !== "NORMAL" && (
        <div
          onClick={() => {
            setSafetyData({
              riskLevel: latestResponse.risk_level,
              guidance: latestResponse.safety_guidance,
              helplines: latestResponse.helplines,
            });
            setIsSafetyModalOpen(true);
          }}
          className={`p-3.5 rounded-xl border flex items-center justify-between cursor-pointer transition-all hover:scale-[1.005] ${
            latestResponse.risk_level === "IMMEDIATE_SAFETY"
              ? "bg-rose-950/80 border-rose-500 text-rose-200 shadow-[0_0_20px_rgba(244,63,94,0.3)]"
              : "bg-amber-950/80 border-amber-500 text-amber-200 shadow-[0_0_20px_rgba(245,158,11,0.3)]"
          }`}
        >
          <div className="flex items-center gap-3">
            <span className="text-xl animate-pulse">⚠️</span>
            <div>
              <div className="text-xs font-bold tracking-widest uppercase">
                SAFETY PROTOCOL TRIGGERED: [{latestResponse.risk_level}]
              </div>
              <div className="text-[11px] opacity-90 font-sans mt-0.5">
                {latestResponse.safety_guidance?.headline || "Human Connection Guidance Recommended"}
              </div>
            </div>
          </div>
          <span className="text-[11px] font-bold px-3 py-1 rounded bg-white/10 border border-white/20">
            VIEW PROTOCOL →
          </span>
        </div>
      )}

      {/* Main Jarvis Voice Sphere Core */}
      <div className="hud-panel p-6 sm:p-8 flex flex-col items-center justify-center relative overflow-hidden">
        {/* Radar Scanning Line Background */}
        <div className="absolute inset-0 pointer-events-none opacity-20 bg-[radial-gradient(circle_at_center,rgba(0,240,255,0.15)_0,transparent_70%)]"></div>

        {/* Status HUD Header */}
        <div className="w-full flex items-center justify-between text-[11px] text-slate-400 border-b border-cyan-500/20 pb-3 mb-6">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
            <span className="text-cyan-300 font-bold tracking-wider">
              {isRecording
                ? "ACOUSTIC INTAKE: ACTIVE"
                : isSpeaking
                ? "SYNTHESIS VOCALIZING..."
                : isProcessing
                ? "NEURAL REASONING ENGINE..."
                : "JARVIS CORE: LISTENING"}
            </span>
          </div>

          <div className="flex items-center gap-3 text-[10px]">
            <span className="text-slate-500">ENGINE:</span>
            <span className="text-cyan-400 font-bold">GEMINI 1.5</span>
            <span className="text-slate-500">|</span>
            <span className="text-slate-500">STT:</span>
            <span className="text-cyan-400 font-bold">DEEPGRAM</span>
          </div>
        </div>

        {/* Central Holographic Arc Reactor Orb */}
        <div className="relative my-6 flex items-center justify-center">
          {/* Outer Rotating Counter Rings */}
          <div className="absolute w-56 h-56 rounded-full border border-dashed border-cyan-400/30 animate-spin-slow pointer-events-none"></div>
          <div className="absolute w-48 h-48 rounded-full border border-cyan-500/20 border-t-cyan-400 border-b-cyan-400 animate-spin-reverse-slow pointer-events-none"></div>

          {/* Glowing Aura Rings */}
          {(isRecording || isSpeaking) && (
            <div className="absolute w-40 h-40 rounded-full bg-cyan-500/20 animate-ping opacity-50"></div>
          )}

          {/* Central Reactor Orb Button */}
          <button
            onClick={handleToggleRecord}
            disabled={isProcessing}
            aria-label={isRecording ? "Stop voice recording" : "Start speaking"}
            className={`relative z-10 w-36 h-36 rounded-full flex flex-col items-center justify-center transition-all duration-500 cursor-pointer shadow-2xl ${
              isRecording
                ? "bg-gradient-to-tr from-rose-600 to-rose-900 border-2 border-rose-400 shadow-[0_0_50px_rgba(244,63,94,0.6)] animate-pulse"
                : isSpeaking
                ? "bg-gradient-to-tr from-cyan-600 via-indigo-600 to-purple-800 border-2 border-cyan-300 shadow-[0_0_60px_rgba(0,240,255,0.7)] animate-jarvis-pulse"
                : isProcessing
                ? "bg-gradient-to-tr from-amber-600 to-orange-800 border-2 border-amber-400 shadow-[0_0_40px_rgba(245,158,11,0.5)] animate-spin-slow"
                : "bg-gradient-to-tr from-slate-950 via-cyan-950 to-slate-900 border-2 border-cyan-400/60 shadow-[0_0_35px_rgba(0,240,255,0.4)] hover:shadow-[0_0_50px_rgba(0,240,255,0.7)] hover:border-cyan-300 transform hover:scale-105"
            }`}
          >
            <span className="text-4xl">
              {isRecording ? "⏹️" : isSpeaking ? "🔊" : isProcessing ? "⚡" : "🎙️"}
            </span>
            <span className="text-[10px] font-extrabold uppercase tracking-widest text-cyan-200 mt-1">
              {isRecording
                ? "TRANSMIT"
                : isSpeaking
                ? "OUTPUT"
                : isProcessing
                ? "ANALYZING"
                : "TAP MIC"}
            </span>
          </button>
        </div>

        {/* Live Acoustic Waveform Visualizer */}
        <div className="w-full flex flex-col items-center gap-2 mt-2">
          <div className="flex items-center gap-1.5 h-10">
            {[20, 55, 90, 45, 80, 35, 95, 60, 85, 30, 70, 40, 75, 50, 85, 30].map((h, i) => (
              <div
                key={i}
                className={`w-1 rounded-full transition-all duration-200 ${
                  isRecording
                    ? "bg-rose-400 shadow-[0_0_8px_#f43f5e]"
                    : isSpeaking
                    ? "bg-cyan-400 shadow-[0_0_8px_#00f0ff] wave-bar-hud"
                    : "bg-cyan-950 h-1.5 border border-cyan-800/40"
                }`}
                style={{
                  height: isRecording || isSpeaking ? `${(h * 0.38) + 6}px` : "5px",
                  animationDelay: `${i * 0.06}s`,
                }}
              ></div>
            ))}
          </div>

          {currentTranscript && (
            <div className="px-3 py-1 rounded-lg bg-cyan-950/80 border border-cyan-400/40 text-xs text-cyan-200 text-center max-w-md line-clamp-2">
              &gt; LIVE INTAKE: "{currentTranscript}"
            </div>
          )}
        </div>
      </div>

      {/* Terminal Conversation Stream */}
      <div className="hud-panel p-4 sm:p-5 flex-1 flex flex-col justify-between min-h-[300px]">
        <div className="space-y-3.5 max-h-[260px] overflow-y-auto pr-1">
          {messages.map((msg) => {
            const isAssistant = msg.role === "assistant";

            return (
              <div
                key={msg.id}
                className={`flex flex-col ${isAssistant ? "items-start" : "items-end"}`}
              >
                <div
                  className={`max-w-[90%] sm:max-w-[85%] rounded-xl p-3.5 text-xs font-sans leading-relaxed ${
                    isAssistant
                      ? "bg-slate-950/90 border border-cyan-500/30 text-slate-200 rounded-tl-none shadow-[0_0_15px_rgba(0,240,255,0.08)]"
                      : "bg-cyan-950/90 border border-cyan-400/60 text-cyan-100 rounded-tr-none shadow-[0_0_15px_rgba(0,240,255,0.15)]"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 font-mono-hud text-[10px] text-cyan-400/80 mb-1 border-b border-white/5 pb-1">
                    <span>{isAssistant ? "⚡ AURA // CORE" : "👤 TEENAGER"}</span>
                    <span>{msg.timestamp}</span>
                  </div>

                  <p>{msg.content}</p>

                  {/* Micro-Intervention Suggestion */}
                  {msg.intervention && (
                    <div className="mt-2.5 p-2.5 rounded-lg bg-cyan-950/60 border border-cyan-400/30 font-mono-hud text-[11px] text-cyan-300">
                      <div className="font-bold flex items-center gap-1.5 mb-0.5">
                        <span>🛡️ PROTOCOL:</span>
                        <span>{msg.intervention.title}</span>
                      </div>
                      <p className="font-sans text-slate-300 text-xs">{msg.intervention.content}</p>
                    </div>
                  )}

                  {/* Detected Tone Signals */}
                  {isAssistant && msg.emotions && msg.emotions.length > 0 && (
                    <div className="mt-2 pt-1.5 border-t border-white/5 flex items-center gap-1.5 font-mono-hud text-[10px] text-slate-400">
                      <span>TONE_SIGNALS:</span>
                      {msg.emotions.map((e) => (
                        <span key={e} className="px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                          {e}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Command Injection Prompts & Input Bar */}
        <div className="pt-3 border-t border-cyan-500/20 space-y-2 mt-2">
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar text-[10px]">
            <span className="text-slate-500 font-bold shrink-0">[PRESETS]:</span>
            {quickTelemetryPrompts.map((item) => (
              <button
                key={item.label}
                onClick={() => processUserMessage(item.text)}
                disabled={isProcessing}
                className="shrink-0 px-2 py-0.5 rounded bg-cyan-950/60 hover:bg-cyan-900 text-cyan-300 border border-cyan-500/30 hover:border-cyan-400 transition-all cursor-pointer font-mono-hud"
              >
                {item.label}
              </button>
            ))}
          </div>

          <form onSubmit={handleTextSubmit} className="flex items-center gap-2">
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="&gt; Transmit neural message or query..."
              disabled={isProcessing}
              className="flex-1 px-3.5 py-2.5 rounded-lg bg-slate-950 border border-cyan-500/30 focus:border-cyan-400 focus:outline-none text-xs text-white placeholder:text-slate-600 font-mono-hud transition-colors"
            />
            <button
              type="submit"
              disabled={!textInput.trim() || isProcessing}
              className="px-4 py-2.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/40 border border-cyan-400/60 text-cyan-300 hover:text-white font-bold text-xs transition-all shadow-[0_0_15px_rgba(0,240,255,0.2)] cursor-pointer"
            >
              TRANSMIT ↵
            </button>
          </form>
        </div>
      </div>

      {/* Safety Modal */}
      <SafetyModal
        isOpen={isSafetyModalOpen}
        onClose={() => setIsSafetyModalOpen(false)}
        riskLevel={safetyData.riskLevel}
        guidance={safetyData.guidance}
        helplines={safetyData.helplines}
      />
    </div>
  );
}
