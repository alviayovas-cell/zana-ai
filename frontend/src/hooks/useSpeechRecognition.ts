import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';

export type VoiceState = 'IDLE' | 'LISTENING' | 'PROCESSING' | 'RESPONDING' | 'ERROR';

interface UseSpeechRecognitionProps {
  onTranscript: (text: string) => void;
}

function writeString(view: DataView, offset: number, string: string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

function encodeWAV(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  // RIFF chunk
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, 'WAVE');

  // fmt chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // Linear PCM
  view.setUint16(22, 1, true); // Mono (1 channel)
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // Byte rate
  view.setUint16(32, 2, true); // Block align
  view.setUint16(34, 16, true); // 16 bits per sample

  // data chunk
  writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);

  // Write 16-bit signed PCM
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([view], { type: 'audio/wav' });
}

export function useSpeechRecognition({ onTranscript }: UseSpeechRecognitionProps) {
  const [state, setState] = useState<VoiceState>('IDLE');
  const [interimText, setInterimText] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState<boolean>(true);

  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);
  const inputNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const pcmBuffersRef = useRef<Float32Array[]>([]);

  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  useEffect(() => {
    if (
      !navigator.mediaDevices ||
      !navigator.mediaDevices.getUserMedia ||
      (typeof window.AudioContext === 'undefined' && typeof (window as any).webkitAudioContext === 'undefined')
    ) {
      console.warn('[VOICE] Microphone/AudioContext not supported in this browser.');
      setIsSupported(false);
    } else {
      setIsSupported(true);
    }
  }, []);

  const cleanupAudio = useCallback(() => {
    if (processorNodeRef.current) {
      try {
        processorNodeRef.current.disconnect();
      } catch (_) {}
      processorNodeRef.current = null;
    }
    if (inputNodeRef.current) {
      try {
        inputNodeRef.current.disconnect();
      } catch (_) {}
      inputNodeRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      try {
        audioContextRef.current.close();
      } catch (_) {}
      audioContextRef.current = null;
    }
  }, []);

  const startListening = useCallback(async () => {
    if (!isSupported) {
      setErrorMessage('Audio recording is not supported in this browser.');
      return;
    }

    setErrorMessage(null);
    setInterimText('');
    pcmBuffersRef.current = [];

    try {
      console.log('[VOICE] Requesting microphone access...');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      mediaStreamRef.current = stream;

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      inputNodeRef.current = source;

      // 4096 buffer size, 1 input channel, 1 output channel
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorNodeRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        // Clone samples
        const copy = new Float32Array(inputData.length);
        copy.set(inputData);
        pcmBuffersRef.current.push(copy);
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      console.log('[VOICE] 🔴 Recording started at 16000Hz PCM. Listening...');
      setState('LISTENING');
    } catch (err: any) {
      console.error('[VOICE] Failed to start microphone capture:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setErrorMessage('Microphone permission denied. Please allow microphone access in browser settings.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setErrorMessage('No microphone device found on your computer.');
      } else {
        setErrorMessage(`Microphone error: ${err.message || err.name}`);
      }
      setState('ERROR');
      cleanupAudio();
    }
  }, [isSupported, cleanupAudio]);

  const stopListening = useCallback(async () => {
    console.log('[VOICE] ⏹️ Stop requested. Processing captured audio...');

    const buffers = pcmBuffersRef.current;
    cleanupAudio();

    if (buffers.length === 0) {
      console.warn('[VOICE] No audio buffers recorded.');
      setState('IDLE');
      return;
    }

    // Merge PCM buffers
    let totalLength = 0;
    for (const b of buffers) {
      totalLength += b.length;
    }

    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const b of buffers) {
      merged.set(b, offset);
      offset += b.length;
    }

    // Check if recording is longer than ~0.4s (6400 samples at 16kHz)
    if (totalLength < 6400) {
      console.warn('[VOICE] Audio too short.');
      setErrorMessage('No speech detected. Click the mic and speak your command.');
      setState('IDLE');
      return;
    }

    const wavBlob = encodeWAV(merged, 16000);
    console.log(`[VOICE] Encoded 16kHz WAV: ${wavBlob.size} bytes (${(totalLength / 16000).toFixed(2)}s)`);

    setState('PROCESSING');

    try {
      console.log('[VOICE] Sending WAV audio to backend STT service...');
      const resp = await api.transcribeAudio(wavBlob);
      console.log('[VOICE] STT response:', resp);

      const transcript = resp.transcript?.trim() || '';

      if (transcript) {
        console.log(`[VOICE] ✅ Final transcript: "${transcript}"`);
        console.log('[VOICE] Sending transcript to chat:', transcript);
        onTranscriptRef.current(transcript);
      } else {
        console.log('[VOICE] Empty transcript returned from STT provider.');
        setErrorMessage("Sorry, I couldn't understand that. Please try speaking closer to your mic.");
        setState('IDLE');
      }
    } catch (err: any) {
      console.error('[VOICE] Transcription API error:', err);
      setErrorMessage(err.message || 'Could not transcribe voice audio.');
      setState('ERROR');
    }
  }, [cleanupAudio]);

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
