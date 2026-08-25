import type { ChatRequest, ChatResponse, HealthResponse, BrainStatusResponse } from '../types/chat';
import type { SpotifyStatusResponse, SpotifyPlaybackState } from '../types/spotify';

const API_BASE_URL = '';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API error ${res.status}: ${errorText}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  sendMessage: (payload: ChatRequest): Promise<ChatResponse> =>
    apiFetch<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  transcribeAudio: async (audioBlob: Blob): Promise<{ transcript: string }> => {
    const formData = new FormData();
    formData.append('file', audioBlob, 'voice_command.wav');

    const res = await fetch(`${API_BASE_URL}/api/voice/transcribe`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Transcription error ${res.status}: ${errorText}`);
    }

    return res.json() as Promise<{ transcript: string }>;
  },

  getBrainStatus: (): Promise<BrainStatusResponse> =>
    apiFetch<BrainStatusResponse>('/api/brain/status'),

  testBrain: (message: string, session_id?: string): Promise<ChatResponse> =>
    apiFetch<ChatResponse>('/api/brain/test', {
      method: 'POST',
      body: JSON.stringify({ message, session_id }),
    }),

  checkHealth: (): Promise<HealthResponse> =>
    apiFetch<HealthResponse>('/api/health'),

  getSpotifyAuthUrl: (): Promise<{ url: string; is_authenticated: boolean }> =>
    apiFetch<{ url: string; is_authenticated: boolean }>('/api/spotify/auth-url'),

  getSpotifyStatus: (): Promise<SpotifyStatusResponse> =>
    apiFetch<SpotifyStatusResponse>('/api/spotify/status'),

  getSpotifyPlayer: (): Promise<SpotifyPlaybackState> =>
    apiFetch<SpotifyPlaybackState>('/api/spotify/player'),

  controlSpotify: (action: string, params?: { query?: string; item_type?: string; volume_percent?: number }): Promise<{ success: boolean; message: string }> =>
    apiFetch<{ success: boolean; message: string }>('/api/spotify/player/control', {
      method: 'POST',
      body: JSON.stringify({ action, ...params }),
    }),
};
