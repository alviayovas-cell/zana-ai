import React, { useEffect, useRef, useState } from 'react';
import type { SpotifyUser } from '../types/spotify';
import { API_BASE_URL } from '../services/api';
import './ProfileModal.css';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  userId?: string;
  isDark: boolean;
  onToggleTheme: () => void;
  ttsEnabled: boolean;
  onToggleTts: () => void;
  voices?: SpeechSynthesisVoice[];
  selectedVoiceURI?: string;
  onSelectVoice?: (voiceURI: string) => void;
  ttsRate?: number;
  onSetTtsRate?: (rate: number) => void;
  hasSamantha?: boolean;
  resolvedVoice?: SpeechSynthesisVoice | null;
  wakeWordEnabled: boolean;
  onToggleWakeWord: (enabled: boolean) => void;
  spotifyUser: SpotifyUser | null;
  isSpotifyConnected: boolean;
  onConnectSpotify: () => void;
}

type Section = 'profile' | 'voice' | 'memory' | 'music' | 'appearance' | 'privacy';
type MemoryItem = { id?: string; content: string; category?: string; created_at?: number };

function getMemorySessionId(): string {
  try { return localStorage.getItem('zana_session_id') || 'anonymous'; } catch { return 'anonymous'; }
}

const sections: Array<{ id: Section; label: string; icon: string }> = [
  { id: 'profile', label: 'Profile', icon: '◉' },
  { id: 'voice', label: 'Voice & Speech', icon: '◌' },
  { id: 'memory', label: 'Memory', icon: '✦' },
  { id: 'music', label: 'Music', icon: '♫' },
  { id: 'appearance', label: 'Appearance', icon: '◐' },
  { id: 'privacy', label: 'Privacy', icon: '⌁' },
];

export const ProfileModal: React.FC<Props> = ({
  isOpen, onClose, userId = 'default-user', isDark, onToggleTheme,
  ttsEnabled, onToggleTts, voices = [], selectedVoiceURI = '', onSelectVoice,
  ttsRate = 1.0, onSetTtsRate, hasSamantha = false, resolvedVoice = null,
  wakeWordEnabled, onToggleWakeWord,
  spotifyUser, isSpotifyConnected, onConnectSpotify,
}) => {
  const [section, setSection] = useState<Section>('profile');
  const [displayName, setDisplayName] = useState('Music Enthusiast');
  const [language, setLanguage] = useState('en');
  const [timezone, setTimezone] = useState('UTC');
  const [responseStyle, setResponseStyle] = useState('balanced');
  const [memoryEnabled, setMemoryEnabled] = useState(true);
  const [toolExecution, setToolExecution] = useState(true);
  const [autoplay, setAutoplay] = useState(true);
  const [avatarUrl, setAvatarUrl] = useState('');
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [confirmAction, setConfirmAction] = useState<'memory' | 'preferences' | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!isOpen) return;
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    setSection('profile'); setErrorMessage(''); setStatusMessage(''); setIsLoading(true);
    Promise.all([
      fetch(`${API_BASE_URL}/api/profile?user_id=${userId}`).then((res) => res.ok ? res.json() : null),
      fetch(`${API_BASE_URL}/api/memory?session_id=${encodeURIComponent(getMemorySessionId())}`).then((res) => res.ok ? res.json() : null),
    ]).then(([profile, memoryData]) => {
      if (profile) {
        setDisplayName(profile.display_name || 'Music Enthusiast');
        setLanguage(profile.preferred_language || 'en'); setTimezone(profile.timezone || 'UTC');
        setResponseStyle(profile.assistant_preferences?.response_style || 'balanced');
        setMemoryEnabled(profile.assistant_preferences?.memory_enabled ?? true);
        setToolExecution(profile.assistant_preferences?.tool_execution ?? true);
        setAutoplay(profile.music_preferences?.autoplay ?? true);
        if (profile.assistant_preferences?.selected_voice && onSelectVoice && !selectedVoiceURI) {
          onSelectVoice(profile.assistant_preferences.selected_voice);
        }
        if (profile.assistant_preferences?.tts_rate && onSetTtsRate) {
          onSetTtsRate(Number(profile.assistant_preferences.tts_rate));
        }
      }
      if (memoryData) setMemories(memoryData.memories || []);
    }).catch(() => setErrorMessage('Unable to load profile settings.')).finally(() => setIsLoading(false));
    try { setAvatarUrl(localStorage.getItem(`zana_avatar_${userId}`) || ''); } catch { setAvatarUrl(''); }
    const handleKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') onCloseRef.current(); };
    document.addEventListener('keydown', handleKeyDown);
    return () => { document.removeEventListener('keydown', handleKeyDown); previousFocusRef.current?.focus(); };
  }, [isOpen, userId]);

  if (!isOpen) return null;

  const saveProfile = async () => {
    const trimmedName = displayName.trim();
    if (!trimmedName) { setErrorMessage('Please enter a display name.'); setSection('profile'); return; }
    setIsSaving(true); setErrorMessage('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/profile`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, display_name: trimmedName, preferred_language: language, timezone,
          tts_enabled: ttsEnabled, wake_word_enabled: wakeWordEnabled,
          music_preferences: { autoplay },
          assistant_preferences: {
            response_style: responseStyle,
            memory_enabled: memoryEnabled,
            tool_execution: toolExecution,
            selected_voice: selectedVoiceURI,
            tts_rate: ttsRate,
          } }),
      });
      if (!response.ok) throw new Error('save failed');
      setDisplayName(trimmedName); setStatusMessage('Changes saved'); window.setTimeout(() => setStatusMessage(''), 2500);
    } catch { setErrorMessage('Unable to save changes. Your values are still here.'); } finally { setIsSaving(false); }
  };

  const handleAvatar = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; if (!file) return;
    if (!file.type.startsWith('image/')) { setErrorMessage('Choose a JPG, PNG, WEBP, or GIF image.'); return; }
    if (file.size > 2 * 1024 * 1024) { setErrorMessage('Profile images must be smaller than 2 MB.'); return; }
    const reader = new FileReader();
    reader.onload = () => { const value = String(reader.result || ''); setAvatarUrl(value); try { localStorage.setItem(`zana_avatar_${userId}`, value); setStatusMessage('Profile photo updated'); } catch { setErrorMessage('This image could not be stored locally.'); } };
    reader.readAsDataURL(file);
  };
  const removeAvatar = () => { setAvatarUrl(''); try { localStorage.removeItem(`zana_avatar_${userId}`); } catch {} setStatusMessage('Profile photo removed'); };
  const clearMemory = async () => { try { const response = await fetch(`${API_BASE_URL}/api/memory?session_id=${encodeURIComponent(getMemorySessionId())}`, { method: 'DELETE' }); if (!response.ok) throw new Error(); setMemories([]); setStatusMessage('Memory cleared'); } catch { setErrorMessage('Unable to clear memory right now.'); } setConfirmAction(null); };
  const resetPreferences = () => { setDisplayName('Music Enthusiast'); setLanguage('en'); setTimezone('UTC'); setResponseStyle('balanced'); setMemoryEnabled(true); setToolExecution(true); setAutoplay(true); setConfirmAction(null); setStatusMessage('Defaults restored locally. Save to apply them.'); };
  const initials = displayName.trim().split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase() || 'M';

  return <div className="modal-backdrop profile-backdrop" onClick={onClose}>
    <div className="modal-content profile-modal" role="dialog" aria-modal="true" aria-labelledby="profile-title" onClick={(event) => event.stopPropagation()}>
      <header className="profile-header"><div><p className="profile-eyebrow">ZANA / PERSONAL SPACE</p><h2 id="profile-title">Profile &amp; Settings</h2></div><button className="profile-close" onClick={onClose} aria-label="Close profile settings">×</button></header>
      <div className="profile-layout">
        <nav className="profile-nav" aria-label="Settings sections">{sections.map((item) => <button key={item.id} className={`profile-nav-item ${section === item.id ? 'active' : ''}`} onClick={() => setSection(item.id)} aria-current={section === item.id ? 'page' : undefined}><span aria-hidden="true">{item.icon}</span>{item.label}</button>)}<div className="profile-nav-note"><span>●</span> Preferences stay with this device</div></nav>
        <main className="profile-content">{isLoading ? <div className="profile-loading" role="status">Loading your settings...</div> : <>
          {section === 'profile' && <ProfileSection displayName={displayName} setDisplayName={setDisplayName} language={language} setLanguage={setLanguage} timezone={timezone} setTimezone={setTimezone} avatarUrl={avatarUrl} initials={initials} avatarInputRef={avatarInputRef} handleAvatar={handleAvatar} removeAvatar={removeAvatar} />}
          {section === 'voice' && <VoiceSection ttsEnabled={ttsEnabled} onToggleTts={onToggleTts} voices={voices} selectedVoiceURI={selectedVoiceURI} onSelectVoice={onSelectVoice} ttsRate={ttsRate} onSetTtsRate={onSetTtsRate} hasSamantha={hasSamantha} resolvedVoice={resolvedVoice} wakeWordEnabled={wakeWordEnabled} onToggleWakeWord={onToggleWakeWord} responseStyle={responseStyle} setResponseStyle={setResponseStyle} memoryEnabled={memoryEnabled} setMemoryEnabled={setMemoryEnabled} toolExecution={toolExecution} setToolExecution={setToolExecution} />}
          {section === 'memory' && <MemorySection memories={memories} memoryEnabled={memoryEnabled} setMemoryEnabled={setMemoryEnabled} onClear={() => setConfirmAction('memory')} />}
          {section === 'music' && <MusicSection isSpotifyConnected={isSpotifyConnected} spotifyUser={spotifyUser} onConnectSpotify={onConnectSpotify} autoplay={autoplay} setAutoplay={setAutoplay} />}
          {section === 'appearance' && <AppearanceSection isDark={isDark} onToggleTheme={onToggleTheme} />}
          {section === 'privacy' && <PrivacySection memoryCount={memories.length} onClearMemory={() => setConfirmAction('memory')} onReset={() => setConfirmAction('preferences')} />}
        </>}</main>
      </div>
      {errorMessage && <div className="profile-message error" role="alert">! {errorMessage}</div>}{statusMessage && <div className="profile-message success" role="status">✓ {statusMessage}</div>}
      <footer className="profile-footer"><span className="profile-footer-hint">{section === 'profile' || section === 'voice' ? 'Changes apply to your Zana experience.' : 'Your existing Zana features remain unchanged.'}</span><div><button className="profile-secondary" onClick={onClose}>Close</button><button className="profile-primary" onClick={saveProfile} disabled={isSaving || isLoading}>{isSaving ? 'Saving...' : 'Save changes'}</button></div></footer>
      {confirmAction && <div className="profile-confirm" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title"><div><p className="profile-eyebrow">Confirmation</p><h3 id="confirm-title">{confirmAction === 'memory' ? 'Clear all saved memories?' : 'Restore default preferences?'}</h3><p>{confirmAction === 'memory' ? 'This cannot be undone.' : 'Your current preference values will be replaced locally.'}</p><div><button className="profile-secondary" onClick={() => setConfirmAction(null)}>Cancel</button><button className="profile-danger" onClick={confirmAction === 'memory' ? clearMemory : resetPreferences}>{confirmAction === 'memory' ? 'Clear memory' : 'Restore defaults'}</button></div></div></div>}
    </div>
  </div>;
};

function Toggle({ checked, onChange, label, description }: { checked: boolean; onChange: (value: boolean) => void; label: string; description: string }) { return <label className="setting-row"><span><strong>{label}</strong><small>{description}</small></span><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /><i aria-hidden="true" /></label>; }
function ProfileSection({ displayName, setDisplayName, language, setLanguage, timezone, setTimezone, avatarUrl, initials, avatarInputRef, handleAvatar, removeAvatar }: any) { return <section className="settings-section"><SectionIntro eyebrow="Your profile" title="Make Zana yours" description="A few details help Zana feel more personal, without getting in your way." /><div className="profile-identity"><div className="profile-avatar">{avatarUrl ? <img src={avatarUrl} alt="Profile" /> : <span>{initials}</span>}</div><div><h3>{displayName}</h3><p>Personal AI user</p><button className="profile-link" onClick={() => avatarInputRef.current?.click()}>Change photo</button>{avatarUrl && <button className="profile-link muted" onClick={removeAvatar}>Remove</button>}<input ref={avatarInputRef} className="visually-hidden" type="file" accept="image/png,image/jpeg,image/webp,image/gif" onChange={handleAvatar} /></div></div><div className="settings-grid"><Field label="Display name"><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Your name" /></Field><Field label="Preferred language"><select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="en">English (US)</option><option value="ta">Tamil</option><option value="hi">Hindi</option></select></Field><Field label="Timezone"><select value={timezone} onChange={(event) => setTimezone(event.target.value)}><option>UTC</option><option>Asia/Kolkata</option><option>America/New_York</option><option>Europe/London</option><option>Asia/Tokyo</option><option>Australia/Sydney</option></select></Field></div></section>; }
function VoiceSection({
  ttsEnabled,
  onToggleTts,
  voices = [],
  selectedVoiceURI = '',
  onSelectVoice,
  ttsRate = 1.0,
  onSetTtsRate,
  hasSamantha = false,
  resolvedVoice = null,
  wakeWordEnabled,
  onToggleWakeWord,
  responseStyle,
  setResponseStyle,
  memoryEnabled,
  setMemoryEnabled,
  toolExecution,
  setToolExecution,
}: any) {
  const isSamanthaSelected = selectedVoiceURI?.toLowerCase().includes('samantha');

  return (
    <section className="settings-section">
      <SectionIntro
        eyebrow="Voice & Speech"
        title="How Zana responds"
        description="Configure voice output, assistant personality, and speech preferences."
      />
      <div className="settings-group">
        <Toggle
          checked={ttsEnabled}
          onChange={() => onToggleTts()}
          label="Voice output"
          description="Let Zana read replies aloud."
        />
        {ttsEnabled && (
          <div style={{ padding: '14px 0', borderBottom: '1px solid var(--glass-border)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <Field label="Assistant Voice">
              <select
                value={selectedVoiceURI || ''}
                onChange={(event) => onSelectVoice && onSelectVoice(event.target.value)}
                aria-label="Assistant Voice"
              >
                <option value="">Default (Auto - Best Natural Female Voice)</option>
                <option value="samantha">
                  Samantha (Natural Female{hasSamantha ? ' - Installed' : ' - Auto Fallback'})
                </option>
                {voices
                  .filter((v: SpeechSynthesisVoice) => !v.name.toLowerCase().includes('samantha'))
                  .map((v: SpeechSynthesisVoice) => (
                    <option key={v.voiceURI || v.name} value={v.voiceURI || v.name}>
                      {v.name} ({v.lang})
                    </option>
                  ))}
              </select>
            </Field>

            {/* Active Voice Status Pill */}
            <div
              style={{
                fontSize: '0.68rem',
                color: 'var(--text-muted)',
                lineHeight: 1.4,
                padding: '7px 10px',
                borderRadius: '7px',
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid var(--glass-border)',
              }}
            >
              <strong style={{ color: 'var(--text-secondary)' }}>Active Voice: </strong>
              {resolvedVoice ? `${resolvedVoice.name} (${resolvedVoice.lang})` : 'System Default'}
              {isSamanthaSelected && !hasSamantha && (
                <span style={{ display: 'block', color: 'var(--accent-light)', marginTop: '2px' }}>
                  ✦ Samantha fallback active: Using best natural female voice available on this device.
                </span>
              )}
            </div>

            {onSetTtsRate && (
              <Field label={`Speech Rate (${ttsRate.toFixed(1)}x)`}>
                <input
                  type="range"
                  min="0.7"
                  max="1.5"
                  step="0.1"
                  value={ttsRate}
                  onChange={(event) => onSetTtsRate(parseFloat(event.target.value))}
                  aria-label="Speech Rate"
                />
              </Field>
            )}
          </div>
        )}
        <Toggle
          checked={wakeWordEnabled}
          onChange={onToggleWakeWord}
          label="Hey Zana wake word"
          description="Listen for the wake word when explicitly enabled."
        />
        <Toggle
          checked={memoryEnabled}
          onChange={setMemoryEnabled}
          label="Conversation memory"
          description="Allow Zana to remember useful preferences and context."
        />
        <Toggle
          checked={toolExecution}
          onChange={setToolExecution}
          label="Tool execution"
          description="Let Zana carry out supported music and assistant actions."
        />
      </div>
      <div className="style-picker">
        <div>
          <p className="section-kicker">Response style</p>
          <h3>Choose your default tone</h3>
        </div>
        <div className="style-options">
          {['concise', 'balanced', 'detailed'].map((style) => (
            <button
              key={style}
              className={responseStyle === style ? 'selected' : ''}
              onClick={() => setResponseStyle(style)}
            >
              {style[0].toUpperCase() + style.slice(1)}
              <small>
                {style === 'concise'
                  ? 'Fast and focused'
                  : style === 'balanced'
                  ? 'Clear and natural'
                  : 'More context'}
              </small>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
function MemorySection({ memories, memoryEnabled, setMemoryEnabled, onClear }: { memories: MemoryItem[]; memoryEnabled: boolean; setMemoryEnabled: (value: boolean) => void; onClear: () => void }) { return <section className="settings-section"><SectionIntro eyebrow="Memory" title="A little context goes a long way" description="Review the real memories Zana has saved for this session." /><div className="memory-summary"><div><span className="memory-number">{memories.length}</span><small>saved memories</small></div><span className={`status-pill ${memoryEnabled ? 'on' : ''}`}>{memoryEnabled ? '● On' : '○ Off'}</span></div><Toggle checked={memoryEnabled} onChange={setMemoryEnabled} label="Memory" description="Allow Zana to remember useful preferences and context." /><div className="memory-list">{memories.length ? memories.slice(0, 5).map((memory) => <div className="memory-item" key={memory.id || memory.content}><span>•</span><p>{memory.content}</p></div>) : <div className="memory-empty"><span>✦</span><p>No saved memories yet.</p></div>}</div><button className="text-danger" onClick={onClear} disabled={!memories.length}>Clear memory</button></section>; }
function MusicSection({ isSpotifyConnected, spotifyUser, onConnectSpotify, autoplay, setAutoplay }: any) { return <section className="settings-section"><SectionIntro eyebrow="Music" title="Keep the soundtrack close" description="Manage the connection Zana uses for playback." /><div className={`connection-panel ${isSpotifyConnected ? 'connected' : ''}`}><span className="spotify-mark">♫</span><div><h3>Spotify</h3><p>{isSpotifyConnected ? `Connected${spotifyUser?.display_name ? ` as ${spotifyUser.display_name}` : ''}` : 'Not connected'}</p></div><span className="connection-state">{isSpotifyConnected ? '● Connected' : '○ Offline'}</span></div>{!isSpotifyConnected && <button className="profile-primary full-width" onClick={onConnectSpotify}>Connect Spotify</button>}<div className="settings-group"><Toggle checked={autoplay} onChange={setAutoplay} label="Autoplay" description="Keep music moving after the current track ends." /></div></section>; }
function AppearanceSection({ isDark, onToggleTheme }: { isDark: boolean; onToggleTheme: () => void }) { return <section className="settings-section"><SectionIntro eyebrow="Appearance" title="Set the atmosphere" description="Choose the look that feels right for your listening space." /><div className="theme-options"><button className={isDark ? 'selected' : ''} onClick={() => { if (!isDark) onToggleTheme(); }}>◐<strong>Dark</strong><small>Low light, focused</small></button><button className={!isDark ? 'selected' : ''} onClick={() => { if (isDark) onToggleTheme(); }}>☼<strong>Light</strong><small>Bright and open</small></button><button className="disabled-option" disabled>◌<strong>System</strong><small>Coming soon</small></button></div><div className="info-note">Animation follows your browser's reduced-motion preference where supported.</div></section>; }
function PrivacySection({ memoryCount, onClearMemory, onReset }: { memoryCount: number; onClearMemory: () => void; onReset: () => void }) { return <section className="settings-section"><SectionIntro eyebrow="Privacy" title="Your data, your say" description="See what is stored and manage the controls that matter." /><div className="privacy-list"><div><span>Microphone</span><strong>Controlled by your browser</strong></div><div><span>Saved memories</span><strong>{memoryCount} items in Zana memory</strong></div><div><span>Profile preferences</span><strong>Stored through your existing profile service</strong></div></div><div className="privacy-actions"><button className="text-danger" onClick={onClearMemory}>Clear memory</button><button className="text-danger" onClick={onReset}>Reset preferences</button></div></section>; }
function SectionIntro({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) { return <div className="section-intro"><p className="section-kicker">{eyebrow}</p><h2>{title}</h2><p>{description}</p></div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="settings-field"><span>{label}</span>{children}</label>; }