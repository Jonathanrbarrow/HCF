/** GeoJSON feature properties returned by the HCF backend */
export interface DataQuality {
  noise: 'real' | 'default' | 'unavailable';
  canopy: 'real' | 'default' | 'unavailable';
  heat: 'real' | 'default' | 'unavailable' | 'fixed';
}

export interface ComfortProperties {
  comfort_score: number;
  noise_dba: number | null;
  canopy_height_m: number | null;
  canopy_pct: number | null;
  heat_index: number | null;
  data_quality?: DataQuality;
}

export interface ComfortFeature {
  type: 'Feature';
  geometry: GeoJSON.Geometry;
  properties: ComfortProperties;
}

export interface ComfortGeoJSON {
  type: 'FeatureCollection';
  features: ComfortFeature[];
}

export interface CityStats {
  segments: number;
  avg: number;
  min: number;
  max: number;
}
