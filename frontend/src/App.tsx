import { useState, useEffect, useCallback, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatWindow } from './components/ChatWindow';
import { ChatInput } from './components/ChatInput';
import { PlayerBar } from './components/PlayerBar';
import { AiBrainPanel } from './components/AiBrainPanel';
import type { PlayerBarRef } from './components/PlayerBar';
import { useChat } from './hooks/useChat';
import { useSpotify } from './hooks/useSpotify';
import { useSpeechSynthesis } from './hooks/useSpeechSynthesis';
import type { TrackPayload } from './types/chat';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('chat');
  const [isDark, setIsDark] = useState(true);
  const [currentTrack, setCurrentTrack] = useState<TrackPayload | null>(null);
  const playerRef = useRef<PlayerBarRef>(null);

  // Phase 5.3 — Text-to-Speech
  const tts = useSpeechSynthesis();

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

  // TTS callback: speak after assistant messages are received
  const handleResponseReceived = useCallback(
    (text: string) => {
      if (tts.isEnabled && text) {
        tts.speak(text);
      }
    },
    [tts]
  );

  const { messages, isLoading, sendMessage, handleSuggestion } = useChat(
    handleTrackReceived,
    handleActionReceived,
    handleResponseReceived
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
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        ttsEnabled={tts.isEnabled}
        onToggleTts={tts.toggleEnabled}
      />

      <main className="chat-area" id="chat-area" role="main" aria-label="Zana AI Application Area">
        {/* Main Header */}
        <header className="chat-header" role="banner">
          <div className="chat-header-info">
            <div className="header-status-dot" aria-hidden="true" />
            <div>
              <h2 className="header-title">Zana</h2>
              <p className="header-subtitle">
                AI Music Assistant · {activeTab === 'brain' ? 'AI Brain Telemetry' : isLoading ? 'Searching music…' : 'Ready'}
              </p>
            </div>
          </div>
          <div className="header-actions">
            {/* TTS Toggle Button */}
            {tts.isSupported && (
              <button
                id="tts-toggle-btn"
                className={`tts-toggle-btn ${tts.isEnabled ? 'tts-on' : 'tts-off'}`}
                onClick={tts.toggleEnabled}
                title={tts.isEnabled ? 'Voice Output ON — click to disable' : 'Voice Output OFF — click to enable'}
                aria-pressed={tts.isEnabled}
                aria-label="Toggle voice output"
              >
                {tts.isSpeaking ? (
                  <span className="tts-speaking-indicator">
                    <span className="tts-wave" />
                    <span className="tts-wave" />
                    <span className="tts-wave" />
                  </span>
                ) : (
                  <span>{tts.isEnabled ? '🔊' : '🔇'}</span>
                )}
                <span className="tts-btn-label">{tts.isEnabled ? 'Voice On' : 'Voice Off'}</span>
              </button>
            )}
            {/* Stop Speaking Button */}
            {tts.isSupported && tts.isSpeaking && (
              <button
                id="tts-stop-btn"
                className="tts-stop-btn"
                onClick={tts.stop}
                title="Stop speaking"
                aria-label="Stop voice output"
              >
                ⏹ Stop
              </button>
            )}
            <div className="connection-badge" role="status" aria-label="AI Engine status">
              <span className="conn-dot" aria-hidden="true" />
              {activeTab === 'brain' ? 'AI Brain Orchestration Active' : 'Free Audio Engine Active'}
            </div>
          </div>
        </header>

        {/* View Switcher */}
        {activeTab === 'brain' ? (
          <AiBrainPanel onSendMessage={sendMessage} />
        ) : (
          <>
            {/* Messages */}
            <ChatWindow
              messages={messages}
              isLoading={isLoading}
              onSuggestion={handleSuggestion}
            />

            {/* Input (Text + Voice) */}
            <ChatInput onSend={sendMessage} disabled={isLoading} />
          </>
        )}
      </main>

      {/* Floating Bottom Music Player — Always available across all tabs */}
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
