import React from 'react';
import { scoreToColor, scoreToLabel } from '../utils/colors';
import type { ComfortProperties } from '../types/comfort';

interface SegmentPopupProps {
  properties: ComfortProperties;
}

const SegmentPopup: React.FC<SegmentPopupProps> = ({ properties }) => {
  const { comfort_score, noise_dba, canopy_height_m, canopy_pct, heat_index, safety_score, street_name, data_quality } =
    properties;
  const color = scoreToColor(comfort_score);
  const label = scoreToLabel(comfort_score);

  const dq = data_quality;
  const hasLimitedData = dq
    ? Object.values(dq).some((v) => v !== 'real')
    : false;

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', minWidth: 160 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#e4e6ed', marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={street_name}>
        {street_name}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 24, fontWeight: 700, color }}>{comfort_score}</span>
        <span style={{ fontSize: 11, color: '#8b8fa3' }}>{label}</span>
      </div>
      <div style={{ fontSize: 13 }}>
        {noise_dba !== null && (
          <>
            🔊 Noise: {noise_dba.toFixed(1)} dBA
            {dq && dq.noise !== 'real' && (
              <span style={{ color: '#f97316', marginLeft: 4 }} title="Estimated noise data">⚠</span>
            )}
            <br />
          </>
        )}
        {canopy_height_m !== null && canopy_pct !== null && (
          <>
            🌳 Canopy: {canopy_height_m.toFixed(1)}m ({canopy_pct.toFixed(0)}% shade)
            {dq && dq.canopy !== 'real' && (
              <span style={{ color: '#f97316', marginLeft: 4 }} title="Estimated canopy data">⚠</span>
            )}
            <br />
          </>
        )}
        {heat_index !== null && (
          <>
            🌡️ Apparent Temp: {heat_index.toFixed(1)}°F
            {dq && dq.heat !== 'real' && (
              <span style={{ color: '#f97316', marginLeft: 4 }} title="Estimated or fixed heat data">⚠</span>
            )}
            <br />
          </>
        )}
        {safety_score !== null && (
          <>
            🛡️ Safety: {safety_score.toFixed(0)}/100
            {dq && dq.safety !== 'real' && (
              <span style={{ color: '#f97316', marginLeft: 4 }} title="Default road safety template applied">⚠</span>
            )}
          </>
        )}
      </div>
      {hasLimitedData && (
        <div
          style={{
            fontSize: 11,
            color: '#f97316',
            marginTop: 8,
            borderTop: '1px solid #333',
            paddingTop: 6,
          }}
        >
          ⚠ Some data estimated
        </div>
      )}
    </div>
  );
};

export default SegmentPopup;
