export interface SpotifyUser {
  id: string;
  display_name: string;
  email?: string;
  product?: string;
  images?: Array<{ url: string; height?: number; width?: number }>;
  is_authenticated: boolean;
}

export interface SpotifyTrack {
  id?: string;
  name: string;
  artists: string;
  album?: string;
  album_art?: string;
  uri?: string;
  external_url?: string;
  duration_ms?: number;
}

export interface SpotifyPlaybackState {
  is_connected: boolean;
  is_playing: boolean;
  progress_ms?: number;
  duration_ms?: number;
  volume_percent?: number;
  track?: SpotifyTrack | null;
  device?: {
    id?: string;
    name?: string;
    type?: string;
    volume_percent?: number;
  };
  error?: string;
}

export interface SpotifyStatusResponse {
  is_authenticated: boolean;
  user: SpotifyUser | null;
}
