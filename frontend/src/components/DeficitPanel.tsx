import React, { useMemo } from 'react';
import type { ComfortGeoJSON, ComfortFeature } from '../types/comfort';
import { computeComfortScoreClient } from '../utils/scoring';
import { scoreToColor, scoreToLabel } from '../utils/colors';

interface DeficitPanelProps {
  data: ComfortGeoJSON | null;
  wNoise: number;
  wCanopy: number;
  wHeat: number;
  onSelectSegment: (lat: number, lon: number, properties: any) => void;
}

const DeficitPanel: React.FC<DeficitPanelProps> = ({
  data,
  wNoise,
  wCanopy,
  wHeat,
  onSelectSegment,
}) => {
  // Sort segments by comfort score (ascending - worst first) and pick top 10
  const worstSegments = useMemo(() => {
    if (!data || data.features.length === 0) return [];

    const scoredFeatures = data.features.map((f) => {
      const { noise_dba, canopy_pct, heat_index } = f.properties;
      const score = computeComfortScoreClient(
        noise_dba,
        canopy_pct,
        heat_index,
        wNoise,
        wCanopy,
        wHeat,
      );
      return {
        feature: f,
        score,
      };
    });

    // Sort ascending
    scoredFeatures.sort((a, b) => a.score - b.score);

    // Pick top 10
    return scoredFeatures.slice(0, 10);
  }, [data, wNoise, wCanopy, wHeat]);

  // Identify the primary environmental stressor for a segment
  const getPrimaryStressor = (f: ComfortFeature) => {
    const { noise_dba, canopy_pct, heat_index } = f.properties;

    // Normalize penalties to see which is highest
    const noisePenalty = noise_dba !== null ? Math.max(0, (noise_dba - 45) / 35) : 0.14;
    const canopyPenalty = 1.0 - ((canopy_pct !== null ? canopy_pct : 20.0) / 100.0);
    const heatPenalty = heat_index !== null ? Math.max(0, (heat_index - 75) / 35) : 0.28;

    const weightedNoise = noisePenalty * wNoise;
    const weightedCanopy = canopyPenalty * wCanopy;
    const weightedHeat = heatPenalty * wHeat;

    const maxPenalty = Math.max(weightedNoise, weightedCanopy, weightedHeat);

    if (maxPenalty === weightedNoise && noise_dba !== null) {
      return `🔊 Noise: ${noise_dba.toFixed(0)} dBA`;
    }
    if (maxPenalty === weightedCanopy && canopy_pct !== null) {
      return `🌳 Low Shade: ${canopy_pct.toFixed(0)}%`;
    }
    if (maxPenalty === weightedHeat && heat_index !== null) {
      return `🌡️ Heat: ${heat_index.toFixed(0)}°F`;
    }
    return 'Multiple stressors';
  };

  const handleItemClick = (f: ComfortFeature, score: number) => {
    // Find segment midpoint to fly to
    const geom = f.geometry;
    let lat = 0;
    let lon = 0;

    if (geom.type === 'LineString') {
      const coords = geom.coordinates;
      const midIdx = Math.floor(coords.length / 2);
      lon = coords[midIdx][0];
      lat = coords[midIdx][1];
    } else if (geom.type === 'MultiLineString') {
      const line = geom.coordinates[0];
      const midIdx = Math.floor(line.length / 2);
      lon = line[midIdx][0];
      lat = line[midIdx][1];
    }

    if (lat && lon) {
      onSelectSegment(lat, lon, { ...f.properties, comfort_score: score });
    }
  };

  if (!data) return null;

  return (
    <div className="deficit-panel">
      <h3>⚠️ High-Stress Corridors</h3>
      <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 12 }}>
        Lowest scored street segments in view. Click to inspect on map.
      </p>
      <div className="deficit-list">
        {worstSegments.map(({ feature, score }, idx) => {
          const color = scoreToColor(score);
          const label = scoreToLabel(score);
          const name = feature.properties.street_name || 'Unnamed Path';
          const stressor = getPrimaryStressor(feature);

          return (
            <div
              key={idx}
              className="deficit-item"
              onClick={() => handleItemClick(feature, score)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span className="street-title">{name}</span>
                <span
                  className="score-badge"
                  style={{ backgroundColor: color + '15', color: color, borderColor: color }}
                >
                  {score}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-secondary)' }}>
                <span>{label} comfort</span>
                <span style={{ color: 'var(--orange)' }}>{stressor}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DeficitPanel;
