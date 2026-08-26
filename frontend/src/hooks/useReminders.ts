import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../services/api';

export interface Reminder {
  id: string;
  user_id: string;
  message: string;
  scheduled_at: number;
  status: string;
}

export function useReminders(userId: string = 'default-user') {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [dueAlerts, setDueAlerts] = useState<Reminder[]>([]);

  const fetchReminders = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/reminders?user_id=${userId}`);
      if (res.ok) {
        const data = await res.json();
        setReminders(data.reminders || []);
      }
    } catch {}
  }, [userId]);

  const checkDueReminders = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/reminders/due`);
      if (res.ok) {
        const data = await res.json();
        if (data.due && data.due.length > 0) {
          setDueAlerts((prev) => [...prev, ...data.due]);
        }
      }
    } catch {}
  }, []);

  const createReminder = useCallback(
    async (message: string, delaySeconds: number) => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/reminders`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId, message, delay_seconds: delaySeconds }),
        });
        if (res.ok) {
          await fetchReminders();
          return true;
        }
      } catch {}
      return false;
    },
    [userId, fetchReminders]
  );

  const deleteReminder = useCallback(
    async (reminderId: string) => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/reminders/${reminderId}?user_id=${userId}`, {
          method: 'DELETE',
        });
        if (res.ok) {
          await fetchReminders();
          return true;
        }
      } catch {}
      return false;
    },
    [userId, fetchReminders]
  );

  const dismissAlert = useCallback((id: string) => {
    setDueAlerts((prev) => prev.filter((r) => r.id !== id));
  }, []);

  useEffect(() => {
    fetchReminders();
    const interval = setInterval(() => {
      checkDueReminders();
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchReminders, checkDueReminders]);

  return { reminders, dueAlerts, createReminder, deleteReminder, dismissAlert, refresh: fetchReminders };
}
