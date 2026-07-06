import { useCallback, useState } from 'react';
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

  const analyze = useCallback(async (city: string) => {
    setLoading(true);
    setError(null);

    try {
      const geojson = await fetchComfortData(city);
      setData(geojson);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, analyze };
}
