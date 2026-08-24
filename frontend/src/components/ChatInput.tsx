import { useState, useRef, useCallback, useEffect, type KeyboardEvent } from 'react';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import './ChatInput.css';

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleTranscript = useCallback((text: string) => {
    onSend(text);
  }, [onSend]);

  const {
    state: voiceState,
    setState: setVoiceState,
    isSupported,
    errorMessage,
    startListening,
    stopListening,
  } = useSpeechRecognition({ onTranscript: handleTranscript });

  // Sync assistant busy state with voice state
  useEffect(() => {
    if (disabled && voiceState === 'PROCESSING') {
      // Keep it in processing
    } else if (disabled && voiceState === 'IDLE') {
      setVoiceState('PROCESSING');
    } else if (!disabled && (voiceState === 'PROCESSING' || voiceState === 'RESPONDING')) {
      setVoiceState('IDLE');
    }
  }, [disabled, voiceState, setVoiceState]);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
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
    if (voiceState === 'LISTENING') {
      stopListening();
    } else {
      startListening();
    }
  };

  const canSend = value.trim().length > 0 && !disabled;

  // Set message hints based on current voice state
  let hintText = 'Press Enter to send · Shift+Enter for new line';
  let placeholderText = 'Message Zana…';

  if (voiceState === 'LISTENING') {
    hintText = '🔴 Listening… Speak your command now.';
    placeholderText = 'Listening…';
  } else if (voiceState === 'PROCESSING') {
    hintText = '⏳ Zana is processing your request…';
    placeholderText = 'Processing…';
  } else if (errorMessage) {
    hintText = `⚠️ ${errorMessage}`;
  } else if (!isSupported) {
    hintText = '⚠️ Voice input is not supported in this browser. Please type your message.';
  }

  return (
    <div className="chat-input-wrapper">
      <div className={`chat-input-box ${disabled ? 'disabled' : ''} ${voiceState === 'LISTENING' ? 'listening' : ''}`}>
        
        {/* Voice Microphone Button */}
        <button
          id="chat-voice-btn"
          className={`mic-btn ${voiceState === 'LISTENING' ? 'listening' : ''} ${!isSupported ? 'unsupported' : ''}`}
          onClick={handleMicClick}
          disabled={disabled || !isSupported}
          aria-label={voiceState === 'LISTENING' ? 'Stop listening' : 'Start voice input'}
          title={!isSupported ? 'Voice input not supported in this browser' : ''}
        >
          {voiceState === 'LISTENING' ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="16" />
              <line x1="8" y1="12" x2="16" y2="12" />
            </svg>
          ) : (
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
          disabled={disabled || voiceState === 'LISTENING'}
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
