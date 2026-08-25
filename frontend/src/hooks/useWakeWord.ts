import { useState, useEffect, useCallback, useRef } from 'react';

const WAKE_WORD_STORAGE_KEY = 'zana_wakeword_enabled';

interface UseWakeWordOptions {
  onWakeWordDetected?: () => void;
}

export interface UseWakeWordReturn {
  isListening: boolean;
  isEnabled: boolean;
  isSupported: boolean;
  toggleEnabled: () => void;
}

export function useWakeWord({ onWakeWordDetected }: UseWakeWordOptions = {}): UseWakeWordReturn {
  const SpeechRecognition =
    typeof window !== 'undefined' &&
    ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);

  const isSupported = Boolean(SpeechRecognition);

  const [isEnabled, setIsEnabled] = useState<boolean>(() => {
    try {
      return localStorage.getItem(WAKE_WORD_STORAGE_KEY) !== 'false';
    } catch {
      return true;
    }
  });

  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    try {
      localStorage.setItem(WAKE_WORD_STORAGE_KEY, isEnabled ? 'true' : 'false');
    } catch {}
  }, [isEnabled]);

  const startListening = useCallback(() => {
    if (!isSupported || !isEnabled || recognitionRef.current) return;

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => {
        setIsListening(false);
        recognitionRef.current = null;
        // Auto-restart continuous listening if enabled
        if (isEnabled) {
          setTimeout(() => {
            startListening();
          }, 1000);
        }
      };

      recognition.onresult = (event: any) => {
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript.toLowerCase().trim();
          if (transcript.includes('hey zana') || transcript.includes('hey zana') || transcript.includes('hi zana')) {
            console.log('[WAKE-WORD] Triggered: "Hey Zana"');
            if (onWakeWordDetected) {
              onWakeWordDetected();
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
  }, [isSupported, isEnabled, onWakeWordDetected]);

  useEffect(() => {
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

  return { isListening, isEnabled, isSupported, toggleEnabled };
}
