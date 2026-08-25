/**
 * useSpeechSynthesis.ts — Browser Web Speech Synthesis hook for Zana (Phase 5).
 *
 * Features:
 *  - Text-to-speech with enable/disable toggle (default OFF)
 *  - Strip markdown, emojis, code blocks before speaking
 *  - Rate control (0.7 – 1.4)
 *  - Persists enabled state to localStorage
 *  - Exposes isSpeaking state for UI indicators
 */
import { useState, useCallback, useRef, useEffect } from 'react';

const STORAGE_KEY = 'zana_tts_enabled';
const DEFAULT_RATE = 1.0;

// ── Text cleaning ─────────────────────────────────────────────────────────────

function cleanTextForSpeech(text: string): string {
  return text
    // Remove code blocks
    .replace(/```[\s\S]*?```/g, '')
    // Remove inline code
    .replace(/`[^`]*`/g, '')
    // Remove markdown bold / italic
    .replace(/\*{1,3}([^*]+)\*{1,3}/g, '$1')
    // Remove markdown headers
    .replace(/^#{1,6}\s+/gm, '')
    // Remove markdown links [text](url)
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove bullet markers
    .replace(/^[\s]*[-•]\s+/gm, '')
    // Remove emojis
    .replace(/[\u{1F300}-\u{1FFFF}]/gu, '')
    .replace(/[\u2600-\u26FF]/g, '')
    .replace(/[\u2700-\u27BF]/g, '')
    // Remove HTML tags
    .replace(/<[^>]*>/g, '')
    // Collapse multiple whitespace
    .replace(/\s{2,}/g, ' ')
    .trim();
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export interface UseSpeechSynthesisReturn {
  isSpeaking: boolean;
  isEnabled: boolean;
  rate: number;
  isSupported: boolean;
  speak: (text: string) => void;
  stop: () => void;
  toggleEnabled: () => void;
  setRate: (r: number) => void;
}

export function useSpeechSynthesis(): UseSpeechSynthesisReturn {
  const isSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isEnabled, setIsEnabled] = useState<boolean>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true';
    } catch {
      return false;
    }
  });
  const [rate, setRateState] = useState(DEFAULT_RATE);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Persist to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, isEnabled ? 'true' : 'false');
    } catch {}
  }, [isEnabled]);

  const stop = useCallback(() => {
    if (!isSupported) return;
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, [isSupported]);

  const speak = useCallback(
    (text: string) => {
      if (!isSupported || !isEnabled || !text) return;

      // Cancel any current speech
      window.speechSynthesis.cancel();

      const cleaned = cleanTextForSpeech(text);
      if (!cleaned) return;

      const utterance = new SpeechSynthesisUtterance(cleaned);
      utterance.rate = rate;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [isSupported, isEnabled, rate]
  );

  const toggleEnabled = useCallback(() => {
    setIsEnabled((prev) => {
      if (prev) {
        // Turning off — stop any speech
        if (isSupported) window.speechSynthesis.cancel();
        setIsSpeaking(false);
      }
      return !prev;
    });
  }, [isSupported]);

  const setRate = useCallback((r: number) => {
    setRateState(Math.min(Math.max(r, 0.5), 2.0));
  }, []);

  return { isSpeaking, isEnabled, rate, isSupported, speak, stop, toggleEnabled, setRate };
}
