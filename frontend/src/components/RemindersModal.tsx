import React, { useState } from 'react';
import type { Reminder } from '../hooks/useReminders';
import './RemindersModal.css';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  reminders: Reminder[];
  onCreateReminder: (message: string, delaySeconds: number) => Promise<boolean>;
  onDeleteReminder: (id: string) => Promise<boolean>;
}

export const RemindersModal: React.FC<Props> = ({
  isOpen,
  onClose,
  reminders,
  onCreateReminder,
  onDeleteReminder,
}) => {
  const [message, setMessage] = useState('');
  const [minutes, setMinutes] = useState(5);
  const [isCreating, setIsCreating] = useState(false);

  if (!isOpen) return null;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    setIsCreating(true);
    await onCreateReminder(message.trim(), minutes * 60);
    setMessage('');
    setIsCreating(false);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content reminders-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>⏰ Proactive Reminders</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <form className="reminder-form" onSubmit={handleCreate}>
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="e.g. Study for exam, take a break..."
              required
            />
            <div className="time-select">
              <label>In (minutes):</label>
              <input
                type="number"
                min="1"
                max="1440"
                value={minutes}
                onChange={(e) => setMinutes(Number(e.target.value))}
              />
              <button type="submit" className="btn-primary" disabled={isCreating}>
                {isCreating ? 'Saving...' : 'Add Reminder'}
              </button>
            </div>
          </form>

          <div className="reminders-list">
            <h4>Active Scheduled Reminders ({reminders.length})</h4>
            {reminders.length === 0 ? (
              <p className="no-reminders">No scheduled reminders. Add one above!</p>
            ) : (
              reminders.map((r) => (
                <div key={r.id} className="reminder-card">
                  <div className="reminder-info">
                    <span className="reminder-msg">{r.message}</span>
                    <span className="reminder-time">
                      Scheduled for: {new Date(r.scheduled_at * 1000).toLocaleTimeString()}
                    </span>
                  </div>
                  <button
                    className="btn-delete-reminder"
                    onClick={() => onDeleteReminder(r.id)}
                    title="Cancel reminder"
                  >
                    🗑
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
