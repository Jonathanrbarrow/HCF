import React, { useEffect, useRef, useCallback, useMemo } from 'react';
import { renderToString } from 'react-dom/server';
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import type { Map as LeafletMap, Layer, PathOptions } from 'leaflet';
import type { ComfortGeoJSON, ComfortFeature } from '../types/comfort';
import { scoreToColor } from '../utils/colors';
import { computeComfortScoreClient } from '../utils/scoring';
import {
  DEFAULT_CENTER,
  DEFAULT_ZOOM,
  TILE_URL,
  TILE_ATTRIBUTION,
  TILE_SUBDOMAINS,
  TILE_MAX_ZOOM,
} from '../utils/constants';
import SegmentPopup from './SegmentPopup';

import 'leaflet/dist/leaflet.css';

interface ComfortMapProps {
  data: ComfortGeoJSON | null;
  wNoise: number;
  wCanopy: number;
  wHeat: number;
}

const ComfortMap: React.FC<ComfortMapProps> = ({ data, wNoise, wCanopy, wHeat }) => {
  const mapRef = useRef<LeafletMap | null>(null);
  const geoJsonKey = useRef(0);

  // Bump key whenever data or weights change to force GeoJSON layer re-render
  useEffect(() => {
    geoJsonKey.current += 1;
  }, [data, wNoise, wCanopy, wHeat]);

  // Fit bounds when data arrives
  useEffect(() => {
    if (!data || !mapRef.current) return;
    const map = mapRef.current;

    // Small delay to let the GeoJSON layer render
    const timer = setTimeout(() => {
      let allBounds: L.LatLngBounds | null = null;
      map.eachLayer((layer: Layer) => {
        if ('getBounds' in layer && typeof (layer as { getBounds: () => L.LatLngBounds }).getBounds === 'function') {
          const bounds = (layer as { getBounds: () => L.LatLngBounds }).getBounds();
          if (bounds.isValid()) {
            allBounds = allBounds ? allBounds.extend(bounds) : bounds;
          }
        }
      });
      if (allBounds) {
        map.fitBounds(allBounds, { padding: [30, 30] });
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [data]);

  const style = useCallback((feature: GeoJSON.Feature | undefined): PathOptions => {
    if (!feature) return {};
    const f = feature as unknown as ComfortFeature;
    const { noise_dba, canopy_pct, heat_index } = f.properties;
    const score = computeComfortScoreClient(noise_dba, canopy_pct, heat_index, wNoise, wCanopy, wHeat);
    const dq = f.properties.data_quality;
    const hasDefaults = dq ? Object.values(dq).some((v) => v !== 'real') : false;

    return {
      color: scoreToColor(score),
      weight: hasDefaults ? 2 : 3,
      opacity: hasDefaults ? 0.45 : 0.85,
      dashArray: hasDefaults ? '6 4' : undefined,
    };
  }, [wNoise, wCanopy, wHeat]);

  const onEachFeature = useCallback(
    (feature: GeoJSON.Feature, layer: Layer) => {
      const f = feature as unknown as ComfortFeature;
      const { noise_dba, canopy_pct, heat_index } = f.properties;
      const score = computeComfortScoreClient(noise_dba, canopy_pct, heat_index, wNoise, wCanopy, wHeat);
      
      const popupHtml = renderToString(
        <SegmentPopup properties={{ ...f.properties, comfort_score: score }} />,
      );
      (layer as L.Path).bindPopup(popupHtml);
    },
    [wNoise, wCanopy, wHeat],
  );

  // Memoize the data key so GeoJSON only re-renders when data or weights actually change
  const dataKey = useMemo(() => geoJsonKey.current, [data, wNoise, wCanopy, wHeat]);

  return (
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={DEFAULT_ZOOM}
      id="map"
      ref={mapRef}
      zoomControl
      attributionControl
    >
      <TileLayer
        url={TILE_URL}
        attribution={TILE_ATTRIBUTION}
        subdomains={TILE_SUBDOMAINS}
        maxZoom={TILE_MAX_ZOOM}
      />
      {data && (
        <GeoJSON
          key={dataKey}
          data={data}
          style={style}
          onEachFeature={onEachFeature}
        />
      )}
    </MapContainer>
  );
};

export default ComfortMap;
