import { useState, useEffect, useRef, useCallback } from 'react';

export type VoiceState = 'IDLE' | 'LISTENING' | 'PROCESSING' | 'RESPONDING' | 'ERROR';

interface UseSpeechRecognitionProps {
  onTranscript: (text: string) => void;
}

export function useSpeechRecognition({ onTranscript }: UseSpeechRecognitionProps) {
  const [state, setState] = useState<VoiceState>('IDLE');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState<boolean>(true);
  const recognitionRef = useRef<any>(null);
  // Store callback in a ref so the SpeechRecognition object does not need to be
  // recreated every time the parent re-renders with a new callback identity.
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
      console.warn('[VOICE] SpeechRecognition API not supported in this browser.');
      return;
    }

    console.log('[VOICE] SpeechRecognition API detected — initializing.');

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      console.log('[VOICE] Listening…');
      setState('LISTENING');
      setErrorMessage(null);
    };

    recognition.onresult = (event: any) => {
      const resultIndex = event.resultIndex;
      const transcript = event.results[resultIndex][0].transcript;
      console.log('[VOICE] Raw transcript:', transcript);
      if (transcript && transcript.trim()) {
        const finalText = transcript.trim();
        console.log('[VOICE] Final transcript:', finalText);
        setState('PROCESSING');
        onTranscriptRef.current(finalText);
      }
    };

    recognition.onerror = (event: any) => {
      console.error('[VOICE] Recognition error:', event.error);
      if (event.error === 'not-allowed') {
        setState('ERROR');
        setErrorMessage('Microphone permission denied. Please allow microphone access.');
      } else if (event.error === 'no-speech') {
        setErrorMessage('No speech detected. Click the mic and try again.');
        setState('IDLE');
      } else if (event.error === 'aborted') {
        // User or system aborted — silently return to idle
        setState('IDLE');
      } else {
        setState('ERROR');
        setErrorMessage(`Voice error: ${event.error}. Please try again.`);
      }
    };

    recognition.onend = () => {
      console.log('[VOICE] Recognition session ended.');
      setState((prev) => {
        // If we just got a result and moved to PROCESSING, keep it there.
        // Otherwise return to IDLE.
        if (prev === 'LISTENING') return 'IDLE';
        if (prev === 'ERROR') return 'IDLE';
        return prev;
      });
    };

    recognitionRef.current = recognition;

    return () => {
      try { recognition.abort(); } catch (_) { /* ignore */ }
    };
  }, []); // ← Empty deps — create recognition once

  const startListening = useCallback(() => {
    if (!isSupported) {
      setErrorMessage('Voice input is not supported in this browser.');
      return;
    }
    setErrorMessage(null);
    try {
      recognitionRef.current?.start();
    } catch (e: any) {
      console.warn('[VOICE] Could not start recognition:', e.message);
    }
  }, [isSupported]);

  const stopListening = useCallback(() => {
    try {
      recognitionRef.current?.stop();
    } catch (_) { /* ignore */ }
    setState('IDLE');
  }, []);

  const resetState = useCallback(() => {
    setState('IDLE');
    setErrorMessage(null);
  }, []);

  return {
    state,
    setState,
    isSupported,
    errorMessage,
    startListening,
    stopListening,
    resetState,
  };
}
