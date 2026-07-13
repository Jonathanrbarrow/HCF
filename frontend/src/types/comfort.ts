/** GeoJSON feature properties returned by the HCF backend */
export interface DataQuality {
  noise: 'real' | 'default' | 'unavailable' | 'disabled';
  canopy: 'real' | 'default' | 'unavailable' | 'disabled';
  heat: 'real' | 'default' | 'unavailable' | 'fixed' | 'disabled';
  safety: 'real' | 'default' | 'unavailable' | 'disabled';
  traffic: 'real' | 'default' | 'unavailable' | 'disabled';
  aqi: 'real' | 'default' | 'unavailable' | 'disabled';
}

export interface ComfortProperties {
  comfort_score: number;
  noise_dba: number | null;
  canopy_height_m: number | null;
  canopy_pct: number | null;
  heat_index: number | null;
  safety_score: number | null;
  traffic_volume: number | null;
  aqi: number | null;
  street_name: string;
  data_quality?: DataQuality;
}

export type ComfortGeometry =
  | GeoJSON.LineString
  | GeoJSON.MultiLineString;

export interface ComfortFeature {
  type: 'Feature';
  geometry: ComfortGeometry;
  properties: ComfortProperties;
}

export interface ComfortMetadata {
  place: string;
  total_segments: number;
  elapsed_seconds?: number;
  from_cache?: boolean;
  data_note?: string;
}

export interface ComfortGeoJSON {
  type: 'FeatureCollection';
  features: ComfortFeature[];
  metadata?: ComfortMetadata;
}

export interface CityStats {
  segments: number;
  avg: number;
  min: number;
  max: number;
  baselineAvg: number;
}
