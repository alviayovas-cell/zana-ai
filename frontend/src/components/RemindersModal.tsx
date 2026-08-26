import React, { useEffect, useMemo, useRef, useState } from 'react';
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
  const [selectedDelay, setSelectedDelay] = useState<number | 'custom'>(5);
  const [isCreating, setIsCreating] = useState(false);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  const [deleteCandidate, setDeleteCandidate] = useState<string | null>(null);
  const [messageError, setMessageError] = useState('');
  const [timeError, setTimeError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const messageInputRef = useRef<HTMLInputElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const quickDelays = [5, 10, 15, 30, 60];

  const sortedReminders = useMemo(
    () => [...reminders].sort((a, b) => a.scheduled_at - b.scheduled_at),
    [reminders]
  );

  useEffect(() => {
    if (!isOpen) return;

    previousFocusRef.current = document.activeElement as HTMLElement | null;
    messageInputRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previousFocusRef.current?.focus();
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
    };
  }, [isOpen, onClose]);

  useEffect(() => () => {
    if (successTimerRef.current) clearTimeout(successTimerRef.current);
  }, []);

  if (!isOpen) return null;

  const handleDelayChange = (value: number | 'custom') => {
    setSelectedDelay(value);
    if (value !== 'custom') {
      setMinutes(value);
      setTimeError('');
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedMessage = message.trim();
    const validMessage = trimmedMessage.length > 0;
    const validMinutes = Number.isFinite(minutes) && minutes >= 1 && minutes <= 1440;

    setMessageError(validMessage ? '' : 'Please enter what you would like to be reminded about.');
    setTimeError(validMinutes ? '' : 'Choose a reminder time between 1 minute and 24 hours.');
    if (!validMessage || !validMinutes) return;

    setIsCreating(true);
    const created = await onCreateReminder(trimmedMessage, minutes * 60);
    setIsCreating(false);

    if (created) {
      setSuccessMessage(`${trimmedMessage} - due ${formatRelativeTime(Date.now() / 1000 + minutes * 60)}`);
      setMessage('');
      setSelectedDelay(5);
      setMinutes(5);
      setMessageError('');
      setTimeError('');
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
      successTimerRef.current = setTimeout(() => setSuccessMessage(''), 4500);
    } else {
      setTimeError('The reminder could not be saved. Please try again.');
    }
  };

  const handleDelete = async (id: string) => {
    setIsDeleting(id);
    const deleted = await onDeleteReminder(id);
    setIsDeleting(null);
    if (deleted) setDeleteCandidate(null);
  };

  return (
    <div className="modal-backdrop reminders-backdrop" onClick={onClose}>
      <div
        className="modal-content reminders-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="reminders-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="reminders-header">
          <div className="reminders-heading">
            <span className="reminders-icon" aria-hidden="true">⏰</span>
            <div>
              <p className="reminders-eyebrow">ZANA / PLANNING</p>
              <h2 id="reminders-title">Reminders</h2>
            </div>
          </div>
          <button className="reminders-close" onClick={onClose} aria-label="Close reminders">×</button>
        </div>
        <div className="reminders-intro">
          <p>Keep the small things moving. Zana will bring them back at the right moment.</p>
        </div>

        <div className="reminders-body">
          <form className="reminder-form" onSubmit={handleCreate} noValidate>
            <div className="reminder-form-heading">
              <div>
                <p className="section-kicker">New reminder</p>
                <h3>What should I remind you about?</h3>
              </div>
              <span className="form-step">01</span>
            </div>
            <input
              ref={messageInputRef}
              id="reminder-message"
              type="text"
              value={message}
              onChange={(e) => { setMessage(e.target.value); if (messageError) setMessageError(''); }}
              placeholder="e.g. Take a break, call Mum..."
              aria-invalid={Boolean(messageError)}
              aria-describedby={messageError ? 'reminder-message-error' : undefined}
            />
            {messageError && <p className="field-error" id="reminder-message-error">{messageError}</p>}

            <div className="time-select">
              <div className="reminder-form-heading time-heading">
                <div>
                  <p className="section-kicker">When should I remind you?</p>
                  <h3>Choose a moment that works</h3>
                </div>
                <span className="form-step">02</span>
              </div>
              <div className="quick-delays" role="group" aria-label="Quick reminder times">
                {quickDelays.map((delay) => (
                  <button
                    key={delay}
                    type="button"
                    className={`delay-chip ${selectedDelay === delay ? 'selected' : ''}`}
                    onClick={() => handleDelayChange(delay)}
                    aria-pressed={selectedDelay === delay}
                  >
                    {delay < 60 ? `${delay} min` : '1 hour'}
                  </button>
                ))}
                <button
                  type="button"
                  className={`delay-chip ${selectedDelay === 'custom' ? 'selected' : ''}`}
                  onClick={() => handleDelayChange('custom')}
                  aria-pressed={selectedDelay === 'custom'}
                >
                  Custom
                </button>
              </div>
              {selectedDelay === 'custom' && (
                <label className="custom-time-label" htmlFor="reminder-minutes">
                  Minutes from now
                  <input
                    id="reminder-minutes"
                    type="number"
                    min="1"
                    max="1440"
                    value={minutes}
                    onChange={(e) => { setMinutes(Number(e.target.value)); setTimeError(''); }}
                    aria-invalid={Boolean(timeError)}
                  />
                </label>
              )}
              {timeError && <p className="field-error">{timeError}</p>}
            </div>

            <div className="reminder-form-actions">
              <button type="button" className="reminders-secondary" onClick={onClose}>Cancel</button>
              <button type="submit" className="reminders-primary" disabled={isCreating}>
                <span aria-hidden="true">+</span>{isCreating ? 'Setting...' : 'Set reminder'}
              </button>
            </div>
          </form>

          <div className="reminders-list">
            <div className="list-heading">
              <div>
                <p className="section-kicker">Your queue</p>
                <h3>Active reminders <span>{reminders.length}</span></h3>
              </div>
              <span className="list-status"><span /> Live</span>
            </div>
            {sortedReminders.length === 0 ? (
              <div className="no-reminders">
                <span className="empty-icon" aria-hidden="true">✦</span>
                <h4>No reminders yet</h4>
                <p>Create one above and Zana will keep track of it for you.</p>
              </div>
            ) : (
              sortedReminders.map((r) => (
                <div key={r.id} className="reminder-card">
                  <div className="reminder-card-mark" aria-hidden="true">⏰</div>
                  <div className="reminder-info">
                    <span className="reminder-msg">{r.message}</span>
                    <span className="reminder-time">{formatRelativeTime(r.scheduled_at)}</span>
                    <span className="reminder-date">{formatScheduledTime(r.scheduled_at)}</span>
                  </div>
                  <div className="reminder-card-actions">
                    {deleteCandidate === r.id ? (
                      <div className="delete-confirmation" role="group" aria-label={`Delete ${r.message}`}>
                        <span>Delete this?</span>
                        <button type="button" onClick={() => setDeleteCandidate(null)}>Cancel</button>
                        <button type="button" className="confirm-delete" onClick={() => handleDelete(r.id)} disabled={isDeleting === r.id}>
                          {isDeleting === r.id ? '...' : 'Delete'}
                        </button>
                      </div>
                    ) : (
                      <button
                        className="btn-delete-reminder"
                        onClick={() => setDeleteCandidate(r.id)}
                        title="Delete reminder"
                        aria-label={`Delete reminder: ${r.message}`}
                      >
                        <span aria-hidden="true">⌫</span>
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
        {successMessage && (
          <div className="reminder-success" role="status" aria-live="polite">
            <span aria-hidden="true">✓</span>
            <div><strong>Reminder set</strong><p>{successMessage}</p></div>
          </div>
        )}
      </div>
    </div>
  );
};

function formatRelativeTime(scheduledAt: number): string {
  const secondsRemaining = Math.round(scheduledAt - Date.now() / 1000);
  if (secondsRemaining <= 0) return 'Due now';
  const minutesRemaining = Math.round(secondsRemaining / 60);
  if (minutesRemaining < 60) return `Due in ${Math.max(1, minutesRemaining)} minute${minutesRemaining === 1 ? '' : 's'}`;
  const hoursRemaining = Math.round(minutesRemaining / 60);
  if (hoursRemaining < 24) return `Due in ${hoursRemaining} hour${hoursRemaining === 1 ? '' : 's'}`;
  const daysRemaining = Math.round(hoursRemaining / 24);
  return `Due in ${daysRemaining} day${daysRemaining === 1 ? '' : 's'}`;
}

function formatScheduledTime(scheduledAt: number): string {
  const date = new Date(scheduledAt * 1000);
  const time = date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const today = new Date();
  const isToday = date.toDateString() === today.toDateString();
  return isToday ? `Today at ${time}` : date.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ` at ${time}`;
}
