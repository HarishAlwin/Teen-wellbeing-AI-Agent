/**
 * Audio Recording and Speech Utilities
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
 * Native Web Speech API speech recognition for instant, low-latency live STT.
 *
 * Previously this used `continuous = false`, which made the browser stop
 * listening after the first short pause in speech (~3-4 seconds) — that was
 * the root cause of "STT only transcribes for 3-4 seconds and doesn't
 * continue." Fixed by:
 *  1. Setting `continuous = true` so it doesn't stop on short pauses.
 *  2. Accumulating the FINAL transcript across multiple result events,
 *     since continuous mode fires many onresult events over a session
 *     rather than one.
 *  3. Auto-restarting recognition in `onend` if the user hasn't manually
 *     stopped yet — some browsers (notably Chrome) still end a continuous
 *     session after a long silence or ~60s even with continuous=true, so
 *     auto-restart is what makes this reliably keep going until the user
 *     taps stop.
 */
export function startBrowserSpeechRecognition(
  onResult: (transcript: string) => void,
  onError: (err: any) => void
): { stop: () => void } | null {
  const SpeechRecognition =
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

  if (!SpeechRecognition) {
    return null;
  }

  let manuallyStopped = false;
  let finalTranscript = "";

  const recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "en-US";

  recognition.onresult = (event: any) => {
    let interimTranscript = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const chunk = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += chunk + " ";
      } else {
        interimTranscript += chunk;
      }
    }
    onResult((finalTranscript + interimTranscript).trim());
  };

  recognition.onerror = (event: any) => {
    // "no-speech" fires often in continuous mode during natural pauses —
    // it isn't a real error, so don't bubble it up or it'll look like a
    // failure on every pause between sentences.
    if (event.error !== "no-speech") {
      onError(event.error);
    }
  };

  recognition.onend = () => {
    // If the session ended on its own (browser timeout/silence) but the
    // user hasn't tapped stop yet, restart it transparently so the
    // teenager can keep talking without the mic silently going dead.
    if (!manuallyStopped) {
      try {
        recognition.start();
      } catch (e) {
        // Already running or briefly unavailable — safe to ignore.
      }
    }
  };

  recognition.start();

  return {
    stop: () => {
      manuallyStopped = true;
      try {
        recognition.stop();
      } catch (e) {
        // ignore
      }
    }
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
      // Fallback to browser synthesis on audio error
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
  utterance.rate = 0.95; // Slightly slower, calming pace
  utterance.pitch = 1.0;
  utterance.lang = "en-US";

  // Pick a warm voice if available
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
