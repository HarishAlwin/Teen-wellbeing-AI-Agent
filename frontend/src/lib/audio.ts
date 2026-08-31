/**
 * Audio Recording and Speech Utilities with Hands-Free Conversational Voice Loop
 */

let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];
let activeAudioElement: HTMLAudioElement | null = null;

export async function startRecording(): Promise<MediaStream> {
  audioChunks = [];
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

  // Prefer webm or mp4 audio
  const mimeType = MediaRecorder.isTypeSupported("audio/webm")
    ? "audio/webm"
    : MediaRecorder.isTypeSupported("audio/mp4")
    ? "audio/mp4"
    : "";

  mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
      audioChunks.push(event.data);
    }
  };

  mediaRecorder.start(200);
  return stream;
}

export function stopRecording(): Promise<Blob> {
  return new Promise((resolve) => {
    if (!mediaRecorder) {
      resolve(new Blob());
      return;
    }

    mediaRecorder.onstop = () => {
      const mimeType = mediaRecorder?.mimeType || "audio/webm";
      const audioBlob = new Blob(audioChunks, { type: mimeType });
      // Stop all tracks in the media stream
      if (mediaRecorder?.stream) {
        mediaRecorder.stream.getTracks().forEach((track) => track.stop());
      }
      mediaRecorder = null;
      resolve(audioBlob);
    };

    if (mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
  });
}

/**
 * Native Web Speech API speech recognition with continuous listening
 * and optional silence auto-complete for hands-free speech communication.
 *
 * Parameters:
 *  - onResult: called whenever new transcript is received
 *  - onError: called on non-fatal/fatal errors
 *  - onSpeechPause: called after silenceTimeoutMs of no speech when words were spoken
 *  - silenceTimeoutMs: delay in ms to trigger auto-submit (default: 1800ms)
 */
export function startBrowserSpeechRecognition(
  onResult: (transcript: string, isFinal: boolean) => void,
  onError: (err: any) => void,
  onSpeechPause?: (transcript: string) => void,
  silenceTimeoutMs: number = 1800
): { stop: () => void; getTranscript: () => string; resetTranscript: () => void } | null {
  const SpeechRecognition =
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

  if (!SpeechRecognition) {
    return null;
  }

  let shouldListen = true;
  let committedTranscript = "";
  let currentInterim = "";
  let recognition: any = null;
  let silenceTimer: any = null;

  const resetSilenceTimer = () => {
    if (silenceTimer) {
      clearTimeout(silenceTimer);
      silenceTimer = null;
    }

    const fullText = (committedTranscript + " " + currentInterim).trim();
    if (fullText.length > 0 && onSpeechPause && shouldListen) {
      silenceTimer = setTimeout(() => {
        const textToSubmit = (committedTranscript + " " + currentInterim).trim();
        if (textToSubmit.length > 0 && shouldListen) {
          onSpeechPause(textToSubmit);
        }
      }, silenceTimeoutMs);
    }
  };

  const createAndStart = () => {
    if (!shouldListen) return;

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      let interimTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          committedTranscript += (committedTranscript ? " " : "") + result[0].transcript.trim();
        } else {
          interimTranscript += result[0].transcript;
        }
      }

      currentInterim = interimTranscript;
      const fullTranscript = (committedTranscript + " " + currentInterim).trim();
      onResult(fullTranscript, interimTranscript === "");

      // Reset auto-submit timer on new spoken words
      resetSilenceTimer();
    };

    recognition.onerror = (event: any) => {
      if (event.error === "no-speech") {
        return;
      }
      if (event.error === "aborted") {
        return;
      }
      onError(event.error);
    };

    recognition.onend = () => {
      if (shouldListen) {
        try {
          recognition.start();
        } catch {
          setTimeout(() => {
            if (shouldListen) {
              try { createAndStart(); } catch { /* ignore */ }
            }
          }, 250);
        }
      }
    };

    try {
      recognition.start();
    } catch (e) {
      // ignore already started
    }
  };

  createAndStart();

  return {
    stop: () => {
      shouldListen = false;
      if (silenceTimer) {
        clearTimeout(silenceTimer);
        silenceTimer = null;
      }
      if (recognition) {
        try {
          recognition.stop();
        } catch {
          // ignore
        }
      }
    },
    getTranscript: () => (committedTranscript + " " + currentInterim).trim(),
    resetTranscript: () => {
      committedTranscript = "";
      currentInterim = "";
      if (silenceTimer) {
        clearTimeout(silenceTimer);
        silenceTimer = null;
      }
    },
  };
}

/**
 * Play audio response via Blob or fallback to Web Speech API TTS
 */
export function playSpokenResponse(
  audioBlob: Blob | null,
  fallbackText: string,
  onStart?: () => void,
  onEnd?: () => void
) {
  // Stop existing playback if any
  stopAudioPlayback();

  if (audioBlob && audioBlob.size > 0) {
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    activeAudioElement = audio;

    audio.onplay = () => {
      if (onStart) onStart();
    };

    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      activeAudioElement = null;
      if (onEnd) onEnd();
    };

    audio.onerror = () => {
      speakWithBrowserTTS(fallbackText, onStart, onEnd);
    };

    audio.play().catch(() => {
      speakWithBrowserTTS(fallbackText, onStart, onEnd);
    });
  } else {
    speakWithBrowserTTS(fallbackText, onStart, onEnd);
  }
}

export function speakWithBrowserTTS(
  text: string,
  onStart?: () => void,
  onEnd?: () => void
) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    if (onEnd) onEnd();
    return;
  }

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.98; // Natural conversational cadence
  utterance.pitch = 1.0;
  utterance.lang = "en-US";

  // Pick a warm natural voice if available
  const voices = window.speechSynthesis.getVoices();
  const naturalVoice = voices.find(
    (v) =>
      v.lang.startsWith("en") &&
      (v.name.includes("Natural") ||
        v.name.includes("Google") ||
        v.name.includes("Samantha") ||
        v.name.includes("Karen") ||
        v.name.includes("Jenny"))
  );
  if (naturalVoice) {
    utterance.voice = naturalVoice;
  }

  utterance.onstart = () => {
    if (onStart) onStart();
  };

  utterance.onend = () => {
    if (onEnd) onEnd();
  };

  utterance.onerror = () => {
    if (onEnd) onEnd();
  };

  window.speechSynthesis.speak(utterance);
}

export function stopAudioPlayback() {
  if (activeAudioElement) {
    activeAudioElement.pause();
    activeAudioElement = null;
  }
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}
