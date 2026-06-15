import { useEffect, useRef } from 'react';

export function usePolling(callback, delay, enabled = true) {
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled || !delay) return undefined;
    const intervalId = window.setInterval(() => callbackRef.current(), delay);
    return () => window.clearInterval(intervalId);
  }, [delay, enabled]);
}
