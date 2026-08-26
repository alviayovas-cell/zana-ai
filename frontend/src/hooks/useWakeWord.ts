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

export function useWakeWord({ onWakeWordDetected }: UseWakeWordOptions = {}): UseWakeWordReturn {
  const SpeechRecognition =
    typeof window !== 'undefined' &&
    ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);

  const isSupported = Boolean(SpeechRecognition);

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

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => {
        setIsListening(false);
        recognitionRef.current = null;
        if (isEnabledRef.current) {
          restartTimerRef.current = setTimeout(() => {
            restartTimerRef.current = null;
            startListeningRef.current();
          }, 1000);
        }
      };

      recognition.onresult = (event: any) => {
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript.toLowerCase().trim();
          if (transcript.includes('hey zana') || transcript.includes('hey zana') || transcript.includes('hi zana')) {
            console.log('[WAKE-WORD] Triggered: "Hey Zana"');
            if (onWakeWordDetectedRef.current) {
              onWakeWordDetectedRef.current();
            }
            break;
          }
        }
      };

      recognition.onerror = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
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
