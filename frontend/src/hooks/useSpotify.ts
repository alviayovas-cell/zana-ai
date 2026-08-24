import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { SpotifyUser, SpotifyPlaybackState } from '../types/spotify';

export function useSpotify() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<SpotifyUser | null>(null);
  const [playback, setPlayback] = useState<SpotifyPlaybackState>({
    is_connected: false,
    is_playing: false,
    track: null,
  });
  const [isLoadingAuth, setIsLoadingAuth] = useState<boolean>(true);

  // Check auth status
  const checkStatus = useCallback(async () => {
    try {
      const res = await api.getSpotifyStatus();
      setIsAuthenticated(res.is_authenticated);
      setUser(res.user);
    } catch (e) {
      console.warn('Failed to check Spotify status:', e);
    } finally {
      setIsLoadingAuth(false);
    }
  }, []);

  // Poll player state
  const refreshPlayer = useCallback(async () => {
    try {
      const state = await api.getSpotifyPlayer();
      setPlayback(state);
    } catch (e) {
      // silent catch for poll errors
    }
  }, []);

  // Login handler
  const loginSpotify = async () => {
    try {
      const { url } = await api.getSpotifyAuthUrl();
      if (url) {
        window.location.href = url;
      }
    } catch (e) {
      console.error('Failed to get Spotify auth url:', e);
    }
  };

  // Playback controls
  const handleControl = async (action: string, params?: { query?: string; volume_percent?: number }) => {
    try {
      await api.controlSpotify(action, params);
      // Quickly refresh player state
      setTimeout(refreshPlayer, 400);
    } catch (e) {
      console.error(`Error controlling Spotify (${action}):`, e);
    }
  };

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  useEffect(() => {
    if (!isAuthenticated) return;
    refreshPlayer();
    const interval = setInterval(refreshPlayer, 3000);
    return () => clearInterval(interval);
  }, [isAuthenticated, refreshPlayer]);

  return {
    isAuthenticated,
    user,
    playback,
    isLoadingAuth,
    loginSpotify,
    refreshPlayer,
    handleControl,
  };
}
