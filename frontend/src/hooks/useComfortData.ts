import { useCallback, useState } from 'react';
import { fetchComfortData } from '../api/client';
import type { CityStats, ComfortGeoJSON } from '../types/comfort';

interface UseComfortDataReturn {
  data: ComfortGeoJSON | null;
  stats: CityStats | null;
  loading: boolean;
  error: string | null;
  analyze: (city: string) => Promise<void>;
}

export function useComfortData(): UseComfortDataReturn {
  const [data, setData] = useState<ComfortGeoJSON | null>(null);
  const [stats, setStats] = useState<CityStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(async (city: string) => {
    setLoading(true);
    setError(null);

    try {
      const geojson = await fetchComfortData(city);
      setData(geojson);

      // Compute summary stats
      const scores = geojson.features.map((f) => f.properties.comfort_score);
      if (scores.length > 0) {
        const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
        setStats({
          segments: scores.length,
          avg,
          min: Math.min(...scores),
          max: Math.max(...scores),
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, stats, loading, error, analyze };
}
