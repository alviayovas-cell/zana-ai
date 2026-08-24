import { useState, useRef, useCallback, type KeyboardEvent } from 'react';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import type { VoiceState } from '../hooks/useSpeechRecognition';
import './ChatInput.css';

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Track whether this specific chat-loading cycle was triggered by voice
  const voiceTriggeredRef = useRef(false);

  const handleTranscript = useCallback((text: string) => {
    console.log('[VOICE] Sending transcript to chat pipeline:', text);
    voiceTriggeredRef.current = true;
    onSend(text);
  }, [onSend]);

  const {
    state: voiceState,
    isSupported,
    errorMessage,
    startListening,
    stopListening,
    resetState,
  } = useSpeechRecognition({ onTranscript: handleTranscript });

  // Derive the display state: only show "Processing" hint if voice triggered the request
  let displayVoiceState: VoiceState = voiceState;
  if (voiceState === 'PROCESSING' && !disabled) {
    // Backend already responded — reset voice state
    displayVoiceState = 'IDLE';
    voiceTriggeredRef.current = false;
    // Defer reset to avoid calling setState during render
    queueMicrotask(() => resetState());
  }

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    voiceTriggeredRef.current = false; // Text input, not voice
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
    }
  };

  const handleMicClick = () => {
    if (displayVoiceState === 'LISTENING') {
      stopListening();
    } else if (displayVoiceState === 'IDLE' || displayVoiceState === 'ERROR') {
      startListening();
    }
  };

  const canSend = value.trim().length > 0 && !disabled;

  // The mic button should only be disabled when voice is actively processing,
  // NOT when chat is loading from a typed message.
  const isMicDisabled = !isSupported || displayVoiceState === 'PROCESSING';

  // --- Hint & placeholder text ---
  let hintText = 'Press Enter to send · Shift+Enter for new line · 🎤 Click mic for voice';
  let placeholderText = 'Message Zana…';

  if (displayVoiceState === 'LISTENING') {
    hintText = '🔴 Listening… Speak your command now.';
    placeholderText = 'Listening…';
  } else if (displayVoiceState === 'PROCESSING' && voiceTriggeredRef.current) {
    hintText = '⏳ Zana is processing your voice command…';
    placeholderText = 'Processing…';
  } else if (displayVoiceState === 'ERROR' && errorMessage) {
    hintText = `⚠️ ${errorMessage}`;
  } else if (!isSupported) {
    hintText = '⚠️ Voice input is not supported in this browser. Please type your message.';
  }

  return (
    <div className="chat-input-wrapper">
      <div className={`chat-input-box ${disabled ? 'disabled' : ''} ${displayVoiceState === 'LISTENING' ? 'listening' : ''}`}>
        
        {/* Voice Microphone Button */}
        <button
          id="chat-voice-btn"
          className={`mic-btn ${displayVoiceState === 'LISTENING' ? 'listening' : ''} ${!isSupported ? 'unsupported' : ''}`}
          onClick={handleMicClick}
          disabled={isMicDisabled}
          aria-label={displayVoiceState === 'LISTENING' ? 'Stop listening' : 'Start voice input'}
          title={
            !isSupported
              ? 'Voice input not supported in this browser'
              : displayVoiceState === 'LISTENING'
                ? 'Click to stop listening'
                : 'Click to speak a command'
          }
        >
          {displayVoiceState === 'LISTENING' ? (
            /* Stop / cancel icon */
            <svg viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          ) : (
            /* Microphone icon */
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          )}
        </button>

        <textarea
          ref={textareaRef}
          id="chat-input"
          className="chat-textarea"
          placeholder={placeholderText}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          rows={1}
          disabled={disabled || displayVoiceState === 'LISTENING'}
          aria-label="Chat message input"
          aria-describedby="chat-input-hint"
        />

        <button
          id="chat-send-btn"
          className={`send-btn ${canSend ? 'active' : ''}`}
          onClick={handleSend}
          disabled={!canSend}
          aria-label="Send message"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
      <p id="chat-input-hint" className="input-hint">
        {hintText}
      </p>
    </div>
  );
}
