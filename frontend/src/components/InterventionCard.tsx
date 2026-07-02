import React from 'react';
import type { ComfortProperties } from '../types/comfort';
import { scoreToColor } from '../utils/colors';

interface InterventionCardProps {
  segment: {
    lat: number;
    lon: number;
    properties: ComfortProperties;
    id: string;
  } | null;
  intervention: {
    canopy_pct?: number;
    noise_dba?: number;
    safety_score?: number;
  } | undefined;
  onUpdateIntervention: (id: string, updates: { canopy_pct?: number; noise_dba?: number; safety_score?: number } | null) => void;
  onClose: () => void;
}

const InterventionCard: React.FC<InterventionCardProps> = ({
  segment,
  intervention,
  onUpdateIntervention,
  onClose,
}) => {
  if (!segment) return null;

  const { street_name, noise_dba, canopy_pct, safety_score, comfort_score } = segment.properties;

  // Active values (either proposed or original)
  const activeCanopy = intervention?.canopy_pct !== undefined ? intervention.canopy_pct : (canopy_pct || 20);
  const activeNoise = intervention?.noise_dba !== undefined ? intervention.noise_dba : (noise_dba || 65);
  const activeSafety = intervention?.safety_score !== undefined ? intervention.safety_score : (safety_score || 70);

  const isIntervened = intervention !== undefined;

  const handleReset = () => {
    onUpdateIntervention(segment.id, null);
  };

  const handleCanopyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onUpdateIntervention(segment.id, {
      ...intervention,
      canopy_pct: Number(e.target.value),
    });
  };

  const handleNoiseLevel = (level: 'none' | 'minor' | 'major') => {
    let targetNoise = noise_dba || 65;
    if (level === 'minor') targetNoise = 55;
    if (level === 'major') targetNoise = 45;

    onUpdateIntervention(segment.id, {
      ...intervention,
      noise_dba: targetNoise,
    });
  };

  const handleSidewalkUpgrade = (active: boolean) => {
    onUpdateIntervention(segment.id, {
      ...intervention,
      safety_score: active ? 100 : (safety_score || 70),
    });
  };

  return (
    <div className="intervention-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>🛠️ Audit & Design Workbench</h3>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      <div className="workbench-street">
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{street_name}</span>
        <span style={{ fontSize: 10, color: 'var(--text-secondary)' }}>ID: {segment.id.split('#')[1]}</span>
      </div>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', margin: '12px 0', padding: '10px', background: 'rgba(255,255,255,0.03)', borderRadius: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Baseline Comfort</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: scoreToColor(comfort_score) }}>{comfort_score.toFixed(0)}</div>
        </div>
        <div style={{ borderLeft: '1px solid var(--border)', height: 32 }} />
        <div style={{ flex: 1, paddingLeft: 8 }}>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Design Status</div>
          <div style={{ fontSize: 12, fontWeight: 600, color: isIntervened ? 'var(--accent)' : 'var(--text-secondary)', marginTop: 4 }}>
            {isIntervened ? '✨ Active Proposal' : 'Original Baseline'}
          </div>
        </div>
      </div>

      <div className="workbench-section">
        <div className="workbench-row">
          <label>🌳 Proposed Tree Canopy</label>
          <span>{activeCanopy.toFixed(0)}% shade</span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={activeCanopy}
          onChange={handleCanopyChange}
          style={{ width: '100%', marginTop: 4 }}
        />
      </div>

      <div className="workbench-section">
        <div className="workbench-row" style={{ marginBottom: 6 }}>
          <label>🔊 Proposed Traffic Calming</label>
          <span>{activeNoise.toFixed(0)} dBA</span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            className={`btn-pill ${activeNoise >= 60 ? 'active' : ''}`}
            onClick={() => handleNoiseLevel('none')}
          >
            None
          </button>
          <button
            className={`btn-pill ${activeNoise >= 50 && activeNoise < 60 ? 'active' : ''}`}
            onClick={() => handleNoiseLevel('minor')}
          >
            Minor (-10dB)
          </button>
          <button
            className={`btn-pill ${activeNoise < 50 ? 'active' : ''}`}
            onClick={() => handleNoiseLevel('major')}
          >
            Major (-20dB)
          </button>
        </div>
      </div>

      <div className="workbench-section">
        <div className="workbench-row" style={{ marginBottom: 6 }}>
          <label>🛡️ Proposed Sidewalk Upgrade</label>
          <span>{activeSafety === 100 ? 'Complete Sidewalks' : 'Original Layout'}</span>
        </div>
        <button
          className={`btn-pill ${activeSafety === 100 ? 'active' : ''}`}
          onClick={() => handleSidewalkUpgrade(activeSafety !== 100)}
          style={{ width: '100%' }}
        >
          {activeSafety === 100 ? '✨ Upgraded to Complete Streets' : 'Upgrade to Complete Streets'}
        </button>
      </div>

      {isIntervened && (
        <button className="reset-btn" onClick={handleReset}>
          Reset to Baseline
        </button>
      )}
    </div>
  );
};

export default InterventionCard;
