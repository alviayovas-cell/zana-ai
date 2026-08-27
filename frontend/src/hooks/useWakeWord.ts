import { useState, useEffect, useCallback, useRef } from 'react';

const WAKE_WORD_STORAGE_KEY = 'zana_wakeword_enabled_v2';

interface UseWakeWordOptions {
  onWakeWordDetected?: () => void;
}

export interface UseWakeWordReturn {
  isListening: boolean;
  isEnabled: boolean;
  isSupported: boolean;
  toggleEnabled: () => void;
  setEnabled: (enabled: boolean) => void;
}

/**
 * Continuous SpeechRecognition is unreliable on mobile browsers: it ends
 * immediately after starting, which turns the auto-restart into a rapid
 * on/off loop that flickers the mic indicator and drains the battery.
 * Wake word is therefore only offered on non-touch desktop browsers.
 */
function isMobileBrowser(): boolean {
  if (typeof navigator === 'undefined') return false;
  const ua = navigator.userAgent || '';
  const coarsePointer =
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(pointer: coarse)').matches;
  return /Android|iPhone|iPad|iPod|Mobile|Windows Phone/i.test(ua) || coarsePointer;
}

export function useWakeWord({ onWakeWordDetected }: UseWakeWordOptions = {}): UseWakeWordReturn {
  const SpeechRecognition =
    typeof window !== 'undefined' &&
    ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);

  const isSupported = Boolean(SpeechRecognition) && !isMobileBrowser();

  const [isEnabled, setIsEnabled] = useState<boolean>(() => {
    try {
      return localStorage.getItem(WAKE_WORD_STORAGE_KEY) === 'true';
    } catch {
      return false;
    }
  });

  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isEnabledRef = useRef(isEnabled);
  const onWakeWordDetectedRef = useRef(onWakeWordDetected);
  const startListeningRef = useRef<() => void>(() => {});
  const consecutiveFailuresRef = useRef(0);
  const lastStartRef = useRef(0);

  useEffect(() => {
    try {
      localStorage.setItem(WAKE_WORD_STORAGE_KEY, isEnabled ? 'true' : 'false');
    } catch {}
  }, [isEnabled]);

  const startListening = useCallback(() => {
    if (!isSupported || !isEnabledRef.current || recognitionRef.current) return;

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      lastStartRef.current = Date.now();

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => {
        setIsListening(false);
        recognitionRef.current = null;
        if (!isEnabledRef.current) return;

        // If the session ended almost immediately, the browser is rejecting
        // continuous mode (common on mobile). Back off, and give up after a
        // few failures so the mic indicator doesn't flicker forever.
        const ranBriefly = Date.now() - lastStartRef.current < 700;
        consecutiveFailuresRef.current = ranBriefly
          ? consecutiveFailuresRef.current + 1
          : 0;

        if (consecutiveFailuresRef.current >= 4) {
          console.warn('[WAKE-WORD] Disabled — continuous recognition unavailable here.');
          setIsEnabled(false);
          return;
        }

        const delay = ranBriefly ? 2000 : 800;
        restartTimerRef.current = setTimeout(() => {
          restartTimerRef.current = null;
          startListeningRef.current();
        }, delay);
      };

      recognition.onresult = (event: any) => {
        consecutiveFailuresRef.current = 0;
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript.toLowerCase().trim();
          if (transcript.includes('hey zana') || transcript.includes('hi zana')) {
            console.log('[WAKE-WORD] Triggered: "Hey Zana"');
            if (onWakeWordDetectedRef.current) {
              onWakeWordDetectedRef.current();
            }
            break;
          }
        }
      };

      recognition.onerror = (event: any) => {
        setIsListening(false);
        const err = event?.error;
        // Permission / service errors will never recover — stop entirely.
        if (err === 'not-allowed' || err === 'service-not-allowed') {
          console.warn('[WAKE-WORD] Microphone permission denied — disabling wake word.');
          if (restartTimerRef.current) {
            clearTimeout(restartTimerRef.current);
            restartTimerRef.current = null;
          }
          setIsEnabled(false);
        }
      };

      recognitionRef.current = recognition;
      try {
        recognition.start();
      } catch (startErr) {
        // "already started" — drop this instance and let onend/cleanup recover
        console.warn('[WAKE-WORD] start() threw, resetting:', startErr);
        recognitionRef.current = null;
        setIsListening(false);
      }
    } catch (err) {
      console.warn('[WAKE-WORD] Start warning:', err);
      setIsListening(false);
    }
  }, [isSupported, SpeechRecognition]);

  useEffect(() => {
    isEnabledRef.current = isEnabled;
    onWakeWordDetectedRef.current = onWakeWordDetected;
    startListeningRef.current = startListening;
  }, [isEnabled, onWakeWordDetected, startListening]);

  useEffect(() => {
    isEnabledRef.current = isEnabled;
    if (isEnabled && isSupported) {
      startListening();
    } else if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
      setIsListening(false);
    }

    return () => {
      if (restartTimerRef.current) {
        clearTimeout(restartTimerRef.current);
        restartTimerRef.current = null;
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
        recognitionRef.current = null;
      }
    };
  }, [isEnabled, isSupported, startListening]);

  const toggleEnabled = useCallback(() => {
    setIsEnabled((prev) => !prev);
  }, []);

  const setEnabled = useCallback((enabled: boolean) => {
    setIsEnabled(enabled);
  }, []);

  return { isListening, isEnabled, isSupported, toggleEnabled, setEnabled };
}
