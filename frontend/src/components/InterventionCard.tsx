import React from 'react';
import type { ComfortProperties } from '../types/comfort';
import { scoreToColor } from '../utils/colors';
import { computeComfortScoreClient } from '../utils/scoring';

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
    heat_index?: number;
    traffic_volume?: number;
  } | undefined;
  onUpdateIntervention: (id: string, updates: {
    canopy_pct?: number;
    noise_dba?: number;
    safety_score?: number;
    heat_index?: number;
    traffic_volume?: number;
  } | null) => void;
  onClose: () => void;
  wNoise: number;
  wCanopy: number;
  wHeat: number;
  wSafety: number;
  wTraffic: number;
}

const InterventionCard: React.FC<InterventionCardProps> = ({
  segment,
  intervention,
  onUpdateIntervention,
  onClose,
  wNoise,
  wCanopy,
  wHeat,
  wSafety,
  wTraffic,
}) => {
  if (!segment) return null;

  const { street_name, noise_dba, canopy_pct, safety_score, heat_index, traffic_volume } = segment.properties;

  // Active values (either proposed or original)
  const activeCanopy = intervention?.canopy_pct !== undefined ? intervention.canopy_pct : (canopy_pct ?? 20);
  const activeNoise = intervention?.noise_dba !== undefined ? intervention.noise_dba : (noise_dba ?? 65);
  const activeSafety = intervention?.safety_score !== undefined ? intervention.safety_score : (safety_score ?? 70);
  const activeHeat = intervention?.heat_index !== undefined ? intervention.heat_index : (heat_index ?? 85);
  const activeTraffic = intervention?.traffic_volume !== undefined ? intervention.traffic_volume : (traffic_volume ?? null);

  const isIntervened = intervention !== undefined;

  // Recompute comfort score from active values so it updates after interventions
  const liveScore = computeComfortScoreClient(
    activeNoise,
    activeCanopy,
    activeHeat,
    activeSafety,
    wNoise,
    wCanopy,
    wHeat,
    wSafety,
    activeTraffic,
    wTraffic,
  );

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
    let targetNoise = noise_dba ?? 65;
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
      safety_score: active ? 100 : (safety_score ?? 70),
    });
  };

  const handleHeatIntervention = (level: 'none' | 'shade' | 'cool_pavement' | 'combined') => {
    const base = heat_index ?? 85;
    let target = base;
    // Shade structures reduce apparent temp by ~5-8°F (FHWA research)
    if (level === 'shade') target = base - 7;
    // Cool pavement coatings reduce by ~5°F (EPA cool pavement guide)
    if (level === 'cool_pavement') target = base - 5;
    // Combined: shade + cool pavement + misting
    if (level === 'combined') target = base - 15;
    target = Math.max(target, 60); // floor at comfortable

    onUpdateIntervention(segment.id, {
      ...intervention,
      heat_index: level === 'none' ? base : target,
    });
  };

  const handleTrafficCalming = (level: 'none' | 'minor' | 'major') => {
    const base = traffic_volume ?? 5000;
    let target = base;
    // Road diets / lane reductions typically reduce volume 10-20%
    if (level === 'minor') target = Math.round(base * 0.7);
    // Full pedestrianization / traffic diversion
    if (level === 'major') target = Math.round(base * 0.3);

    onUpdateIntervention(segment.id, {
      ...intervention,
      traffic_volume: level === 'none' ? base : target,
    });
  };

  // Cost estimation
  const costItems: { label: string; cost: number }[] = [];
  const baseCanopy = canopy_pct ?? 20;
  if (activeCanopy > baseCanopy) {
    costItems.push({ label: '🌳 Tree Planting', cost: Math.ceil((activeCanopy - baseCanopy) / 10) * 2500 });
  }
  const baseNoise = noise_dba ?? 65;
  if (activeNoise < baseNoise) {
    costItems.push({ label: '🔊 Noise Barrier', cost: activeNoise <= 45 ? 45000 : 15000 });
  }
  const baseSafety = safety_score ?? 70;
  if (activeSafety === 100 && baseSafety < 100) {
    costItems.push({ label: '🛡️ Sidewalk Upgrade', cost: 35000 });
  }
  const baseHeat = heat_index ?? 85;
  if (activeHeat < baseHeat) {
    const heatDelta = baseHeat - activeHeat;
    if (heatDelta >= 12) costItems.push({ label: '🌡️ Shade + Cool Pavement', cost: 75000 });
    else if (heatDelta >= 6) costItems.push({ label: '🌡️ Shade Structures', cost: 40000 });
    else costItems.push({ label: '🌡️ Cool Pavement', cost: 25000 });
  }
  const baseTraffic = traffic_volume ?? 5000;
  if (activeTraffic !== null && activeTraffic < baseTraffic) {
    const reduction = 1 - (activeTraffic / baseTraffic);
    costItems.push({ label: '🚗 Traffic Calming', cost: reduction > 0.5 ? 120000 : 50000 });
  }
  const totalCost = costItems.reduce((sum, item) => sum + item.cost, 0);

  return (
    <div className="intervention-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>🛠️ Audit & Design Workbench</h3>
        <button className="close-btn" onClick={onClose} aria-label="Close workbench">×</button>
      </div>

      <div className="workbench-street">
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{street_name}</span>
        <span style={{ fontSize: 10, color: 'var(--text-secondary)' }}>ID: {segment.id.split('#')[1]}</span>
      </div>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', margin: '12px 0', padding: '10px', background: 'rgba(255,255,255,0.03)', borderRadius: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Baseline Comfort</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: scoreToColor(liveScore) }}>{liveScore}</div>
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
          aria-label="Proposed tree canopy percentage"
        />
      </div>

      <div className="workbench-section">
        <div className="workbench-row" style={{ marginBottom: 6 }}>
          <label>🔊 Proposed Noise Reduction</label>
          <span>{activeNoise.toFixed(0)} dBA</span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            className={`btn-pill ${activeNoise >= (noise_dba ?? 65) ? 'active' : ''}`}
            onClick={() => handleNoiseLevel('none')}
            aria-label="No noise reduction"
          >
            None
          </button>
          <button
            className={`btn-pill ${activeNoise < (noise_dba ?? 65) && activeNoise >= 50 ? 'active' : ''}`}
            onClick={() => handleNoiseLevel('minor')}
            aria-label="Minor noise reduction"
          >
            Minor (-10dB)
          </button>
          <button
            className={`btn-pill ${activeNoise < 50 ? 'active' : ''}`}
            onClick={() => handleNoiseLevel('major')}
            aria-label="Major noise reduction"
          >
            Major (-20dB)
          </button>
        </div>
      </div>

      {heat_index !== null && (
        <div className="workbench-section">
          <div className="workbench-row" style={{ marginBottom: 6 }}>
            <label>🌡️ Proposed Cooling</label>
            <span>{activeHeat.toFixed(0)}°F peak</span>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <button
              className={`btn-pill ${activeHeat >= baseHeat ? 'active' : ''}`}
              onClick={() => handleHeatIntervention('none')}
            >
              None
            </button>
            <button
              className={`btn-pill ${activeHeat < baseHeat && activeHeat > baseHeat - 6 ? 'active' : ''}`}
              onClick={() => handleHeatIntervention('cool_pavement')}
            >
              Cool Pavement (-5°F)
            </button>
            <button
              className={`btn-pill ${activeHeat <= baseHeat - 6 && activeHeat > baseHeat - 12 ? 'active' : ''}`}
              onClick={() => handleHeatIntervention('shade')}
            >
              Shade Structures (-7°F)
            </button>
            <button
              className={`btn-pill ${activeHeat <= baseHeat - 12 ? 'active' : ''}`}
              onClick={() => handleHeatIntervention('combined')}
            >
              Combined (-15°F)
            </button>
          </div>
        </div>
      )}

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

      {traffic_volume !== null && (
        <div className="workbench-section">
          <div className="workbench-row" style={{ marginBottom: 6 }}>
            <label>🚗 Proposed Traffic Calming</label>
            <span>{activeTraffic !== null ? activeTraffic.toLocaleString() : '—'} AADT</span>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              className={`btn-pill ${activeTraffic !== null && activeTraffic >= baseTraffic ? 'active' : ''}`}
              onClick={() => handleTrafficCalming('none')}
            >
              None
            </button>
            <button
              className={`btn-pill ${activeTraffic !== null && activeTraffic < baseTraffic && activeTraffic > baseTraffic * 0.5 ? 'active' : ''}`}
              onClick={() => handleTrafficCalming('minor')}
            >
              Road Diet (-30%)
            </button>
            <button
              className={`btn-pill ${activeTraffic !== null && activeTraffic <= baseTraffic * 0.5 ? 'active' : ''}`}
              onClick={() => handleTrafficCalming('major')}
            >
              Diversion (-70%)
            </button>
          </div>
        </div>
      )}

      {costItems.length > 0 && (
        <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 8, padding: 10, marginBottom: 8 }}>
          <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 8 }}>💰 Estimated Cost</div>
          {costItems.map((item) => (
            <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
              <span style={{ color: 'var(--text-primary)' }}>${item.cost.toLocaleString()}</span>
            </div>
          ))}
          <div style={{ borderTop: '1px solid var(--border)', marginTop: 6, paddingTop: 6, display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
            <span style={{ fontWeight: 700 }}>Total</span>
            <span style={{ fontWeight: 700, color: 'var(--accent)' }}>${totalCost.toLocaleString()}</span>
          </div>
          <div style={{ fontSize: 9, color: 'var(--text-secondary)', marginTop: 6, fontStyle: 'italic' }}>Rough planning estimate only</div>
        </div>
      )}

      {isIntervened && (
        <button className="reset-btn" onClick={handleReset}>
          Reset to Baseline
        </button>
      )}
    </div>
  );
};

export default InterventionCard;
