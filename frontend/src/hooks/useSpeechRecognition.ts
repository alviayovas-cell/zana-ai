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

  useEffect(() => {
    // Check browser compatibility
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setState('LISTENING');
      setErrorMessage(null);
    };

    recognition.onresult = (event: any) => {
      const resultIndex = event.resultIndex;
      const transcript = event.results[resultIndex][0].transcript;
      if (transcript && transcript.trim()) {
        setState('PROCESSING');
        onTranscript(transcript.trim());
      }
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setState('ERROR');
      if (event.error === 'not-allowed') {
        setErrorMessage('Microphone permission denied.');
      } else if (event.error === 'no-speech') {
        setErrorMessage('No speech detected. Please try again.');
        setState('IDLE');
      } else {
        setErrorMessage(`Error: ${event.error}. Please try again.`);
      }
    };

    recognition.onend = () => {
      // Return to IDLE or processing status
      setState((prev) => (prev === 'LISTENING' ? 'IDLE' : prev));
    };

    recognitionRef.current = recognition;
  }, [onTranscript]);

  const startListening = useCallback(() => {
    if (!isSupported) return;
    try {
      if (recognitionRef.current) {
        recognitionRef.current.start();
      }
    } catch (e) {
      console.warn('Recognition already started or error: ', e);
    }
  }, [isSupported]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setState('IDLE');
    }
  }, []);

  return {
    state,
    setState,
    isSupported,
    errorMessage,
    startListening,
    stopListening,
  };
}
