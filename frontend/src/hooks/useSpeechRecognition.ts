import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';

export type VoiceState = 'IDLE' | 'LISTENING' | 'PROCESSING' | 'RESPONDING' | 'ERROR';

interface UseSpeechRecognitionProps {
  onTranscript: (text: string) => void;
}

export function useSpeechRecognition({ onTranscript }: UseSpeechRecognitionProps) {
  const [state, setState] = useState<VoiceState>('IDLE');
  const [interimText, setInterimText] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState<boolean>(true);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  // Check support for MediaRecorder & getUserMedia (supported on Brave, Chrome, Edge, Safari, Firefox)
  useEffect(() => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || typeof MediaRecorder === 'undefined') {
      console.warn('[VOICE] MediaRecorder / getUserMedia not supported in this browser.');
      setIsSupported(false);
    } else {
      setIsSupported(true);
    }
  }, []);

  const cleanupStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  const startListening = useCallback(async () => {
    if (!isSupported) {
      setErrorMessage('Audio recording is not supported in this browser.');
      return;
    }

    setErrorMessage(null);
    setInterimText('');
    audioChunksRef.current = [];

    try {
      console.log('[VOICE] Requesting microphone access...');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      streamRef.current = stream;

      // Determine best supported mime type
      let mimeType = 'audio/webm';
      if (!MediaRecorder.isTypeSupported('audio/webm')) {
        if (MediaRecorder.isTypeSupported('audio/mp4')) {
          mimeType = 'audio/mp4';
        } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
          mimeType = 'audio/ogg';
        } else {
          mimeType = '';
        }
      }

      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstart = () => {
        console.log('[VOICE] 🔴 Audio recording started. Listening...');
        setState('LISTENING');
      };

      recorder.onstop = async () => {
        console.log('[VOICE] ⏹️ Recording stopped. Processing audio chunks...');
        cleanupStream();

        const chunks = audioChunksRef.current;
        if (chunks.length === 0) {
          console.warn('[VOICE] No audio data recorded.');
          setState('IDLE');
          return;
        }

        const audioBlob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
        console.log(`[VOICE] Recorded audio blob: ${audioBlob.size} bytes (${audioBlob.type})`);

        if (audioBlob.size < 1000) {
          console.warn('[VOICE] Audio too short / empty.');
          setErrorMessage('No speech detected. Please click the mic and speak your command.');
          setState('IDLE');
          return;
        }

        setState('PROCESSING');

        try {
          console.log('[VOICE] Sending audio to backend transcription API...');
          const resp = await api.transcribeAudio(audioBlob);
          const transcript = resp.transcript?.trim() || '';

          if (transcript) {
            console.log(`[VOICE] ✅ Received transcript: "${transcript}"`);
            onTranscriptRef.current(transcript);
          } else {
            console.log('[VOICE] Empty transcript returned from STT service.');
            setErrorMessage('No speech recognized. Try speaking closer to your microphone.');
            setState('IDLE');
          }
        } catch (err: any) {
          console.error('[VOICE] Transcription API error:', err);
          setErrorMessage(err.message || 'Could not transcribe voice audio.');
          setState('ERROR');
        }
      };

      recorder.onerror = (e: any) => {
        console.error('[VOICE] MediaRecorder error:', e);
        setErrorMessage('Recording error occurred.');
        setState('ERROR');
        cleanupStream();
      };

      recorder.start(250); // Collect slice every 250ms
    } catch (err: any) {
      console.error('[VOICE] Failed to access microphone:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setErrorMessage('Microphone permission denied. Please allow microphone access in Brave/browser settings.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setErrorMessage('No microphone device found on your computer.');
      } else {
        setErrorMessage(`Microphone error: ${err.message || err.name}`);
      }
      setState('ERROR');
      cleanupStream();
    }
  }, [isSupported, cleanupStream]);

  const stopListening = useCallback(() => {
    console.log('[VOICE] Stop recording requested.');
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    } else {
      cleanupStream();
      setState('IDLE');
    }
  }, [cleanupStream]);

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
