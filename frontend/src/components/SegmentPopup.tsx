import React from 'react';
import { scoreToColor, scoreToLabel } from '../utils/colors';
import type { ComfortProperties } from '../types/comfort';

interface SegmentPopupProps {
  properties: ComfortProperties;
}

const SegmentPopup: React.FC<SegmentPopupProps> = ({ properties }) => {
  const { comfort_score, noise_dba, canopy_height_m, canopy_pct, data_quality } =
    properties;
  const color = scoreToColor(comfort_score);
  const label = scoreToLabel(comfort_score);

  const dq = data_quality;
  const hasLimitedData = dq
    ? Object.values(dq).some((v) => v !== 'real')
    : false;

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', minWidth: 160 }}>
      <div style={{ fontSize: 24, fontWeight: 700, color }}>{comfort_score}</div>
      <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 13 }}>
        {noise_dba !== null && (
          <>
            🔊 Noise: {noise_dba.toFixed(1)} dBA
            {dq && dq.noise !== 'real' && (
              <span style={{ color: '#f97316', marginLeft: 4 }}>⚠</span>
            )}
            <br />
          </>
        )}
        {canopy_height_m !== null && canopy_pct !== null && (
          <>
            🌳 Canopy: {canopy_height_m.toFixed(1)}m ({canopy_pct.toFixed(0)}%
            shade)
            {dq && dq.canopy !== 'real' && (
              <span style={{ color: '#f97316', marginLeft: 4 }}>⚠</span>
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
