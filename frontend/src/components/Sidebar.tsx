import React from 'react';
import type { SpotifyUser } from '../types/spotify';
import './Sidebar.css';

interface Props {
  isDark: boolean;
  onToggleTheme: () => void;
  spotifyUser: SpotifyUser | null;
  isSpotifyConnected: boolean;
  onConnectSpotify: () => void;
  activeTab: string;
  onSelectTab: (tabId: string) => void;
  ttsEnabled?: boolean;
  onToggleTts?: () => void;
  onOpenProfile?: () => void;
  onOpenReminders?: () => void;
}

const NAV_ITEMS = [
  { id: 'chat', icon: '💬', label: 'Chat', active: true, phase: null },
  { id: 'spotify', icon: '🎵', label: 'Spotify Player', active: true, phase: 'Active' },
  { id: 'voice', icon: '🎤', label: 'Voice Assistant', active: true, phase: 'Active' },
  { id: 'brain', icon: '🧠', label: 'AI Brain', active: true, phase: 'Active' },
];

export const Sidebar: React.FC<Props> = ({
  isDark,
  onToggleTheme,
  spotifyUser,
  isSpotifyConnected,
  onConnectSpotify,
  activeTab,
  onSelectTab,
  ttsEnabled = false,
  onToggleTts,
  onOpenProfile,
  onOpenReminders,
}) => {
  return (
    <aside className="sidebar" role="navigation" aria-label="Main navigation">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="logo-icon" aria-hidden="true">
          <svg viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="16" fill="url(#logoGrad)" />
            <path d="M10 20 Q16 8 22 20" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" fill="none" />
            <circle cx="16" cy="20" r="3" fill="#fff" />
            <defs>
              <linearGradient id="logoGrad" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
                <stop stopColor="#7C3AED" />
                <stop offset="1" stopColor="#1DB954" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div>
          <h1 className="logo-name">Zana</h1>
          <p className="logo-tagline">AI Music Assistant</p>
        </div>
      </div>

      {/* Phase badge */}
      <div className="phase-badge" role="status" aria-label="Current phase">
        <span className="phase-dot" aria-hidden="true" />
        <span className="phase-badge-text">
          Phase 6A · Advanced Assistant Active
        </span>
      </div>

      {/* Spotify Connection Card */}
      <div className={`spotify-card ${isSpotifyConnected ? 'connected' : 'disconnected'}`}>
        <div className="spotify-card-header">
          <div className="spotify-icon-mini">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.48.66.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
            </svg>
          </div>
          <span className="spotify-card-title">Spotify</span>
          <span className="spotify-status-pill">
            {isSpotifyConnected ? 'Linked' : 'Offline'}
          </span>
        </div>

        {isSpotifyConnected && spotifyUser ? (
          <div className="spotify-user-info">
            {spotifyUser.images?.[0]?.url ? (
              <img src={spotifyUser.images[0].url} alt="" className="spotify-avatar" />
            ) : (
              <div className="spotify-avatar-placeholder">
                {spotifyUser.display_name?.charAt(0).toUpperCase() || 'U'}
              </div>
            )}
            <div className="spotify-user-details">
              <span className="spotify-user-name">{spotifyUser.display_name}</span>
              <span className="spotify-plan-tag">{spotifyUser.product || 'Free'} plan</span>
            </div>
          </div>
        ) : (
          <button className="btn-spotify-sidebar-connect" onClick={onConnectSpotify}>
            Connect Account
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <div
            key={item.id}
            id={`nav-item-${item.id}`}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            role="button"
            tabIndex={0}
            onClick={() => onSelectTab(item.id)}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelectTab(item.id)}
            aria-label={item.label + (item.phase ? ` — ${item.phase}` : '')}
            aria-current={activeTab === item.id ? 'page' : undefined}
          >
            <span className="nav-icon" aria-hidden="true">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
            {item.phase && (
              <span className={`nav-phase-tag ${item.phase === 'Active' ? 'tag-active' : ''}`} aria-hidden="true">
                {item.phase}
              </span>
            )}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        {onOpenReminders && (
          <button className="theme-btn tts-sidebar-btn" onClick={onOpenReminders}>
            <span aria-hidden="true">⏰</span> Reminders
          </button>
        )}
        {onOpenProfile && (
          <button className="theme-btn tts-sidebar-btn" onClick={onOpenProfile}>
            <span aria-hidden="true">👤</span> Profile &amp; Settings
          </button>
        )}
        {onToggleTts && (
          <button
            id="sidebar-tts-toggle"
            className={`theme-btn tts-sidebar-btn ${ttsEnabled ? 'tts-sidebar-on' : ''}`}
            onClick={onToggleTts}
            aria-pressed={ttsEnabled}
            aria-label={ttsEnabled ? 'Voice output on — click to disable' : 'Voice output off — click to enable'}
          >
            <span aria-hidden="true">{ttsEnabled ? '🔊' : '🔇'}</span>
            {ttsEnabled ? 'Voice Output On' : 'Voice Output Off'}
          </button>
        )}
        <button
          id="theme-toggle"
          className="theme-btn"
          onClick={onToggleTheme}
          aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          <span aria-hidden="true">{isDark ? '☀️' : '🌙'}</span>
          {isDark ? 'Light mode' : 'Dark mode'}
        </button>
      </div>
    </aside>
  );
};
