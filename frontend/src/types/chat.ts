export interface SuggestionItem {
  label: string;
  action_type: string;
  payload?: string | null;
}

export interface ChatRequest {
  message: string;
  session_id?: string | null;
}

export interface TrackPayload {
  id?: string | null;
  title: string;
  artist: string;
  album_art?: string | null;
  audio_url?: string | null;
  duration?: number | null;
  webpage_url?: string | null;
}

export interface ChatResponse {
  message: string;
  status: string;
  timestamp: string;
  session_id?: string | null;
  suggestions?: SuggestionItem[] | null;
  track?: TrackPayload | null;
  action?: string | null;
  action_value?: any;
  intent?: string | null;
  confidence?: number | null;
  tool?: string | null;
  arguments?: Record<string, any> | null;
  execution_status?: string | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  suggestions?: SuggestionItem[] | null;
  status?: string;
  track?: TrackPayload | null;
  intent?: string | null;
  confidence?: number | null;
  tool?: string | null;
  arguments?: Record<string, any> | null;
  execution_status?: string | null;
}

export interface BrainStatusResponse {
  status: string;
  architecture: string;
  modules: Record<string, boolean>;
  active_sessions: number;
  llm_configured: boolean;
  provider: string;
  model: string;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  environment: string;
  timestamp: string;
}
