import React, { useState, useEffect, useRef, useCallback } from 'react';
import { renderToString } from 'react-dom/server';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { Map as LeafletMap, Layer, PathOptions } from 'leaflet';
import type { ComfortGeoJSON, ComfortFeature, ComfortProperties } from '../types/comfort';
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
  wSafety: number;
  wTraffic: number;
  selectedSegment: { lat: number; lon: number; properties: ComfortProperties } | null;
}

// Controller component to handle programmatically flying and opening popups
const MapController: React.FC<{ selectedSegment: ComfortMapProps['selectedSegment'] }> = ({
  selectedSegment,
}) => {
  const map = useMap();

  useEffect(() => {
    if (!selectedSegment) return;
    const { lat, lon, properties } = selectedSegment;

    map.flyTo([lat, lon], 18, { animate: true, duration: 1.2 });

    const popupHtml = renderToString(<SegmentPopup properties={properties} />);
    L.popup()
      .setLatLng([lat, lon])
      .setContent(popupHtml)
      .openOn(map);
  }, [selectedSegment, map]);

  return null;
};

const ComfortMap: React.FC<ComfortMapProps> = ({
  data,
  wNoise,
  wCanopy,
  wHeat,
  wSafety,
  wTraffic,
  selectedSegment,
}) => {
  const mapRef = useRef<LeafletMap | null>(null);
  const [geoJsonKey, setGeoJsonKey] = useState(0);

  // Bump key whenever data or weights change to force GeoJSON layer re-render.
  // Debounce weight changes to avoid destroying/recreating the layer on every
  // slider tick (which causes severe performance issues during dragging).
  useEffect(() => {
    if (!data) return;
    const timer = setTimeout(() => {
      setGeoJsonKey((k) => k + 1);
    }, 150);
    return () => clearTimeout(timer);
  }, [data, wNoise, wCanopy, wHeat, wSafety, wTraffic]);

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
    const { noise_dba, canopy_pct, heat_index, safety_score, traffic_volume } = f.properties;
    // Recompute score with user's current weights for ALL features.
    // intervenedData only patches comfort_score for intervened segments;
    // non-intervened segments retain the server-side score which may not
    // reflect the current weight settings.
    const score = computeComfortScoreClient(noise_dba, canopy_pct, heat_index, safety_score, wNoise, wCanopy, wHeat, wSafety, traffic_volume, wTraffic);
    const dq = f.properties.data_quality;
    const hasDefaults = dq ? Object.values(dq).some((v) => v !== 'real') : false;

    return {
      color: scoreToColor(score),
      weight: hasDefaults ? 2 : 3,
      opacity: hasDefaults ? 0.45 : 0.85,
      dashArray: hasDefaults ? '6 4' : undefined,
    };
  }, [wNoise, wCanopy, wHeat, wSafety, wTraffic]);

  const onEachFeature = useCallback(
    (feature: GeoJSON.Feature, layer: Layer) => {
      const f = feature as unknown as ComfortFeature;
      const { noise_dba, canopy_pct, heat_index, safety_score, traffic_volume } = f.properties;
      const score = computeComfortScoreClient(noise_dba, canopy_pct, heat_index, safety_score, wNoise, wCanopy, wHeat, wSafety, traffic_volume, wTraffic);
      
      const popupHtml = renderToString(
        <SegmentPopup properties={{ ...f.properties, comfort_score: score }} />,
      );
      (layer as L.Path).bindPopup(popupHtml);
    },
    [wNoise, wCanopy, wHeat, wSafety, wTraffic],
  );



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
          key={geoJsonKey}
          data={data}
          style={style}
          onEachFeature={onEachFeature}
        />
      )}
      <MapController selectedSegment={selectedSegment} />
    </MapContainer>
  );
};

export default ComfortMap;
