/** GeoJSON feature properties returned by the HCF backend */
export interface DataQuality {
  noise: 'real' | 'default' | 'estimated';
  canopy: 'real' | 'default' | 'estimated';
  shade: 'real' | 'default' | 'estimated';
}

export interface ComfortProperties {
  comfort_score: number;
  noise_dba: number | null;
  canopy_height_m: number | null;
  canopy_pct: number | null;
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
