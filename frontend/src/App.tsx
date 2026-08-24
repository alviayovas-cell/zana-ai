import { useState, useEffect, useCallback, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatWindow } from './components/ChatWindow';
import { ChatInput } from './components/ChatInput';
import { PlayerBar } from './components/PlayerBar';
import type { PlayerBarRef } from './components/PlayerBar';
import { useChat } from './hooks/useChat';
import { useSpotify } from './hooks/useSpotify';
import type { TrackPayload } from './types/chat';
import './App.css';

export default function App() {
  const [isDark, setIsDark] = useState(true);
  const [currentTrack, setCurrentTrack] = useState<TrackPayload | null>(null);
  const playerRef = useRef<PlayerBarRef>(null);

  const handleTrackReceived = useCallback((track: TrackPayload) => {
    setCurrentTrack(track);
  }, []);

  const handleActionReceived = useCallback((action: string, value?: any) => {
    if (!playerRef.current) return;
    if (action === 'pause') {
      playerRef.current.pause();
    } else if (action === 'resume') {
      playerRef.current.play();
    } else if (action === 'volume') {
      playerRef.current.setVolume(Number(value));
    } else if (action === 'seek') {
      playerRef.current.seek(Number(value));
    }
  }, []);

  const { messages, isLoading, sendMessage, handleSuggestion } = useChat(
    handleTrackReceived,
    handleActionReceived
  );

  const {
    isAuthenticated,
    user,
    playback,
    loginSpotify,
    handleControl,
    refreshPlayer,
  } = useSpotify();

  // Listen for Spotify OAuth return redirect
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('spotify') === 'connected') {
      window.history.replaceState({}, document.title, window.location.pathname);
      refreshPlayer();
    }
  }, [refreshPlayer]);

  const toggleTheme = () => {
    setIsDark((prev) => {
      const next = !prev;
      document.documentElement.setAttribute('data-theme', next ? 'dark' : 'light');
      return next;
    });
  };

  return (
    <div className="app-shell" id="app-shell">
      <Sidebar
        isDark={isDark}
        onToggleTheme={toggleTheme}
        spotifyUser={user}
        isSpotifyConnected={isAuthenticated}
        onConnectSpotify={loginSpotify}
      />

      <main className="chat-area" id="chat-area" role="main" aria-label="Chat with Zana">
        {/* Header */}
        <header className="chat-header" role="banner">
          <div className="chat-header-info">
            <div className="header-status-dot" aria-hidden="true" />
            <div>
              <h2 className="header-title">Zana</h2>
              <p className="header-subtitle">
                AI Music Assistant · {isLoading ? 'Searching music…' : 'Ready'}
              </p>
            </div>
          </div>
          <div className="header-actions">
            <div className="connection-badge" role="status" aria-label="Audio engine status">
              <span className="conn-dot" aria-hidden="true" />
              Free Audio Engine Active
            </div>
          </div>
        </header>

        {/* Messages */}
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onSuggestion={handleSuggestion}
        />

        {/* Input */}
        <ChatInput onSend={sendMessage} disabled={isLoading} />
      </main>

      {/* Floating Bottom Music Player */}
      <PlayerBar
        ref={playerRef}
        playback={playback}
        activeTrack={currentTrack}
        onControl={handleControl}
        onConnect={loginSpotify}
        isConnected={true}
      />
    </div>
  );
}
