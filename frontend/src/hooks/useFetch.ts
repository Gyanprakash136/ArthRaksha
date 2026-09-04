import { useState, useEffect, useCallback } from "react";

export const API_BASE = import.meta.env.VITE_API_URL ?? "";

export interface FetchState<T> {
  data: T | null;
  loading: boolean;
  live: boolean;
  error: string | null;
  refetch: () => void;
}

export function useFetch<T>(path: string, fallback: T | null = null): FetchState<T> {
  const [data, setData]       = useState<T | null>(fallback);
  const [loading, setLoading] = useState(true);
  const [live, setLive]       = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const [tick, setTick]       = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(`${API_BASE}${path}`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d: T) => {
        if (!cancelled) { setData(d); setLive(true); setError(null); setLoading(false); }
      })
      .catch((e: Error) => {
        if (!cancelled) { setData(fallback); setLive(false); setError(e.message); setLoading(false); }
      });
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick]);

  const refetch = useCallback(() => setTick(t => t + 1), []);
  return { data, loading, live, error, refetch };
}
