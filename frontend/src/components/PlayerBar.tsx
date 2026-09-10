import React, {
  useRef,
  useState,
  useEffect,
  useImperativeHandle,
  forwardRef,
  useCallback,
} from 'react';
import type { SpotifyPlaybackState } from '../types/spotify';
import type { TrackPayload, ProviderType } from '../types/chat';
import './PlayerBar.css';

interface PlayerBarProps {
  playback: SpotifyPlaybackState;
  activeTrack: TrackPayload | null;
  onControl: (action: string, params?: { query?: string; volume_percent?: number }) => void;
  onConnect?: () => void;
  isConnected?: boolean;
  isSpeaking?: boolean; // For TTS audio ducking
}

export interface PlayerBarRef {
  play: () => void;
  pause: () => void;
  setVolume: (val: number) => void;
  seek: (val: number) => void;
}

declare global {
  interface Window {
    YT?: any;
    onYouTubeIframeAPIReady?: () => void;
  }
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
  isSpeaking = false,
}, ref) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ytPlayerRef = useRef<any>(null);
  const ytContainerRef = useRef<HTMLDivElement | null>(null);
  const progressTimerRef = useRef<number | null>(null);

  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isBuffering, setIsBuffering] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [volume, setVolume] = useState<number>(0.8);
  const [playbackError, setPlaybackError] = useState<string | null>(null);
  const [autoplayBlocked, setAutoplayBlocked] = useState<boolean>(false);
  const [isVideoExpanded, setIsVideoExpanded] = useState<boolean>(false);
  const [ytApiReady, setYtApiReady] = useState<boolean>(false);

  // Determine current active provider
  const currentProvider: ProviderType =
    activeTrack?.provider === 'spotify'
      ? 'spotify'
      : activeTrack?.provider === 'soundcloud'
      ? 'soundcloud'
      : (activeTrack?.videoId || activeTrack?.video_id)
      ? 'youtube'
      : activeTrack?.audio_url
      ? 'youtube' // fallback to embedded/audio
      : 'youtube';

  const currentVideoId = activeTrack?.videoId || activeTrack?.video_id || (
    activeTrack?.id && activeTrack.id.length === 11 ? activeTrack.id : null
  );

  // ── Load official YouTube IFrame Player API ──────────────────────────────
  useEffect(() => {
    if (window.YT && window.YT.Player) {
      setYtApiReady(true);
      return;
    }

    const prevReady = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      if (prevReady) prevReady();
      setYtApiReady(true);
    };

    if (!document.getElementById('youtube-iframe-api-script')) {
      const tag = document.createElement('script');
      tag.id = 'youtube-iframe-api-script';
      tag.src = 'https://www.youtube.com/iframe_api';
      tag.async = true;
      document.body.appendChild(tag);
    }
  }, []);

  // ── YouTube Player state listener helper ─────────────────────────────────
  const onPlayerStateChange = useCallback((event: any) => {
    const YT = window.YT;
    if (!YT) return;

    switch (event.data) {
      case YT.PlayerState.PLAYING:
        setIsPlaying(true);
        setIsBuffering(false);
        setAutoplayBlocked(false);
        setPlaybackError(null);
        break;
      case YT.PlayerState.PAUSED:
        setIsPlaying(false);
        setIsBuffering(false);
        break;
      case YT.PlayerState.BUFFERING:
        setIsBuffering(true);
        break;
      case YT.PlayerState.ENDED:
        setIsPlaying(false);
        setIsBuffering(false);
        onControl('next');
        break;
      case YT.PlayerState.UNSTARTED:
        setIsBuffering(false);
        break;
      default:
        break;
    }
  }, [onControl]);

  // ── YouTube Player error handling ─────────────────────────────────────────
  const onPlayerError = useCallback((event: any) => {
    console.warn('[YT-PLAYER] Error event:', event.data);
    setIsBuffering(false);
    setIsPlaying(false);

    let errorMsg = 'An error occurred during YouTube playback.';
    if (event.data === 2) {
      errorMsg = 'Invalid YouTube video ID.';
    } else if (event.data === 5) {
      errorMsg = 'HTML5 player error on YouTube.';
    } else if (event.data === 100) {
      errorMsg = 'This video is private or removed from YouTube.';
    } else if (event.data === 101 || event.data === 150) {
      errorMsg = 'Embedding is disabled by the content owner on YouTube.';
    }
    setPlaybackError(errorMsg);
  }, []);

  // ── Initialize or update YouTube Player instance ──────────────────────────
  useEffect(() => {
    if (!ytApiReady || !currentVideoId) return;

    if (!ytPlayerRef.current) {
      // Create fresh player
      try {
        ytPlayerRef.current = new window.YT.Player('zana-yt-player-iframe', {
          videoId: currentVideoId,
          playerVars: {
            autoplay: 1,
            controls: 1,
            modestbranding: 1,
            rel: 0,
            fs: 1,
            enablejsapi: 1,
            playsinline: 1,
            origin: window.location.origin,
          },
          events: {
            onReady: (event: any) => {
              event.target.setVolume(Math.round(volume * 100));
              try {
                event.target.playVideo();
              } catch (e) {
                console.warn('[YT-PLAYER] Autoplay blocked:', e);
                setAutoplayBlocked(true);
              }
            },
            onStateChange: onPlayerStateChange,
            onError: onPlayerError,
          },
        });
      } catch (e) {
        console.error('[YT-PLAYER] Initialization error:', e);
        setPlaybackError('Failed to initialize YouTube player.');
      }
    } else {
      // Player exists: load new video
      try {
        setPlaybackError(null);
        setAutoplayBlocked(false);
        setIsBuffering(true);
        ytPlayerRef.current.loadVideoById({
          videoId: currentVideoId,
          startSeconds: 0,
        });
        ytPlayerRef.current.setVolume(Math.round(volume * 100));
      } catch (e) {
        console.warn('[YT-PLAYER] loadVideoById error:', e);
      }
    }
  }, [ytApiReady, currentVideoId, onPlayerStateChange, onPlayerError]);

  // ── Time & Duration Polling for YouTube Player ────────────────────────────
  useEffect(() => {
    if (progressTimerRef.current) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }

    if (isPlaying && ytPlayerRef.current && typeof ytPlayerRef.current.getCurrentTime === 'function') {
      progressTimerRef.current = window.setInterval(() => {
        try {
          const cur = ytPlayerRef.current.getCurrentTime();
          const dur = ytPlayerRef.current.getDuration();
          if (typeof cur === 'number' && !isNaN(cur)) {
            setCurrentTime(cur);
          }
          if (typeof dur === 'number' && !isNaN(dur) && dur > 0) {
            setDuration(dur);
          }
        } catch {}
      }, 500);
    }

    return () => {
      if (progressTimerRef.current) {
        window.clearInterval(progressTimerRef.current);
        progressTimerRef.current = null;
      }
    };
  }, [isPlaying]);

  // ── TTS Audio Ducking ────────────────────────────────────────────────────
  // When assistant is speaking, duck the volume to 20% of user setting
  useEffect(() => {
    const effectiveVolume = isSpeaking ? volume * 0.2 : volume;
    if (ytPlayerRef.current && typeof ytPlayerRef.current.setVolume === 'function') {
      ytPlayerRef.current.setVolume(Math.round(effectiveVolume * 100));
    }
    if (audioRef.current) {
      audioRef.current.volume = effectiveVolume;
    }
  }, [isSpeaking, volume]);

  // ── Imperative ref controls (parent can trigger play/pause/volume/seek) ──
  useImperativeHandle(ref, () => ({
    play: () => {
      if (currentVideoId && ytPlayerRef.current && typeof ytPlayerRef.current.playVideo === 'function') {
        try {
          ytPlayerRef.current.playVideo();
          setIsPlaying(true);
          setAutoplayBlocked(false);
        } catch (e) {
          console.warn('[YT-PLAYER] playVideo error:', e);
        }
      } else if (audioRef.current) {
        audioRef.current.play().then(() => setIsPlaying(true)).catch(console.error);
      }
    },
    pause: () => {
      if (currentVideoId && ytPlayerRef.current && typeof ytPlayerRef.current.pauseVideo === 'function') {
        try {
          ytPlayerRef.current.pauseVideo();
          setIsPlaying(false);
        } catch (e) {
          console.warn('[YT-PLAYER] pauseVideo error:', e);
        }
      } else if (audioRef.current) {
        audioRef.current.pause();
        setIsPlaying(false);
      }
    },
    setVolume: (val: number) => {
      const clamped = Math.max(0, Math.min(1, val));
      setVolume(clamped);
      if (ytPlayerRef.current && typeof ytPlayerRef.current.setVolume === 'function') {
        ytPlayerRef.current.setVolume(Math.round(clamped * 100));
      }
      if (audioRef.current) {
        audioRef.current.volume = clamped;
      }
    },
    seek: (val: number) => {
      if (currentVideoId && ytPlayerRef.current && typeof ytPlayerRef.current.seekTo === 'function') {
        ytPlayerRef.current.seekTo(val, true);
        setCurrentTime(val);
      } else if (audioRef.current) {
        audioRef.current.currentTime = val;
        setCurrentTime(val);
      }
    },
  }));

  // ── HTML5 Audio Fallback ─────────────────────────────────────────────────
  useEffect(() => {
    if (activeTrack?.audio_url && !currentVideoId && audioRef.current) {
      audioRef.current.src = activeTrack.audio_url;
      audioRef.current.volume = volume;
      audioRef.current.play().then(() => {
        setIsPlaying(true);
      }).catch((err) => {
        console.warn('[AUDIO] Autoplay error:', err);
        setAutoplayBlocked(true);
      });
    }
  }, [activeTrack, currentVideoId, volume]);

  const togglePlay = () => {
    if (currentVideoId && ytPlayerRef.current) {
      if (isPlaying) {
        try {
          ytPlayerRef.current.pauseVideo();
          setIsPlaying(false);
          onControl('pause');
        } catch {}
      } else {
        try {
          ytPlayerRef.current.playVideo();
          setIsPlaying(true);
          setAutoplayBlocked(false);
          onControl('resume');
        } catch {}
      }
      return;
    }

    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
      onControl('pause');
    } else {
      audioRef.current.play().then(() => {
        setIsPlaying(true);
        setAutoplayBlocked(false);
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
    setCurrentTime(targetTime);
    if (currentVideoId && ytPlayerRef.current && typeof ytPlayerRef.current.seekTo === 'function') {
      ytPlayerRef.current.seekTo(targetTime, true);
    } else if (audioRef.current) {
      audioRef.current.currentTime = targetTime;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const vol = Number(e.target.value);
    setVolume(vol);
    if (currentVideoId && ytPlayerRef.current && typeof ytPlayerRef.current.setVolume === 'function') {
      ytPlayerRef.current.setVolume(Math.round(vol * 100));
    }
    if (audioRef.current) {
      audioRef.current.volume = vol;
    }
    onControl('volume', { volume_percent: Math.round(vol * 100) });
  };

  // Determine current active display data
  const currentTitle =
    activeTrack?.title || playback.track?.name || 'No track playing';
  const currentArtist =
    activeTrack?.artist ||
    activeTrack?.channelTitle ||
    activeTrack?.channel_title ||
    playback.track?.artists ||
    'Ask Zana to play any song!';
  const currentArt =
    activeTrack?.album_art ||
    activeTrack?.thumbnail ||
    playback.track?.album_art;
  const isAudioActive = Boolean(currentVideoId || activeTrack?.audio_url || playback.is_playing || isPlaying);
  const displayProgress = duration ? (currentTime / duration) * 100 : 0;

  return (
    <>
      {/* ── Docked / Expandable Video Viewer ──────────────────────────────── */}
      <div
        ref={ytContainerRef}
        className={`docked-youtube-viewer ${isVideoExpanded ? 'expanded' : 'docked-hidden'}`}
        aria-label="YouTube Video Player"
      >
        <div className="docked-viewer-header">
          <div className="docked-viewer-title">
            <span className="yt-dot" />
            <span className="docked-title-text">{currentTitle}</span>
          </div>
          <div className="docked-viewer-actions">
            {activeTrack?.webpage_url && (
              <a
                href={activeTrack.webpage_url}
                target="_blank"
                rel="noopener noreferrer"
                className="docked-action-link"
                title="Open on YouTube"
              >
                <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                  <path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/>
                </svg>
              </a>
            )}
            <button
              className="docked-close-btn"
              onClick={() => setIsVideoExpanded(false)}
              title="Minimize Video"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
              </svg>
            </button>
          </div>
        </div>

        <div className="docked-iframe-wrapper">
          {/* The official YouTube IFrame will mount here */}
          <div id="zana-yt-player-iframe" />
        </div>
      </div>

      {/* ── Autoplay Blocked Banner ──────────────────────────────────────── */}
      {autoplayBlocked && (
        <div className="autoplay-blocked-banner" role="alert">
          <span className="autoplay-text">⚠️ Browser paused autoplay. Tap Play to start listening.</span>
          <button className="btn-autoplay-start" onClick={togglePlay}>
            Tap Play to start
          </button>
        </div>
      )}

      {/* ── Error Banner ─────────────────────────────────────────────────── */}
      {playbackError && (
        <div className="playback-error-banner" role="alert">
          <span>{playbackError}</span>
          {activeTrack?.webpage_url && (
            <a
              href={activeTrack.webpage_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-error-open-yt"
            >
              Open on YouTube
            </a>
          )}
          <button
            className="btn-error-dismiss"
            onClick={() => setPlaybackError(null)}
            title="Dismiss"
          >
            ✕
          </button>
        </div>
      )}

      {/* ── Bottom Fixed Player Bar ──────────────────────────────────────── */}
      <footer className="player-bar" aria-label="Music Player">
        {/* Hidden HTML5 Audio Element for Fallback / Audio Files */}
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
              <span className="player-track-name" title={currentTitle}>{currentTitle}</span>
              {isPlaying && (
                <div className="equalizer-waves" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
              )}
            </div>
            <span className="player-artist-name" title={currentArtist}>{currentArtist}</span>
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
              className={`player-btn btn-play-main ${isBuffering ? 'btn-buffering' : ''}`}
              title={isPlaying ? 'Pause' : 'Play'}
              onClick={togglePlay}
              disabled={!isAudioActive && !playback.track}
            >
              {isBuffering ? (
                <span className="btn-spinner" />
              ) : isPlaying ? (
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
                aria-label="Seek track position"
              />
              <div
                className="player-progress-fill"
                style={{ width: `${Math.min(100, Math.max(0, displayProgress))}%` }}
              />
            </div>
            <span className="player-time">{formatTime(duration || (activeTrack?.duration || 0))}</span>
          </div>
        </div>

        {/* Right: Provider Badge, Video Toggle & Volume */}
        <div className="player-extra-controls">
          {/* Provider Badge */}
          {currentProvider === 'youtube' && (
            <div className="player-provider-tag tag-youtube" title="Playing via official YouTube IFrame Player">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="#ff0000">
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
              </svg>
              <span>YouTube</span>
            </div>
          )}

          {currentProvider === 'spotify' && (
            <div className="player-provider-tag tag-spotify" title="Spotify Provider">
              <span className="device-dot" />
              <span>Spotify</span>
            </div>
          )}

          {/* Video Toggle Button (Expand/Collapse YouTube video viewer) */}
          {currentVideoId && (
            <button
              className={`btn-video-toggle ${isVideoExpanded ? 'active' : ''}`}
              onClick={() => setIsVideoExpanded((prev) => !prev)}
              title={isVideoExpanded ? 'Hide Video' : 'Show Video'}
              aria-label={isVideoExpanded ? 'Hide Video' : 'Show Video'}
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M21 3H3c-1.11 0-2 .89-2 2v12a2 2 0 0 0 2 2h5v2h8v-2h5c1.1 0 1.99-.9 1.99-2L23 5a2 2 0 0 0-2-2zm0 14H3V5h18v12zm-5-6l-7 4V7z"/>
              </svg>
              <span>{isVideoExpanded ? 'Hide' : 'Video'}</span>
            </button>
          )}

          {/* Open in YouTube Direct Link */}
          {activeTrack?.webpage_url && (
            <a
              href={activeTrack.webpage_url}
              target="_blank"
              rel="noopener noreferrer"
              className="player-icon-link"
              title="Open on YouTube"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/>
              </svg>
            </a>
          )}

          {/* Volume Control */}
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
              aria-label="Volume"
            />
          </div>
        </div>
      </footer>
    </>
  );
});

PlayerBar.displayName = 'PlayerBar';
