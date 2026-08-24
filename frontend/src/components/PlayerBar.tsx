import React, { useRef, useState, useEffect, useImperativeHandle, forwardRef } from 'react';
import type { SpotifyPlaybackState } from '../types/spotify';
import type { TrackPayload } from '../types/chat';
import './PlayerBar.css';

interface PlayerBarProps {
  playback: SpotifyPlaybackState;
  activeTrack: TrackPayload | null;
  onControl: (action: string, params?: { query?: string; volume_percent?: number }) => void;
  onConnect?: () => void;
  isConnected?: boolean;
}

export interface PlayerBarRef {
  play: () => void;
  pause: () => void;
  setVolume: (val: number) => void;
  seek: (val: number) => void;
}

function formatTime(seconds?: number): string {
  if (!seconds || isNaN(seconds)) return '0:00';
  const totalSeconds = Math.floor(seconds);
  const minutes = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${minutes}:${secs < 10 ? '0' : ''}${secs}`;
}

export const PlayerBar = forwardRef<PlayerBarRef, PlayerBarProps>(({
  playback,
  activeTrack,
  onControl,
}, ref) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [volume, setVolume] = useState<number>(0.8);

  // Expose play/pause/volume controls to parent component
  useImperativeHandle(ref, () => ({
    play: () => {
      if (audioRef.current) {
        audioRef.current.play().then(() => setIsPlaying(true)).catch(console.error);
      }
    },
    pause: () => {
      if (audioRef.current) {
        audioRef.current.pause();
        setIsPlaying(false);
      }
    },
    setVolume: (val: number) => {
      const clamped = Math.max(0, Math.min(1, val));
      setVolume(clamped);
      if (audioRef.current) {
        audioRef.current.volume = clamped;
      }
    },
    seek: (val: number) => {
      if (audioRef.current) {
        audioRef.current.currentTime = val;
        setCurrentTime(val);
      }
    }
  }));

  // When a new track is passed from chat
  useEffect(() => {
    if (activeTrack?.audio_url && audioRef.current) {
      audioRef.current.src = activeTrack.audio_url;
      audioRef.current.volume = volume;
      audioRef.current.play().then(() => {
        setIsPlaying(true);
      }).catch((err) => {
        console.warn('Autoplay error:', err);
      });
    }
  }, [activeTrack]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
      onControl('pause');
    } else {
      audioRef.current.play().then(() => {
        setIsPlaying(true);
        onControl('resume');
      }).catch(console.error);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      setDuration(audioRef.current.duration || 0);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const targetTime = Number(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = targetTime;
      setCurrentTime(targetTime);
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const vol = Number(e.target.value);
    setVolume(vol);
    if (audioRef.current) {
      audioRef.current.volume = vol;
    }
    onControl('volume', { volume_percent: Math.round(vol * 100) });
  };

  // Determine current active display data
  const currentTitle = activeTrack?.title || playback.track?.name || 'No track playing';
  const currentArtist = activeTrack?.artist || playback.track?.artists || 'Ask Zana to play any song!';
  const currentArt = activeTrack?.album_art || playback.track?.album_art;
  const isAudioActive = Boolean(activeTrack?.audio_url || playback.is_playing || isPlaying);
  const displayProgress = duration ? (currentTime / duration) * 100 : 0;

  return (
    <footer className="player-bar" aria-label="Music Player">
      {/* Hidden HTML5 Audio Element for Free Streaming */}
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onEnded={() => setIsPlaying(false)}
        onPause={() => setIsPlaying(false)}
        onPlay={() => setIsPlaying(true)}
      />

      {/* Left: Track Info */}
      <div className="player-track-info">
        {currentArt ? (
          <img
            src={currentArt}
            alt={currentTitle}
            className={`player-album-art ${isPlaying ? 'art-pulse' : ''}`}
          />
        ) : (
          <div className="player-album-placeholder">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </div>
        )}

        <div className="player-meta">
          <div className="player-title-row">
            <span className="player-track-name">{currentTitle}</span>
            {isPlaying && (
              <div className="equalizer-waves" aria-hidden="true">
                <span />
                <span />
                <span />
                <span />
              </div>
            )}
          </div>
          <span className="player-artist-name">{currentArtist}</span>
        </div>
      </div>

      {/* Center: Controls & Progress */}
      <div className="player-controls-center">
        <div className="player-buttons">
          <button
            className="player-btn btn-secondary"
            title="Previous"
            onClick={() => onControl('previous')}
            disabled={!isAudioActive}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/>
            </svg>
          </button>

          <button
            className="player-btn btn-play-main"
            title={isPlaying ? 'Pause' : 'Play'}
            onClick={togglePlay}
            disabled={!activeTrack?.audio_url && !playback.track}
          >
            {isPlaying ? (
              <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
                <path d="M8 5v14l11-7z"/>
              </svg>
            )}
          </button>

          <button
            className="player-btn btn-secondary"
            title="Next"
            onClick={() => onControl('next')}
            disabled={!isAudioActive}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/>
            </svg>
          </button>
        </div>

        <div className="player-progress-bar-container">
          <span className="player-time">{formatTime(currentTime)}</span>
          <div className="player-progress-track">
            <input
              type="range"
              min="0"
              max={duration || 100}
              value={currentTime}
              onChange={handleSeek}
              className="player-seek-slider"
            />
            <div
              className="player-progress-fill"
              style={{ width: `${Math.min(100, Math.max(0, displayProgress))}%` }}
            />
          </div>
          <span className="player-time">{formatTime(duration || (activeTrack?.duration || 0))}</span>
        </div>
      </div>

      {/* Right: Mode & Volume */}
      <div className="player-extra-controls">
        <div className="player-engine-tag" title="100% Free Web Audio Streaming">
          <span className="free-dot" />
          <span>Web Audio Engine</span>
        </div>

        <div className="volume-container">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
          </svg>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={volume}
            onChange={handleVolumeChange}
            className="volume-slider"
            title="Volume"
          />
        </div>
      </div>
    </footer>
  );
});

PlayerBar.displayName = 'PlayerBar';
