import { useRef, useEffect } from 'react';
import type { ChatMessage } from '../types/chat';
import type { SuggestionItem } from '../types/chat';
import { SuggestionChips } from './SuggestionChips';
import './ChatWindow.css';

interface Props {
  messages: ChatMessage[];
  isLoading: boolean;
  onSuggestion: (s: SuggestionItem) => void;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/** Very light markdown renderer: bold and newlines only */
function renderContent(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part.split('\n').map((line, j, arr) => (
      <span key={`${i}-${j}`}>
        {line}
        {j < arr.length - 1 && <br />}
      </span>
    ));
  });
}

export function ChatWindow({ messages, isLoading, onSuggestion }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-window" role="log" aria-live="polite" aria-label="Chat messages">
      {messages.map((msg) => (
        <div key={msg.id} className={`message-row ${msg.role}`}>
          {msg.role === 'assistant' && (
            <div className="avatar" aria-hidden="true">
              <span>Z</span>
            </div>
          )}

          <div className="bubble-group">
            <div
              className={`bubble ${msg.role} ${msg.status === 'error' ? 'error' : ''}`}
              role="article"
              aria-label={`${msg.role === 'user' ? 'You' : 'Zana'}: ${msg.content}`}
            >
              <p className="bubble-text">{renderContent(msg.content)}</p>
              <span className="bubble-time">{formatTime(msg.timestamp)}</span>
            </div>

            {msg.role === 'assistant' && msg.suggestions && msg.suggestions.length > 0 && (
              <SuggestionChips
                suggestions={msg.suggestions}
                onSelect={onSuggestion}
                disabled={isLoading}
              />
            )}
          </div>

          {msg.role === 'user' && (
            <div className="avatar user-avatar" aria-hidden="true">
              <span>U</span>
            </div>
          )}
        </div>
      ))}

      {isLoading && (
        <div className="message-row assistant" role="status" aria-label="Zana is typing">
          <div className="avatar" aria-hidden="true">
            <span>Z</span>
          </div>
          <div className="bubble assistant typing-bubble">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
