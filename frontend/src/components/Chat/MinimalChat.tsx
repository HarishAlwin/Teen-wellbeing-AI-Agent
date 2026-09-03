"use client";

import { useState, useEffect, useRef } from "react";
import { sendMessage, transcribeAudio, synthesizeSpeech, ChatResponse } from "@/lib/api";
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
}

export default function MinimalChat() {
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "welcome-msg",
      role: "assistant",
      content:
        "Hi, I'm Aura. I'm here to listen — about school, friends, family, sleep, whatever's on your mind. What's going on?",
    },
  ]);

  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [textInput, setTextInput] = useState("");
  const [currentTranscript, setCurrentTranscript] = useState("");
  const [userId, setUserId] = useState<string>("");
  const [conversationId, setConversationId] = useState<string>("");
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const [isSafetyModalOpen, setIsSafetyModalOpen] = useState(false);
  const [safetyData, setSafetyData] = useState<{
    riskLevel: "NORMAL" | "CONCERNING" | "HIGH_CONCERN" | "IMMEDIATE_SAFETY";
    guidance?: any;
    helplines?: any;
  }>({ riskLevel: "NORMAL" });

  const speechRecognitionRef = useRef<{ stop: () => void } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const savedUserId = localStorage.getItem("teen_user_id") || "teen-alex-01";
    setUserId(savedUserId);
    localStorage.setItem("teen_user_id", savedUserId);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentTranscript]);

  const processUserMessage = async (userText: string) => {
    if (!userText.trim()) return;

    setConnectionError(null);
    const userMsgId = `msg-${Date.now()}`;
    const newMessages: MessageItem[] = [
      ...messages,
      { id: userMsgId, role: "user", content: userText },
    ];
    setMessages(newMessages);
    setCurrentTranscript("");
    setIsProcessing(true);

    try {
      const resp: ChatResponse = await sendMessage(
        userText,
        userId || "teen-alex-01",
        conversationId || undefined
      );

      if (resp.conversation_id) {
        setConversationId(resp.conversation_id);
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
      };

      setMessages([...newMessages, assistantMsg]);
      setIsProcessing(false);

      // Speak the reply aloud (backend TTS via ElevenLabs, falling back to
      // the browser's built-in speech synthesis if that fails).
      try {
        const audioBlob = await synthesizeSpeech(resp.response_text);
        playSpokenResponse(
          audioBlob,
          resp.response_text,
          () => setIsSpeaking(true),
          () => setIsSpeaking(false)
        );
      } catch {
        playSpokenResponse(
          null,
          resp.response_text,
          () => setIsSpeaking(true),
          () => setIsSpeaking(false)
        );
      }
    } catch (err: any) {
      // Show the REAL error instead of a fabricated "glitch" message, so
      // connection/backend problems are actually debuggable.
      console.error("Error communicating with backend:", err);
      setIsProcessing(false);
      const message = err?.message || "Something went wrong reaching the server.";
      setConnectionError(message);
      setMessages([
        ...newMessages,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content:
            "I'm having trouble connecting right now. Your message wasn't lost — please try sending it again in a moment.",
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
          (liveText) => setCurrentTranscript(liveText),
          (err) => console.warn("Speech recognition notice:", err)
        );
        speechRecognitionRef.current = recognition;
      } catch (err) {
        console.error("Error starting recording (mic permission?):", err);
        setIsRecording(false);
      }
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] max-w-2xl mx-auto w-full">
      {/* Message stream */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "assistant" ? "justify-start" : "justify-end"}`}
          >
            <div
              className={`max-w-[80%] px-4 py-3 rounded-2xl text-[15px] leading-relaxed ${
                msg.role === "assistant"
                  ? "bg-white text-slate-700 rounded-bl-sm shadow-sm border border-slate-100"
                  : "bg-teal-600 text-white rounded-br-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {isProcessing && (
          <div className="flex justify-start">
            <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-white border border-slate-100 shadow-sm">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce"></span>
              </div>
            </div>
          </div>
        )}

        {currentTranscript && (
          <div className="flex justify-end">
            <div className="max-w-[80%] px-4 py-3 rounded-2xl rounded-br-sm bg-teal-600/50 text-white text-[15px] italic">
              {currentTranscript}
            </div>
          </div>
        )}

        {connectionError && (
          <div className="text-center text-xs text-rose-500 bg-rose-50 border border-rose-100 rounded-lg px-3 py-2">
            {connectionError}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="px-4 sm:px-6 py-4 border-t border-slate-100 bg-white/60 backdrop-blur-sm">
        <form onSubmit={handleTextSubmit} className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleToggleRecord}
            disabled={isProcessing}
            aria-label={isRecording ? "Stop voice recording" : "Speak your message"}
            className={`shrink-0 w-11 h-11 rounded-full flex items-center justify-center transition-all ${
              isRecording
                ? "bg-rose-500 text-white animate-pulse"
                : isSpeaking
                ? "bg-teal-100 text-teal-700"
                : "bg-slate-100 text-slate-500 hover:bg-slate-200"
            }`}
          >
            {isRecording ? "⏹" : isSpeaking ? "🔊" : "🎙"}
          </button>

          <input
            ref={inputRef}
            type="text"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            placeholder="Type how you're feeling..."
            disabled={isProcessing}
            className="flex-1 px-4 py-2.5 rounded-full bg-slate-100 border border-transparent focus:border-teal-400 focus:bg-white focus:outline-none text-sm text-slate-700 placeholder:text-slate-400 transition-colors"
          />

          <button
            type="submit"
            disabled={!textInput.trim() || isProcessing}
            className="shrink-0 w-11 h-11 rounded-full bg-teal-600 hover:bg-teal-700 disabled:bg-slate-200 disabled:cursor-not-allowed text-white flex items-center justify-center transition-colors"
            aria-label="Send message"
          >
            ➤
          </button>
        </form>
        <p className="text-center text-[11px] text-slate-400 mt-2.5">
          Aura offers supportive listening, not clinical diagnosis. If you're in danger, call{" "}
          <a href="tel:112" className="underline">112</a>.
        </p>
      </div>

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
