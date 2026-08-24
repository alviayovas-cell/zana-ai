import { useState, useEffect, useRef, useCallback } from 'react';

export type VoiceState = 'IDLE' | 'LISTENING' | 'PROCESSING' | 'RESPONDING' | 'ERROR';

interface UseSpeechRecognitionProps {
  onTranscript: (text: string) => void;
}

export function useSpeechRecognition({ onTranscript }: UseSpeechRecognitionProps) {
  const [state, setState] = useState<VoiceState>('IDLE');
  const [interimText, setInterimText] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState<boolean>(true);
  const recognitionRef = useRef<any>(null);
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  // Track whether the user intentionally wants to be listening.
  // This ref survives across onend restarts.
  const wantListeningRef = useRef(false);
  // Prevent infinite restart loops
  const restartCountRef = useRef(0);
  const maxRestarts = 5;

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

    // ── Key config ──────────────────────────────────────────
    // continuous = true  → keeps listening until we call .stop()
    // interimResults = true → gives live partial transcripts while speaking
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      console.log('[VOICE] Recognition started — listening…');
      restartCountRef.current = 0; // reset restart counter on successful start
      setState('LISTENING');
      setInterimText('');
      setErrorMessage(null);
    };

    recognition.onresult = (event: any) => {
      let interim = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0].transcript;

        if (result.isFinal) {
          finalTranscript += text;
        } else {
          interim += text;
        }
      }

      // Show interim text as live feedback
      if (interim) {
        setInterimText(interim);
        console.log('[VOICE] Interim:', interim);
      }

      // When we get a final transcript, submit it
      if (finalTranscript.trim()) {
        const trimmed = finalTranscript.trim();
        console.log('[VOICE] ✅ Final transcript:', trimmed);
        setInterimText('');
        setState('PROCESSING');
        wantListeningRef.current = false;

        // Stop recognition before submitting (prevents duplicate results)
        try { recognition.stop(); } catch (_) { /* ignore */ }

        onTranscriptRef.current(trimmed);
      }
    };

    recognition.onerror = (event: any) => {
      console.error('[VOICE] Recognition error:', event.error);

      switch (event.error) {
        case 'not-allowed':
          setState('ERROR');
          setErrorMessage('Microphone permission denied. Please allow microphone access in browser settings.');
          wantListeningRef.current = false;
          break;

        case 'no-speech':
          // Browser detected prolonged silence — not a real error.
          // If user still wants to listen, onend will restart it.
          console.log('[VOICE] No speech detected — will auto-restart if still listening.');
          setErrorMessage(null);
          break;

        case 'aborted':
          // User or system aborted — go idle silently
          setState('IDLE');
          setInterimText('');
          break;

        case 'audio-capture':
          setState('ERROR');
          setErrorMessage('No microphone found. Please connect a microphone and try again.');
          wantListeningRef.current = false;
          break;

        case 'network':
          setState('ERROR');
          setErrorMessage('Network error during voice recognition. Check your connection.');
          wantListeningRef.current = false;
          break;

        case 'service-not-allowed':
          setState('ERROR');
          setErrorMessage('Speech recognition service is not allowed. Please try a different browser.');
          wantListeningRef.current = false;
          break;

        default:
          setState('ERROR');
          setErrorMessage(`Voice error: ${event.error}. Please try again.`);
          wantListeningRef.current = false;
          break;
      }
    };

    recognition.onend = () => {
      console.log('[VOICE] Recognition session ended. wantListening:', wantListeningRef.current);

      if (wantListeningRef.current) {
        // The user still wants to listen but the browser ended the session
        // (e.g. due to 'no-speech' timeout). Restart safely.
        restartCountRef.current += 1;

        if (restartCountRef.current <= maxRestarts) {
          console.log(`[VOICE] Auto-restarting (${restartCountRef.current}/${maxRestarts})…`);
          try {
            recognition.start();
          } catch (e: any) {
            console.warn('[VOICE] Restart failed:', e.message);
            setState('IDLE');
            setInterimText('');
            wantListeningRef.current = false;
          }
          return; // Don't change state — onstart will keep LISTENING
        } else {
          console.warn('[VOICE] Max restarts reached. Stopping.');
          setErrorMessage('Voice session timed out. Click the mic to try again.');
          wantListeningRef.current = false;
        }
      }

      // Fall through: return to appropriate state
      setState((prev) => {
        if (prev === 'PROCESSING') return prev; // keep processing state
        return 'IDLE';
      });
      setInterimText('');
    };

    recognitionRef.current = recognition;

    return () => {
      wantListeningRef.current = false;
      try { recognition.abort(); } catch (_) { /* ignore */ }
    };
  }, []); // Empty deps — create recognition once

  const startListening = useCallback(() => {
    if (!isSupported) {
      setErrorMessage('Voice input is not supported in this browser.');
      return;
    }
    setErrorMessage(null);
    setInterimText('');
    restartCountRef.current = 0;
    wantListeningRef.current = true;

    try {
      recognitionRef.current?.start();
      console.log('[VOICE] Start requested by user.');
    } catch (e: any) {
      console.warn('[VOICE] Could not start recognition:', e.message);
      wantListeningRef.current = false;
    }
  }, [isSupported]);

  const stopListening = useCallback(() => {
    console.log('[VOICE] Stop requested by user.');
    wantListeningRef.current = false;
    try {
      recognitionRef.current?.stop();
    } catch (_) { /* ignore */ }
    setState('IDLE');
    setInterimText('');
  }, []);

  const resetState = useCallback(() => {
    setState('IDLE');
    setInterimText('');
    setErrorMessage(null);
  }, []);

  return {
    state,
    setState,
    isSupported,
    errorMessage,
    interimText,
    startListening,
    stopListening,
    resetState,
  };
}
