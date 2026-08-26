import { useState, useCallback, useRef } from 'react';
import { api } from '../services/api';
import type { ChatMessage, SuggestionItem } from '../types/chat';

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function getSessionId(): string {
  try {
    const existing = localStorage.getItem('zana_session_id');
    if (existing) return existing;
    const sessionId = generateId();
    localStorage.setItem('zana_session_id', sessionId);
    return sessionId;
  } catch {
    return generateId();
  }
}

const WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content: 'Hello! I am **Zana**, your personal AI music assistant. How can I help you today?',
  timestamp: new Date(),
  suggestions: [
    { label: 'What can you do?', action_type: 'help' },
    { label: 'Check status', action_type: 'status' },
    { label: 'Hello Zana', action_type: 'greeting' },
  ],
};

export function useChat(
  onTrackReceived?: (track: any) => void,
  onActionReceived?: (action: string, value?: any) => void,
  onResponseReceived?: (text: string) => void
) {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionIdRef = useRef<string>(getSessionId());


  const appendMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return;

      setError(null);

      const userMessage: ChatMessage = {
        id: generateId(),
        role: 'user',
        content: trimmed,
        timestamp: new Date(),
      };
      appendMessage(userMessage);
      setIsLoading(true);

      try {
        const response = await api.sendMessage({
          message: trimmed,
          session_id: sessionIdRef.current,
        });

        // Persist session id from backend if returned
        if (response.session_id) {
          sessionIdRef.current = response.session_id;
        }

        const assistantMessage: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: response.message,
          timestamp: new Date(response.timestamp),
          suggestions: response.suggestions,
          status: response.status,
          track: response.track,
        };
        appendMessage(assistantMessage);

        // Phase 5.3 — TTS: speak assistant response
        if (onResponseReceived) {
          onResponseReceived(response.message);
        }

        // If backend returned a streaming track, notify player
        if (response.track && onTrackReceived) {
          onTrackReceived(response.track);
        }

        // If backend returned a player action command, notify player
        if (response.action && onActionReceived) {
          onActionReceived(response.action, response.action_value);
        }
      } catch (err) {


        setError('Could not reach the backend. Please make sure the server is running.');
        const errMsg: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: 'I\'m having trouble connecting to the server. Please check that the backend is running on port 8000.',
          timestamp: new Date(),
          status: 'error',
        };
        appendMessage(errMsg);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, appendMessage]
  );

  const handleSuggestion = useCallback(
    (suggestion: SuggestionItem) => {
      sendMessage(suggestion.label);
    },
    [sendMessage]
  );

  return { messages, isLoading, error, sendMessage, handleSuggestion };
}
