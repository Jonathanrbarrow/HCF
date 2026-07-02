import type { ComfortGeoJSON } from '../types/comfort';
import { DEFAULT_MAX_SEGMENTS } from '../utils/constants';

/** Resolve the API base URL. VITE_API_URL env var takes priority, otherwise same-origin. */
function getBaseUrl(): string {
  const env = import.meta.env.VITE_API_URL;
  if (env) return env.replace(/\/+$/, '');
  return '';
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/**
 * Fetch comfort-scored GeoJSON for a given city.
 * @param city - Human-readable city query, e.g. "Denver, Colorado, USA"
 * @param maxSegments - Cap the number of returned segments (default 200)
 */
export async function fetchComfortData(
  city: string,
  maxSegments: number = DEFAULT_MAX_SEGMENTS,
): Promise<ComfortGeoJSON> {
  const base = getBaseUrl();
  const params = new URLSearchParams({
    city,
    max_segments: String(maxSegments),
  });

  const resp = await fetch(`${base}/api/v1/comfort?${params.toString()}`);

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore parse errors */
    }
    throw new ApiError(detail, resp.status);
  }

  return resp.json() as Promise<ComfortGeoJSON>;
}
