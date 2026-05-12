import { useEffect, useRef } from 'react';
import { backtestAPI } from '../api/client';

const POLL_INTERVAL = 2000;
const TERMINAL_STATUSES = ['completed', 'failed'];

export default function StatusPoller({ backtestId, onUpdate, onComplete }) {
  const timerRef = useRef(null);
  const activeRef = useRef(true);
  const onUpdateRef = useRef(onUpdate);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onUpdateRef.current = onUpdate;
    onCompleteRef.current = onComplete;
  }, [onUpdate, onComplete]);

  useEffect(() => {
    if (!backtestId) return;
    activeRef.current = true;

    const poll = async () => {
      if (!activeRef.current) return;
      try {
        const res = await backtestAPI.getById(backtestId);
        const data = res.data;
        onUpdateRef.current?.(data);
        if (TERMINAL_STATUSES.includes(data.status)) {
          activeRef.current = false;
          onCompleteRef.current?.(data);
          return;
        }
      } catch (err) {
        console.error('Poll error:', err);
      }
      if (activeRef.current) {
        timerRef.current = setTimeout(poll, POLL_INTERVAL);
      }
    };

    // First poll immediately
    poll();

    return () => {
      activeRef.current = false;
      clearTimeout(timerRef.current);
    };
  }, [backtestId]);

  return null;
}
