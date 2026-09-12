import { useState, useEffect } from 'react';
import type { TrackPayload } from '../types/chat';
import './MusicTrackCard.css';

interface Props {
  track: TrackPayload;
  onPlay?: (track: TrackPayload) => void;
  isCurrentlyPlaying?: boolean;
}

function formatDuration(seconds?: number | null, ms?: number | null): string | null {
  const totalSecs = seconds ? Math.floor(seconds) : ms ? Math.floor(ms / 1000) : null;
  if (!totalSecs || isNaN(totalSecs)) return null;
  const mins = Math.floor(totalSecs / 60);
  const secs = totalSecs % 60;
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

export function MusicTrackCard({ track, onPlay, isCurrentlyPlaying }: Props) {
  const [imgError, setImgError] = useState<boolean>(false);

  useEffect(() => {
    setImgError(false);
  }, [track.id, track.title, track.album_art, track.thumbnail, track.artworkUrl]);
  const provider =
    track.provider === 'spotify'
      ? 'spotify'
      : track.provider === 'soundcloud'
      ? 'soundcloud'
      : (track.videoId || track.video_id)
      ? 'youtube'
      : track.external_url?.includes('spotify.com')
      ? 'spotify'
      : 'youtube';

  const durationStr = formatDuration(track.duration, track.duration_ms);
  const artUrl = track.album_art || track.thumbnail;
  const channelOrArtist = track.artist || track.channelTitle || track.channel_title || 'Unknown Artist';
  const isOfficial =
    Boolean(track.ranking_score && track.ranking_score >= 80) ||
    /official|vevo|records|topic/i.test(channelOrArtist) ||
    /official/i.test(track.title);

  const youtubeUrl = track.webpage_url || track.external_url || (track.videoId ? `https://www.youtube.com/watch?v=${track.videoId}` : null);
  const spotifyUrl = track.external_url || (track.uri ? `https://open.spotify.com/track/${track.id}` : null);

  const soundcloudUrl = track.permalinkUrl || (track.external_url?.includes('soundcloud.com') ? track.external_url : null) || track.url;

  return (
    <div className={`music-track-card provider-${provider}`} role="region" aria-label={`Music Result: ${track.title}`}>
      {/* Top row: Provider badge and official tag */}
      <div className="card-header-row">
        <div className={`card-provider-badge badge-${provider}`}>
          {provider === 'youtube' && (
            <>
              <svg viewBox="0 0 24 24" width="13" height="13" fill="#ff0000">
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
              </svg>
              <span>YouTube</span>
            </>
          )}
          {provider === 'spotify' && (
            <>
              <svg viewBox="0 0 24 24" width="13" height="13" fill="#1db954">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
              </svg>
              <span>Spotify</span>
            </>
          )}
          {provider === 'soundcloud' && (
            <>
              <svg viewBox="0 0 24 24" width="13" height="13" fill="#ff5500">
                <path d="M1.16 13.79c-.06 0-.11.05-.11.11v2.85c0 .06.05.11.11.11.06 0 .11-.05.11-.11v-2.85c0-.06-.05-.11-.11-.11zm1.09-1.5c-.07 0-.13.06-.13.13v4.35c0 .07.06.13.13.13s.13-.06.13-.13v-4.35c0-.07-.06-.13-.13-.13zm1.18-.75c-.08 0-.14.06-.14.14v5.1c0 .08.06.14.14.14.08 0 .14-.06.14-.14v-5.1c0-.08-.06-.14-.14-.14zm1.19-.34c-.08 0-.15.07-.15.15v5.77c0 .08.07.15.15.15.08 0 .15-.07.15-.15v-5.77c0-.08-.07-.15-.15-.15zm1.19.46c-.09 0-.16.07-.16.16v5.32c0 .09.07.16.16.16.09 0 .16-.07.16-.16v-5.32c0-.09-.07-.16-.16-.16zm1.19-.92c-.09 0-.17.08-.17.17v6.24c0 .09.08.17.17.17.09 0 .17-.08.17-.17v-6.24c0-.09-.08-.17-.17-.17zm1.19-.24c-.1 0-.18.08-.18.18v6.48c0 .1.08.18.18.18.1 0 .18-.08.18-.18v-6.48c0-.1-.08-.18-.18-.18zm1.2-.55c-.1 0-.19.08-.19.19v7.02c0 .1.09.19.19.19.1 0 .19-.09.19-.19v-7.02c0-.11-.09-.19-.19-.19zm1.19.34c-.11 0-.2.09-.2.2v6.68c0 .11.09.2.2.2.11 0 .2-.09.2-.2v-6.68c0-.11-.09-.2-.2-.2zm1.74-2.88c-.28 0-.55.06-.8.16v8.43c.27.09.55.15.84.15 2.5 0 4.53-2.03 4.53-4.53s-2.03-4.21-4.57-4.21z"/>
              </svg>
              <span>SoundCloud</span>
            </>
          )}
        </div>

        {isOfficial && (
          <div className="card-official-badge" title="Official Verified Release">
            <svg viewBox="0 0 24 24" width="11" height="11" fill="currentColor">
              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
            </svg>
            <span>Official</span>
          </div>
        )}

        {track.access && track.access !== 'playable' && (
          <div className={`card-access-badge badge-${track.access}`} title={`SoundCloud status: ${track.access}`}>
            <span>{track.access === 'preview' ? 'Preview' : 'Geo-restricted'}</span>
          </div>
        )}

        {durationStr && <span className="card-duration-text">{durationStr}</span>}
      </div>

      {/* Main body: Artwork and details */}
      <div className="card-body-row">
        {artUrl && !imgError ? (
          <img
            src={artUrl}
            alt={track.title}
            className="card-thumbnail"
            loading="lazy"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="card-thumbnail-placeholder" title={track.title}>
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 18V5l12-2v13"/>
              <circle cx="6" cy="18" r="3"/>
              <circle cx="18" cy="16" r="3"/>
            </svg>
          </div>
        )}

        <div className="card-meta">
          <span className="card-title" title={track.title}>{track.title}</span>
          <span className="card-artist" title={channelOrArtist}>
            {provider === 'soundcloud' && track.creator ? track.creator : channelOrArtist}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="card-actions-row">
        {provider === 'youtube' && (
          <>
            {onPlay && (
              <button
                className={`btn-card-action btn-play-action ${isCurrentlyPlaying ? 'now-playing' : ''}`}
                onClick={() => onPlay(track)}
              >
                {isCurrentlyPlaying ? (
                  <>
                    <span className="mini-eq"><span /><span /><span /></span>
                    <span>Playing</span>
                  </>
                ) : (
                  <>
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor">
                      <path d="M8 5v14l11-7z"/>
                    </svg>
                    <span>Play</span>
                  </>
                )}
              </button>
            )}

            {youtubeUrl && (
              <a
                href={youtubeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-card-action btn-secondary-action"
                title="Watch directly on YouTube"
              >
                <span>Open on YouTube</span>
                <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
                  <path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/>
                </svg>
              </a>
            )}
          </>
        )}

        {provider === 'spotify' && (
          <>
            {spotifyUrl && (
              <a
                href={spotifyUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-card-action btn-spotify-action"
                title="Listen in Spotify"
              >
                <span>Open in Spotify</span>
                <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
                  <path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/>
                </svg>
              </a>
            )}
          </>
        )}

        {provider === 'soundcloud' && (
          <>
            {onPlay && (
              <button
                className={`btn-card-action btn-play-action btn-soundcloud-play ${isCurrentlyPlaying ? 'now-playing' : ''}`}
                onClick={() => onPlay(track)}
                title={isCurrentlyPlaying ? 'Currently playing' : 'Play audio directly in Zana'}
              >
                {isCurrentlyPlaying ? (
                  <>
                    <span className="mini-eq"><span /><span /><span /></span>
                    <span>Playing</span>
                  </>
                ) : (
                  <>
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor">
                      <path d="M8 5v14l11-7z"/>
                    </svg>
                    <span>Play</span>
                  </>
                )}
              </button>
            )}

            {soundcloudUrl && (
              <a
                href={soundcloudUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-card-action btn-secondary-action btn-soundcloud-link"
                title="View on SoundCloud"
              >
                <span>Open on SoundCloud</span>
                <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
                  <path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/>
                </svg>
              </a>
            )}
          </>
        )}
      </div>
    </div>
  );
}
