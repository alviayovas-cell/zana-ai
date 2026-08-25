import React, { useState, useEffect } from 'react';
import './ProfileModal.css';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  userId?: string;
}

export const ProfileModal: React.FC<Props> = ({ isOpen, onClose, userId = 'default-user' }) => {
  const [displayName, setDisplayName] = useState('Music Enthusiast');
  const [language, setLanguage] = useState('en');
  const [timezone, setTimezone] = useState('UTC');
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [wakeWordEnabled, setWakeWordEnabled] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetch(`http://localhost:8000/api/profile?user_id=${userId}`)
        .then((res) => res.json())
        .then((data) => {
          if (data) {
            setDisplayName(data.display_name || 'Music Enthusiast');
            setLanguage(data.preferred_language || 'en');
            setTimezone(data.timezone || 'UTC');
            setTtsEnabled(data.tts_enabled || false);
            setWakeWordEnabled(data.wake_word_enabled ?? true);
          }
        })
        .catch(() => {});
    }
  }, [isOpen, userId]);

  if (!isOpen) return null;

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await fetch('http://localhost:8000/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          display_name: displayName,
          preferred_language: language,
          timezone,
          tts_enabled: ttsEnabled,
          wake_word_enabled: wakeWordEnabled,
        }),
      });
      onClose();
    } catch (err) {
      console.error('Save profile error:', err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>👤 Personal Profile &amp; Settings</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div className="form-group">
            <label>Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your Name"
            />
          </div>

          <div className="form-group">
            <label>Preferred Language</label>
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              <option value="en">English (US)</option>
              <option value="ta">Tamil (தமிழ்)</option>
              <option value="hi">Hindi (हिंदी)</option>
            </select>
          </div>

          <div className="form-group">
            <label>Timezone</label>
            <input
              type="text"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              placeholder="e.g. UTC, Asia/Kolkata"
            />
          </div>

          <div className="form-toggle-group">
            <label>
              <input
                type="checkbox"
                checked={wakeWordEnabled}
                onChange={(e) => setWakeWordEnabled(e.target.checked)}
              />
              Enable "Hey Zana" Wake Word Detection
            </label>
          </div>

          <div className="form-toggle-group">
            <label>
              <input
                type="checkbox"
                checked={ttsEnabled}
                onChange={(e) => setTtsEnabled(e.target.checked)}
              />
              Enable Voice Output (Text-to-Speech)
            </label>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={handleSave} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </div>
    </div>
  );
};
