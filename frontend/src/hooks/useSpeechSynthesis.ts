/**
 * useSpeechSynthesis.ts — Browser Web Speech Synthesis hook for Zana.
 *
 * Features:
 *  - Text-to-speech with enable/disable toggle (default OFF)
 *  - High-priority natural female-sounding voice selection with fallback cascade
 *  - Dedicated "Samantha" voice support with automatic cross-platform fallback
 *  - Dynamic voice discovery handling async `voiceschanged` event
 *  - Strip markdown, emojis, code blocks before speaking
 *  - Duplicate speech prevention (guards against React re-render loops)
 *  - Rate & Pitch control
 *  - Persists enabled state, user voice preference, and rate to localStorage
 *  - Exposes isSpeaking state, voices list, and resolved active voice info
 */
import { useState, useCallback, useRef, useEffect, useMemo } from 'react';

const STORAGE_KEY_ENABLED = 'zana_tts_enabled';
const STORAGE_KEY_VOICE = 'zana_tts_voice_uri';
const STORAGE_KEY_RATE = 'zana_tts_rate';
const DEFAULT_RATE = 1.0;

// High-priority natural female patterns
const HIGH_PRIORITY_FEMALE_PATTERNS = [
  // Samantha (macOS / iOS / custom)
  /\bsamantha\b/i,
  // Microsoft Natural / Online voices (Edge / Windows 11)
  /natural.*(jenny|aria|sonia|libby|natasha|clara|neerja|swara|maisie)/i,
  // Google Chrome / Android voices
  /google.*(uk.*female|us.*female|female)/i,
  // Apple macOS / iOS high quality voices
  /(victoria|karen|moira|fiona|tessa|ava|nora|serena|allison|susan)/i,
  // Windows Desktop & Web voices
  /(microsoft zira|microsoft jenny|microsoft aria|microsoft sonia|microsoft libby|microsoft natasha|microsoft clara|microsoft neerja|microsoft swara|microsoft pallavi|microsoft hazel|microsoft heera|microsoft veena)/i,
  // Explicit female keywords
  /\b(female|woman|girl)\b/i,
];

// ── Text cleaning ─────────────────────────────────────────────────────────────

export function cleanTextForSpeech(text: string): string {
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

/**
 * Score a voice for female-sounding quality (higher score = better female voice match).
 */
export function getFemaleVoiceScore(voice: SpeechSynthesisVoice): number {
  const nameAndUri = `${voice.name} ${voice.voiceURI}`.toLowerCase();

  // Explicit male check to avoid false positives
  if (
    /\b(male|david|mark|george|guy|stefan|ravi|hemanth|valluvar|madhav)\b/i.test(nameAndUri) &&
    !/female/i.test(nameAndUri)
  ) {
    return -100;
  }

  for (let i = 0; i < HIGH_PRIORITY_FEMALE_PATTERNS.length; i++) {
    if (HIGH_PRIORITY_FEMALE_PATTERNS[i].test(nameAndUri)) {
      return 100 - i * 10;
    }
  }

  return 0;
}

/**
 * Check if a voice matches the name "Samantha"
 */
export function isSamanthaVoice(voice: SpeechSynthesisVoice): boolean {
  const text = `${voice.name} ${voice.voiceURI}`.toLowerCase();
  return text.includes('samantha');
}

/**
 * Check if any installed voice matches Samantha
 */
export function hasSamanthaVoice(voices: SpeechSynthesisVoice[]): boolean {
  return voices.some((v) => isSamanthaVoice(v));
}

/**
 * Find best voice based on user preference, female priority, language match, and browser fallback.
 */
export function findBestVoice(
  voices: SpeechSynthesisVoice[],
  preferredVoiceURI?: string | null,
  targetLang: string = 'en'
): SpeechSynthesisVoice | null {
  if (!voices || voices.length === 0) return null;

  // Priority 1a: User specifically selected Samantha
  if (preferredVoiceURI && preferredVoiceURI.toLowerCase().includes('samantha')) {
    const samantha = voices.find((v) => isSamanthaVoice(v));
    if (samantha) return samantha;
    // Samantha not installed on device -> proceed to fallback cascade below
  } else if (preferredVoiceURI) {
    // Priority 1b: User selected a specific installed voice
    const exactVoice = voices.find(
      (v) => v.voiceURI === preferredVoiceURI || v.name === preferredVoiceURI
    );
    if (exactVoice) return exactVoice;
  }

  const langCode = (targetLang || 'en').toLowerCase().split(/[-_]/)[0];

  // Priority 2: Best female-sounding voice matching target language
  const langVoices = voices.filter((v) =>
    v.lang.toLowerCase().startsWith(langCode)
  );

  const scoredLangVoices = langVoices
    .map((v) => ({ voice: v, score: getFemaleVoiceScore(v) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score);

  if (scoredLangVoices.length > 0) {
    return scoredLangVoices[0].voice;
  }

  // Priority 2b: If target language has no female voice, check all English female voices
  const englishFemaleVoices = voices
    .filter((v) => v.lang.toLowerCase().startsWith('en'))
    .map((v) => ({ voice: v, score: getFemaleVoiceScore(v) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score);

  if (englishFemaleVoices.length > 0) {
    return englishFemaleVoices[0].voice;
  }

  // Priority 3: Any voice matching target language
  if (langVoices.length > 0) {
    const defaultInLang = langVoices.find((v) => v.default);
    return defaultInLang || langVoices[0];
  }

  // Priority 4: System default voice or first available voice
  const defaultVoice = voices.find((v) => v.default);
  return defaultVoice || voices[0] || null;
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export interface UseSpeechSynthesisReturn {
  isSpeaking: boolean;
  isEnabled: boolean;
  rate: number;
  isSupported: boolean;
  voices: SpeechSynthesisVoice[];
  selectedVoiceURI: string;
  hasSamantha: boolean;
  resolvedVoice: SpeechSynthesisVoice | null;
  speak: (text: string, lang?: string) => void;
  stop: () => void;
  toggleEnabled: () => void;
  setRate: (r: number) => void;
  setSelectedVoiceURI: (voiceURI: string) => void;
}

export function useSpeechSynthesis(): UseSpeechSynthesisReturn {
  const isSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoiceURI, setSelectedVoiceURIState] = useState<string>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY_VOICE) || '';
    } catch {
      return '';
    }
  });
  const [isEnabled, setIsEnabled] = useState<boolean>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY_ENABLED) === 'true';
    } catch {
      return false;
    }
  });
  const [rate, setRateState] = useState<number>(() => {
    try {
      const savedRate = localStorage.getItem(STORAGE_KEY_RATE);
      return savedRate ? parseFloat(savedRate) : DEFAULT_RATE;
    } catch {
      return DEFAULT_RATE;
    }
  });

  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const lastSpokenRef = useRef<{ text: string; timestamp: number } | null>(null);

  // Load and listen for available browser voices
  useEffect(() => {
    if (!isSupported) return;

    const updateVoices = () => {
      try {
        const available = window.speechSynthesis.getVoices();
        if (available && available.length > 0) {
          setVoices(available);
        }
      } catch (err) {
        console.warn('[TTS] Failed to load voices:', err);
      }
    };

    updateVoices();

    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }
    window.speechSynthesis.addEventListener('voiceschanged', updateVoices);

    const timer = setTimeout(updateVoices, 300);

    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', updateVoices);
      clearTimeout(timer);
    };
  }, [isSupported]);

  // Persist enabled state to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_ENABLED, isEnabled ? 'true' : 'false');
    } catch {}
  }, [isEnabled]);

  const hasSamantha = useMemo(() => hasSamanthaVoice(voices), [voices]);

  const resolvedVoice = useMemo(
    () => findBestVoice(voices, selectedVoiceURI, 'en'),
    [voices, selectedVoiceURI]
  );

  const setSelectedVoiceURI = useCallback((voiceURI: string) => {
    setSelectedVoiceURIState(voiceURI);
    try {
      if (voiceURI) {
        localStorage.setItem(STORAGE_KEY_VOICE, voiceURI);
      } else {
        localStorage.removeItem(STORAGE_KEY_VOICE);
      }
    } catch {}
  }, []);

  const setRate = useCallback((r: number) => {
    const clamped = Math.min(Math.max(r, 0.5), 2.0);
    setRateState(clamped);
    try {
      localStorage.setItem(STORAGE_KEY_RATE, String(clamped));
    } catch {}
  }, []);

  const stop = useCallback(() => {
    if (!isSupported) return;
    try {
      window.speechSynthesis.cancel();
    } catch {}
    setIsSpeaking(false);
  }, [isSupported]);

  const speak = useCallback(
    (text: string, lang: string = 'en') => {
      if (!isSupported || !isEnabled || !text) return;

      const cleaned = cleanTextForSpeech(text);
      if (!cleaned) return;

      // Prevent duplicate speech caused by rapid React re-renders or effect re-runs
      const now = Date.now();
      if (
        lastSpokenRef.current &&
        lastSpokenRef.current.text === cleaned &&
        now - lastSpokenRef.current.timestamp < 1200
      ) {
        return;
      }
      lastSpokenRef.current = { text: cleaned, timestamp: now };

      try {
        // Cancel any current speech
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(cleaned);

        // Dynamically query available voices
        const currentVoices = window.speechSynthesis.getVoices();
        const availableVoices = currentVoices.length > 0 ? currentVoices : voices;
        const chosenVoice = findBestVoice(availableVoices, selectedVoiceURI, lang);

        if (chosenVoice) {
          utterance.voice = chosenVoice;
          utterance.lang = chosenVoice.lang;
        } else if (lang) {
          utterance.lang = lang.startsWith('ta') ? 'ta-IN' : lang.startsWith('hi') ? 'hi-IN' : 'en-US';
        }

        utterance.rate = rate;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = (e) => {
          if (e.error !== 'interrupted' && e.error !== 'canceled') {
            console.warn('[TTS] Speech synthesis error:', e.error);
          }
          setIsSpeaking(false);
        };

        utteranceRef.current = utterance;
        window.speechSynthesis.speak(utterance);
      } catch (err) {
        console.error('[TTS] Speech failed safely:', err);
        setIsSpeaking(false);
      }
    },
    [isSupported, isEnabled, rate, selectedVoiceURI, voices]
  );

  const toggleEnabled = useCallback(() => {
    setIsEnabled((prev) => {
      if (prev) {
        // Turning off — stop any active speech
        if (isSupported) {
          try {
            window.speechSynthesis.cancel();
          } catch {}
        }
        setIsSpeaking(false);
      }
      return !prev;
    });
  }, [isSupported]);

  return {
    isSpeaking,
    isEnabled,
    rate,
    isSupported,
    voices,
    selectedVoiceURI,
    hasSamantha,
    resolvedVoice,
    speak,
    stop,
    toggleEnabled,
    setRate,
    setSelectedVoiceURI,
  };
}
