import { useState, useEffect, useCallback, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatWindow } from './components/ChatWindow';
import { ChatInput } from './components/ChatInput';
import { PlayerBar } from './components/PlayerBar';
import { AiBrainPanel } from './components/AiBrainPanel';
import { ProfileModal } from './components/ProfileModal';
import { RemindersModal } from './components/RemindersModal';
import { PermissionModal } from './components/PermissionModal';
import type { PlayerBarRef } from './components/PlayerBar';
import { useChat } from './hooks/useChat';
import { useSpotify } from './hooks/useSpotify';
import { useSpeechSynthesis } from './hooks/useSpeechSynthesis';
import { useWakeWord } from './hooks/useWakeWord';
import { useReminders } from './hooks/useReminders';
import type { TrackPayload } from './types/chat';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('chat');
  const [isDark, setIsDark] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentTrack, setCurrentTrack] = useState<TrackPayload | null>(null);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isRemindersOpen, setIsRemindersOpen] = useState(false);
  const [permissionModal, setPermissionModal] = useState<{
    isOpen: boolean;
    toolName: string;
    prompt: string;
    onConfirm?: () => void;
  }>({ isOpen: false, toolName: '', prompt: '' });

  const playerRef = useRef<PlayerBarRef>(null);

  // Phase 5.3 — Text-to-Speech
  const tts = useSpeechSynthesis();

  // Phase 6A — Reminders
  const { reminders, dueAlerts, createReminder, deleteReminder, dismissAlert } = useReminders();

  const handleTrackReceived = useCallback((track: TrackPayload) => {
    setCurrentTrack(track);
  }, []);

  const handlePlayTrack = useCallback((track: TrackPayload) => {
    setCurrentTrack(track);
  }, []);

  const handleActionReceived = useCallback((action: string, value?: any) => {
    if (!playerRef.current) return;
    if (action === 'pause') {
      playerRef.current.pause();
    } else if (action === 'resume' || action === 'play') {
      playerRef.current.play();
    } else if (action === 'volume') {
      const volNum = typeof value === 'object' && value?.volume_percent ? value.volume_percent / 100 : Number(value) / 100;
      playerRef.current.setVolume(volNum);
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

  // Phase 6A — Wake Word ("Hey Zana")
  const handleWakeWord = useCallback(() => {
    console.log('[WAKE-WORD] Activated by "Hey Zana"');
    if (tts.isEnabled) {
      tts.speak("Yes, I'm listening!");
    }
  }, [tts]);

  const wakeWord = useWakeWord({ onWakeWordDetected: handleWakeWord });

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

  const handlePlayerControl = useCallback(
    (action: string, params?: { query?: string; volume_percent?: number }) => {
      if (action === 'next') {
        sendMessage('Play next song');
      } else if (action === 'previous') {
        sendMessage('Play previous song');
      } else {
        handleControl(action, params);
      }
    },
    [sendMessage, handleControl]
  );

  return (
    <div className="app-shell" id="app-shell">
      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}
      <Sidebar
        isDark={isDark}
        onToggleTheme={toggleTheme}
        spotifyUser={user}
        isSpotifyConnected={isAuthenticated}
        onConnectSpotify={loginSpotify}
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          setSidebarOpen(false);
        }}
        ttsEnabled={tts.isEnabled}
        onToggleTts={tts.toggleEnabled}
        onOpenProfile={() => {
          setIsProfileOpen(true);
          setSidebarOpen(false);
        }}
        onOpenReminders={() => {
          setIsRemindersOpen(true);
          setSidebarOpen(false);
        }}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="chat-area" id="chat-area" role="main" aria-label="Zana AI Application Area">
        {/* Main Header */}
        <header className="chat-header" role="banner">
          <div className="chat-header-info">
            <button
              className="sidebar-toggle-btn"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
            >
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <div className="header-status-dot" aria-hidden="true" />
            <div>
              <h2 className="header-title">Zana</h2>
              <p className="header-subtitle">
                AI Music Assistant · {activeTab === 'brain' ? 'AI Brain Telemetry' : isLoading ? 'Searching music…' : 'Ready'}
              </p>
            </div>
          </div>
          <div className="header-actions">
            {/* Wake word indicator */}
            {wakeWord.isSupported && (
              <span
                className={`connection-badge ${wakeWord.isListening ? 'wakeword-active' : ''}`}
                style={{ cursor: 'pointer' }}
                onClick={wakeWord.toggleEnabled}
                title={wakeWord.isEnabled ? 'Wake Word "Hey Zana" active' : 'Wake Word disabled'}
              >
                <span className="conn-dot" style={{ background: wakeWord.isListening ? '#a78bfa' : '#64748b' }} />
                {wakeWord.isEnabled ? 'Hey Zana: Active' : 'Hey Zana: Off'}
              </span>
            )}
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

        {/* Due Reminders Alert Toasts */}
        {dueAlerts.length > 0 && (
          <div style={{ position: 'absolute', top: '70px', right: '20px', zIndex: 900, display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {dueAlerts.map((alert) => (
              <div
                key={alert.id}
                style={{
                  background: 'linear-gradient(135deg, #7c3aed, #4c1d95)',
                  color: '#fff',
                  padding: '12px 18px',
                  borderRadius: '12px',
                  boxShadow: '0 8px 24px rgba(124, 58, 237, 0.4)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                }}
              >
                <span>⏰ <strong>Reminder:</strong> {alert.message}</span>
                <button
                  style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontWeight: 'bold' }}
                  onClick={() => dismissAlert(alert.id)}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

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
              onPlayTrack={handlePlayTrack}
              currentTrack={currentTrack}
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
        onControl={handlePlayerControl}
        onConnect={loginSpotify}
        isConnected={true}
        isSpeaking={tts.isSpeaking}
      />

      {/* Phase 6A Modals */}
      <ProfileModal
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
        isDark={isDark}
        onToggleTheme={toggleTheme}
        ttsEnabled={tts.isEnabled}
        onToggleTts={tts.toggleEnabled}
        voices={tts.voices}
        selectedVoiceURI={tts.selectedVoiceURI}
        onSelectVoice={tts.setSelectedVoiceURI}
        ttsRate={tts.rate}
        onSetTtsRate={tts.setRate}
        hasSamantha={tts.hasSamantha}
        resolvedVoice={tts.resolvedVoice}
        wakeWordEnabled={wakeWord.isEnabled}
        onToggleWakeWord={wakeWord.setEnabled}
        spotifyUser={user}
        isSpotifyConnected={isAuthenticated}
        onConnectSpotify={loginSpotify}
      />
      <RemindersModal
        isOpen={isRemindersOpen}
        onClose={() => setIsRemindersOpen(false)}
        reminders={reminders}
        onCreateReminder={createReminder}
        onDeleteReminder={deleteReminder}
      />
      <PermissionModal
        isOpen={permissionModal.isOpen}
        toolName={permissionModal.toolName}
        prompt={permissionModal.prompt}
        onConfirm={() => {
          if (permissionModal.onConfirm) permissionModal.onConfirm();
          setPermissionModal({ isOpen: false, toolName: '', prompt: '' });
        }}
        onCancel={() => setPermissionModal({ isOpen: false, toolName: '', prompt: '' })}
      />
    </div>
  );
}
