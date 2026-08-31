"use client";

import { useState, useEffect, useRef } from "react";
import {
  sendMessage,
  transcribeAudio,
  synthesizeSpeech,
  analyzeImageDocument,
  ChatResponse,
  OCRResponse,
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
  ocrDetails?: {
    filename: string;
    documentType: string;
    extractedText: string;
    summary: string;
  };
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
      timestamp: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      content: "All systems online and operational, Boss.",
      emotions: ["active"],
      riskLevel: "NORMAL",
    },
  ]);

  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [continuousMode, setContinuousMode] = useState(true);
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

  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const speechRecognitionRef = useRef<{
    stop: () => void;
    getTranscript: () => string;
    resetTranscript: () => void;
  } | null>(null);

  const isProcessingRef = useRef(false);
  isProcessingRef.current = isProcessing;

  useEffect(() => {
    const savedUserId = localStorage.getItem("teen_user_id") || "teen-alex-01";
    setUserId(savedUserId);
    localStorage.setItem("teen_user_id", savedUserId);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const processUserMessage = async (userText: string) => {
    if (!userText.trim() || isProcessingRef.current) return;

    if (speechRecognitionRef.current) {
      speechRecognitionRef.current.stop();
      speechRecognitionRef.current = null;
    }
    setIsRecording(false);

    const timeString = new Date().toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
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
          () => {
            setIsSpeaking(false);
            if (continuousMode) {
              setTimeout(() => startVoiceListening(), 400);
            }
          }
        );
      } catch (audioErr) {
        playSpokenResponse(
          null,
          resp.response_text,
          () => setIsSpeaking(true),
          () => {
            setIsSpeaking(false);
            if (continuousMode) {
              setTimeout(() => startVoiceListening(), 400);
            }
          }
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
          content: "System error: unable to contact FRIDAY core.",
        },
      ]);
      if (continuousMode) {
        setTimeout(() => startVoiceListening(), 1000);
      }
    }
  };

  const handleImageUpload = async (file: File) => {
    if (!file) return;

    stopAudioPlayback();
    setIsSpeaking(false);
    setIsProcessing(true);

    const timeString = new Date().toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    });

    try {
      const ocrResp: OCRResponse = await analyzeImageDocument(
        file,
        userId || "teen-alex-01",
        conversationId || undefined
      );

      const userMsg: MessageItem = {
        id: `ocr-usr-${Date.now()}`,
        role: "user",
        content: `Uploaded Document: ${file.name}`,
        timestamp: timeString,
        ocrDetails: {
          filename: file.name,
          documentType: ocrResp.ocr_result.document_type,
          extractedText: ocrResp.ocr_result.extracted_text,
          summary: ocrResp.ocr_result.summary,
        },
      };

      const aiMsg: MessageItem = {
        id: `ocr-ai-${Date.now() + 1}`,
        role: "assistant",
        content: ocrResp.ai_companion_reply,
        timestamp: timeString,
        riskLevel: ocrResp.risk_assessment?.proposed_level || "NORMAL",
      };

      setMessages((prev) => [...prev, userMsg, aiMsg]);
      setIsProcessing(false);

      playSpokenResponse(
        null,
        ocrResp.ai_companion_reply,
        () => setIsSpeaking(true),
        () => {
          setIsSpeaking(false);
          if (continuousMode) setTimeout(() => startVoiceListening(), 400);
        }
      );
    } catch (err) {
      console.error("OCR Error:", err);
      setIsProcessing(false);
    }
  };

  const startVoiceListening = async () => {
    stopAudioPlayback();
    setIsSpeaking(false);
    setCurrentTranscript("");

    try {
      await startRecording();
      setIsRecording(true);

      const recognition = startBrowserSpeechRecognition(
        (liveText, _isFinal) => {
          setCurrentTranscript(liveText);
        },
        (err) => console.warn("Speech recognition notice:", err),
        async (finishedTranscript) => {
          if (finishedTranscript.trim().length > 0 && !isProcessingRef.current) {
            await finalizeAndSubmit(finishedTranscript);
          }
        },
        1800
      );
      speechRecognitionRef.current = recognition;
    } catch (err) {
      console.error("Error starting recording:", err);
      setIsRecording(false);
    }
  };

  const finalizeAndSubmit = async (overrideTranscript?: string) => {
    setIsRecording(false);
    setIsProcessing(true);

    if (speechRecognitionRef.current) {
      speechRecognitionRef.current.stop();
      speechRecognitionRef.current = null;
    }

    try {
      const audioBlob = await stopRecording();
      let spokenText = (overrideTranscript || currentTranscript).trim();

      if (!spokenText && audioBlob.size > 0) {
        spokenText = await transcribeAudio(audioBlob);
      }

      if (spokenText) {
        await processUserMessage(spokenText);
      } else {
        setIsProcessing(false);
        if (continuousMode) setTimeout(() => startVoiceListening(), 500);
      }
    } catch (err) {
      console.error("Error finalizing audio:", err);
      setIsProcessing(false);
    }
  };

  const handleToggleRecord = async () => {
    if (isRecording) {
      await finalizeAndSubmit();
    } else {
      await startVoiceListening();
    }
  };

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput.trim() || isProcessing) return;
    const txt = textInput;
    setTextInput("");
    await processUserMessage(txt);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-100px)] font-mono-hud text-[11px] text-cyan-400/80 max-w-7xl mx-auto px-4">
      
      {/* Hidden OCR Input */}
      <input type="file" ref={fileInputRef} accept="image/*,.pdf" className="hidden" onChange={(e) => {
          if (e.target.files && e.target.files[0]) handleImageUpload(e.target.files[0]);
      }} />

      {/* LEFT / CENTER PANEL: Hologram Sphere, Status & Controls */}
      <div className="lg:col-span-5 flex flex-col items-center justify-between border border-cyan-500/30 rounded-2xl bg-[#010e17]/80 p-6 shadow-[0_0_20px_rgba(0,210,255,0.08)] relative">
        
        {/* Status Header */}
        <div className="w-full flex items-center justify-between border-b border-cyan-500/20 pb-3">
          <div className="flex items-center gap-2 font-bold text-cyan-300 tracking-wider">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#00d2ff]"></span>
            FRIDAY // VOICE_CORE
          </div>
          <span className="px-2 py-0.5 border border-cyan-500/40 rounded text-[9px] bg-cyan-950/40 text-cyan-300">
            {isProcessing ? "PROCESSING" : isSpeaking ? "SPEAKING" : isRecording ? "LISTENING" : "STANDBY"}
          </span>
        </div>

        {/* Transmission Status */}
        <div className="w-full max-w-xs rounded-xl border border-cyan-500/20 bg-[#010e17]/60 p-2.5 text-center my-2">
          <div className="text-[9px] text-cyan-500/80 mb-0.5 uppercase tracking-widest">CURRENT PROTOCOL</div>
          <div className="text-xs font-bold text-cyan-100 font-sans tracking-wide">
            {isProcessing ? "ANALYZING UPLINK..." : 
             latestResponse?.risk_level === "IMMEDIATE_SAFETY" ? "CRITICAL PROTOCOL ACTIVE" : 
             latestResponse?.risk_level === "HIGH_CONCERN" ? "SUPPORT ESCALATION ACTIVE" :
             "ALL SYSTEMS ONLINE"}
          </div>
        </div>

        {/* FRIDAY Holographic Sphere */}
        <div 
          onClick={handleToggleRecord}
          className={`plasma-sphere-container ${isRecording ? 'plasma-listening' : isSpeaking ? 'plasma-speaking' : ''} my-4 cursor-pointer`}
          title="Click to speak with FRIDAY"
        >
          <div className="hologram-ring-outer"></div>
          <div className="hologram-ring-inner"></div>
          <div className="hologram-sphere"></div>
        </div>

        {/* Controls & Voice Action Button */}
        <div className="flex flex-col items-center gap-3 w-full">
          <div className="flex items-center gap-4">
            {/* OCR Document Upload Button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-10 h-10 rounded-full flex items-center justify-center border border-cyan-500/30 text-cyan-400 hover:border-cyan-300 hover:bg-cyan-950/40 transition-all"
              title="Upload Notes or Document for OCR Analysis"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </button>

            {/* Mic Toggle Button */}
            <button 
              onClick={handleToggleRecord}
              className={`w-14 h-14 rounded-full flex items-center justify-center border transition-all ${
                isRecording 
                  ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-[0_0_25px_rgba(0,210,255,0.6)] animate-pulse' 
                  : 'bg-transparent border-cyan-500/30 text-cyan-500 hover:border-cyan-400 hover:text-cyan-400 hover:shadow-[0_0_15px_rgba(0,210,255,0.3)]'
              }`}
            >
              {isProcessing ? (
                <div className="spinner spinner-sm border-cyan-400 border-t-transparent" />
              ) : (
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
                </svg>
              )}
            </button>

            {/* Continuous Mode Toggle */}
            <button
              type="button"
              onClick={() => setContinuousMode(!continuousMode)}
              className={`w-10 h-10 rounded-full flex items-center justify-center border transition-all text-[9px] font-bold ${
                continuousMode 
                  ? 'border-cyan-400 bg-cyan-950/60 text-cyan-300' 
                  : 'border-cyan-500/20 text-cyan-600 hover:text-cyan-400'
              }`}
              title={continuousMode ? "Continuous voice stream active" : "Push-to-talk mode"}
            >
              {continuousMode ? "AUTO" : "MAN"}
            </button>
          </div>
          
          <div className="px-4 py-1.5 rounded-full border border-cyan-500/30 bg-cyan-950/40 text-cyan-300 font-bold tracking-widest text-[10px] shadow-[0_0_10px_rgba(0,210,255,0.1)] flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isRecording ? 'bg-cyan-400 animate-pulse' : 'bg-cyan-600'}`}></span>
            {isRecording ? "TRANSCRIBING AUDIO..." : 'CLICK SPHERE OR MIC TO TALK'}
          </div>

          {/* Text Command Input Bar */}
          <form onSubmit={handleTextSubmit} className="w-full flex items-center gap-2 mt-2">
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Type message or command..."
              disabled={isProcessing}
              className="flex-1 bg-cyan-950/30 border border-cyan-500/30 rounded-xl px-3.5 py-2 text-cyan-100 text-xs font-sans placeholder-cyan-600/60 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition-all"
            />
            <button
              type="submit"
              disabled={isProcessing || !textInput.trim()}
              className="px-3.5 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 disabled:opacity-30 disabled:hover:bg-cyan-500/20 text-cyan-300 rounded-xl font-bold transition-all text-xs"
            >
              SEND
            </button>
          </form>
        </div>
      </div>

      {/* RIGHT PANEL: Terminal Feed & Chat Stream */}
      <div className="lg:col-span-7 border border-cyan-500/30 rounded-2xl bg-[#010e17]/80 flex flex-col shadow-[0_0_20px_rgba(0,210,255,0.08)] overflow-hidden">
        
        {/* Terminal Header */}
        <div className="flex items-center justify-between p-3.5 border-b border-cyan-500/30 bg-cyan-950/20">
          <div className="flex items-center gap-2 font-bold text-cyan-300">
            <span className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#00d2ff] animate-pulse"></span>
            FRIDAY // TERMINAL_FEED
          </div>
          <span className="text-cyan-500 text-[9px] tracking-widest">LIVE_LOGS</span>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
          {messages.map((msg) => {
            const isAI = msg.role === "assistant";
            return (
              <div key={msg.id} className={`border rounded-xl p-3.5 ${isAI ? 'border-cyan-500/30 bg-cyan-950/20' : 'border-slate-700/50 bg-slate-900/30'}`}>
                <div className="flex justify-between items-center text-[9px] font-bold mb-1.5 text-cyan-500 tracking-widest">
                  <span className="flex items-center gap-1.5">
                    {isAI ? <span className="text-cyan-300 font-bold">✦ FRIDAY_AI</span> : <span className="text-slate-400">&gt; USER_COMMAND</span>}
                  </span>
                  <span className="text-cyan-600/70">{msg.timestamp}</span>
                </div>
                <div className={`font-sans text-xs ${isAI ? 'text-cyan-100' : 'text-slate-200'} leading-relaxed`}>
                  {msg.content}
                </div>
                
                {msg.ocrDetails && (
                  <div className="mt-2.5 p-2.5 border border-cyan-500/30 bg-cyan-950/40 rounded-lg">
                    <div className="text-cyan-300 text-[10px] font-bold mb-1">DOCUMENT OCR: {msg.ocrDetails.documentType.toUpperCase()}</div>
                    <div className="font-sans text-cyan-200/70 italic line-clamp-3">"{msg.ocrDetails.extractedText}"</div>
                  </div>
                )}
                
                {msg.intervention && (
                  <div className={`mt-2.5 p-2.5 rounded-lg border ${
                    msg.riskLevel === "IMMEDIATE_SAFETY" || msg.riskLevel === "HIGH_CONCERN"
                      ? "border-rose-500/40 bg-rose-950/40 text-rose-300 shadow-[0_0_10px_rgba(244,63,94,0.15)]"
                      : "border-cyan-500/30 bg-cyan-950/30 text-cyan-200 shadow-[0_0_10px_rgba(0,210,255,0.05)]"
                  }`}>
                    <div className="text-[10px] font-bold mb-1 flex items-center gap-1.5">
                      {msg.riskLevel === "IMMEDIATE_SAFETY" || msg.riskLevel === "HIGH_CONCERN" ? (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-ping"></span>
                          <span className="text-rose-400">CRITICAL SAFETY PROTOCOL:</span>
                        </>
                      ) : (
                        <>
                          <span className="text-cyan-400">💡 SUGGESTION:</span>
                        </>
                      )}
                      <span>{msg.intervention.title}</span>
                    </div>
                    <div className="font-sans leading-tight text-xs opacity-90">{msg.intervention.content}</div>
                  </div>
                )}
              </div>
            );
          })}
          {currentTranscript && (
            <div className="border border-cyan-500/20 rounded-xl p-3 bg-cyan-950/20 opacity-80 animate-pulse">
              <div className="flex justify-between items-center text-[9px] font-bold mb-1 text-cyan-400 tracking-widest">
                <span>&gt; LIVE_TRANSCRIPT</span>
              </div>
              <div className="font-sans text-xs text-cyan-200 leading-relaxed italic">
                "{currentTranscript}"
              </div>
            </div>
          )}
          <div ref={messagesEndRef}></div>
        </div>

        {/* Terminal Footer */}
        <div className="p-2.5 border-t border-cyan-500/30 text-center text-[9px] text-cyan-600/60 tracking-[0.3em] bg-[#010e17]">
          --- ENCRYPTED TRANSMISSION STREAM ---
        </div>
      </div>
      
      {/* Safety Protocol Modal */}
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

