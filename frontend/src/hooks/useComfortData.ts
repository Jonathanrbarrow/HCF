import { useCallback, useRef, useState } from 'react';
import { fetchComfortData } from '../api/client';
import type { ComfortGeoJSON } from '../types/comfort';

interface UseComfortDataReturn {
  data: ComfortGeoJSON | null;
  loading: boolean;
  error: string | null;
  analyze: (city: string) => Promise<void>;
}

export function useComfortData(): UseComfortDataReturn {
  const [data, setData] = useState<ComfortGeoJSON | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const analyze = useCallback(async (city: string) => {
    // Cancel any in-flight request to prevent stale data from overwriting
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const geojson = await fetchComfortData(city, undefined, controller.signal);
      // Guard against stale responses from cancelled requests
      if (controller.signal.aborted) return;
      setData(geojson);
    } catch (err) {
      if (controller.signal.aborted) return;
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      setData(null);
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }, []);

  return { data, loading, error, analyze };
}
