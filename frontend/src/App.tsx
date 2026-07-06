import React, { useState, useMemo, useEffect, useRef } from 'react';
import type { ComfortProperties } from './types/comfort';
import SearchBar from './components/SearchBar';
import ComfortMap from './components/Map';
import Legend from './components/Legend';
import StatsBar from './components/StatsBar';
import DeficitPanel from './components/DeficitPanel';
import InterventionCard from './components/InterventionCard';
import EmptyState from './components/EmptyState';
import { useComfortData } from './hooks/useComfortData';
import { computeComfortScoreClient } from './utils/scoring';
import type { ComfortFeature } from './types/comfort';

// Helper to generate a unique client-side ID for a street segment based on properties + coordinates
const getSegmentId = (f: ComfortFeature): string => {
  const geom = f.geometry;
  if (geom.type === 'MultiLineString') {
    const firstCoord = geom.coordinates[0][0];
    return `${f.properties.street_name}#${firstCoord[0].toFixed(5)},${firstCoord[1].toFixed(5)}`;
  } else if (geom.type === 'LineString') {
    const firstCoord = geom.coordinates[0];
    return `${f.properties.street_name}#${firstCoord[0].toFixed(5)},${firstCoord[1].toFixed(5)}`;
  }
  return `${f.properties.street_name}#unknown`;
};

const App: React.FC = () => {
  const { data, loading, error, analyze } = useComfortData();

  // Track the last analyzed city for URL persistence
  const [currentCity, setCurrentCity] = useState<string | null>(null);
  const initializedRef = useRef(false);

  // Read initial values from URL params
  const initialParams = useMemo(() => {
    const sp = new URLSearchParams(window.location.search);
    return {
      city: sp.get('city'),
      wNoise: sp.has('wNoise') ? Number(sp.get('wNoise')) : 20,
      wCanopy: sp.has('wCanopy') ? Number(sp.get('wCanopy')) : 20,
      wHeat: sp.has('wHeat') ? Number(sp.get('wHeat')) : 20,
      wSafety: sp.has('wSafety') ? Number(sp.get('wSafety')) : 20,
      wTraffic: sp.has('wTraffic') ? Number(sp.get('wTraffic')) : 20,
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Weight states (default to equal weights, i.e. 20% each)
  const [wNoise, setWNoise] = useState(initialParams.wNoise);
  const [wCanopy, setWCanopy] = useState(initialParams.wCanopy);
  const [wHeat, setWHeat] = useState(initialParams.wHeat);
  const [wSafety, setWSafety] = useState(initialParams.wSafety);
  const [wTraffic, setWTraffic] = useState(initialParams.wTraffic);

  // Detect if traffic data is present (feature-flagged on backend)
  const hasTraffic = data?.features.some((f) => f.properties.traffic_volume !== null) ?? false;

  // Active highlighted segment for workbench
  const [selectedSegment, setSelectedSegment] = useState<{
    lat: number;
    lon: number;
    properties: ComfortProperties;
    id: string;
  } | null>(null);

  // Scenario modeling overrides: segment_id -> overridden values
  const [interventions, setInterventions] = useState<
    Record<string, { canopy_pct?: number; noise_dba?: number; safety_score?: number }>
  >({});

  const statusClass = loading ? 'loading' : error ? 'error' : data ? 'success' : '';
  const statusText = loading
    ? 'Fetching data...'
    : error
      ? `Error: ${error}`
      : data
        ? `${data.features.length} segments scored`
        : 'Ready';

  // Reset selected segment and active proposals when city changes
  const handleSearch = (city: string) => {
    setSelectedSegment(null);
    setInterventions({});
    setCurrentCity(city);
    analyze(city);
  };

  // Task 3: Auto-analyze from URL on mount
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    if (initialParams.city) {
      setCurrentCity(initialParams.city);
      analyze(initialParams.city);
    }
  }, [initialParams.city, analyze]);

  // Task 3: Update URL when city loads or weights change
  useEffect(() => {
    if (!currentCity) return;
    const sp = new URLSearchParams();
    sp.set('city', currentCity);
    sp.set('wNoise', String(wNoise));
    sp.set('wCanopy', String(wCanopy));
    sp.set('wHeat', String(wHeat));
    sp.set('wSafety', String(wSafety));
    sp.set('wTraffic', String(wTraffic));
    window.history.replaceState(null, '', '?' + sp.toString());
  }, [currentCity, wNoise, wCanopy, wHeat, wSafety, wTraffic]);

  // Safe handler to update overrides
  const handleUpdateIntervention = (
    id: string,
    updates: { canopy_pct?: number; noise_dba?: number; safety_score?: number } | null
  ) => {
    setInterventions((prev) => {
      const next = { ...prev };
      if (updates === null) {
        delete next[id];
      } else {
        next[id] = updates;
      }
      return next;
    });

    // Sync selectedSegment properties if active
    if (updates) {
      setSelectedSegment((prev) => {
        if (!prev || prev.id !== id) return prev;
        return {
          ...prev,
          properties: {
            ...prev.properties,
            ...updates,
          },
        };
      });
    }
  };

  // Intercept data to inject active interventions for map layer rendering
  const intervenedData = useMemo(() => {
    if (!data) return null;
    return {
      ...data,
      features: data.features.map((f) => {
        const id = getSegmentId(f);
        const override = interventions[id];
        if (override) {
          const props = { ...f.properties, ...override };
          // Recompute static score on properties for default popup reads
          props.comfort_score = computeComfortScoreClient(
            props.noise_dba,
            props.canopy_pct,
            props.heat_index,
            props.safety_score,
            wNoise,
            wCanopy,
            wHeat,
            wSafety,
            props.traffic_volume,
            wTraffic,
          );
          return { ...f, properties: props };
        }
        return f;
      }),
    };
  }, [data, interventions, wNoise, wCanopy, wHeat, wSafety, wTraffic]);

  // Dynamically compute stats based on active weights and active interventions
  const adjustedStats = useMemo(() => {
    if (!data || data.features.length === 0) return null;
    
    // Baseline stats
    const baselineScores = data.features.map((f) => {
      const { noise_dba, canopy_pct, heat_index, safety_score, traffic_volume } = f.properties;
      return computeComfortScoreClient(
        noise_dba,
        canopy_pct,
        heat_index,
        safety_score,
        wNoise,
        wCanopy,
        wHeat,
        wSafety,
        traffic_volume,
        wTraffic,
      );
    });

    // Proposed stats (incorporates active interventions)
    const proposedScores = data.features.map((f) => {
      const id = getSegmentId(f);
      const override = interventions[id];
      const noise = override?.noise_dba !== undefined ? override.noise_dba : f.properties.noise_dba;
      const canopy = override?.canopy_pct !== undefined ? override.canopy_pct : f.properties.canopy_pct;
      const heat = f.properties.heat_index;
      const safety = override?.safety_score !== undefined ? override.safety_score : f.properties.safety_score;

      return computeComfortScoreClient(
        noise,
        canopy,
        heat,
        safety,
        wNoise,
        wCanopy,
        wHeat,
        wSafety,
        f.properties.traffic_volume,
        wTraffic,
      );
    });

    const sumBaseline = baselineScores.reduce((a, b) => a + b, 0);
    const sumProposed = proposedScores.reduce((a, b) => a + b, 0);

    return {
      segments: baselineScores.length,
      avg: sumProposed / proposedScores.length,
      min: proposedScores.reduce((a, b) => Math.min(a, b), Infinity),
      max: proposedScores.reduce((a, b) => Math.max(a, b), -Infinity),
      baselineAvg: sumBaseline / baselineScores.length,
    };
  }, [data, interventions, wNoise, wCanopy, wHeat, wSafety, wTraffic]);

  // Net gain from scenario modeling
  const netGain = adjustedStats
    ? adjustedStats.avg - adjustedStats.baselineAvg
    : 0;

  return (
    <>
      {/* Print Report Header (Hidden on screen, shown in print PDF) */}
      <div className="print-only-header">
        <h1>Human Comfort Factors (HCF) Walkability Audit</h1>
        <p>
          Generated on {new Date().toLocaleDateString()} | Active Scenario: {Object.keys(interventions).length} Street Interventions
        </p>
      </div>

      <header>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <h1>
            <span>HCF</span> Human Comfort Factors
          </h1>
          <SearchBar onSearch={handleSearch} loading={loading} />
        </div>

        {/* Dynamic Weight Sliders Panel */}
        <div className="weight-panel">
          <div className="slider-group">
            <label>🔊 Noise Weight: {wNoise}%</label>
            <input
              type="range"
              min="0"
              max="100"
              value={wNoise}
              onChange={(e) => setWNoise(Number(e.target.value))}
              aria-label="Noise weight"
            />
          </div>
          <div className="slider-group">
            <label>🌳 Shade Weight: {wCanopy}%</label>
            <input
              type="range"
              min="0"
              max="100"
              value={wCanopy}
              onChange={(e) => setWCanopy(Number(e.target.value))}
              aria-label="Shade weight"
            />
          </div>
          <div className="slider-group">
            <label>🌡️ Heat Weight: {wHeat}%</label>
            <input
              type="range"
              min="0"
              max="100"
              value={wHeat}
              onChange={(e) => setWHeat(Number(e.target.value))}
              aria-label="Heat weight"
            />
          </div>
          <div className="slider-group">
            <label>🛡️ Safety Weight: {wSafety}%</label>
            <input
              type="range"
              min="0"
              max="100"
              value={wSafety}
              onChange={(e) => setWSafety(Number(e.target.value))}
              aria-label="Safety weight"
            />
          </div>
          {hasTraffic && (
            <div className="slider-group">
              <label>🚗 Traffic Weight: {wTraffic}%</label>
              <input
                type="range"
                min="0"
                max="100"
                value={wTraffic}
                onChange={(e) => setWTraffic(Number(e.target.value))}
                aria-label="Traffic weight"
              />
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {netGain > 0 && (
            <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 8px', borderRadius: 6, backgroundColor: 'rgba(34,197,94,0.15)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.3)' }}>
              ✨ Scenario Gain: +{netGain.toFixed(2)} pts
            </span>
          )}
          <span id="status" className={statusClass}>
            {statusText}
          </span>
        </div>
      </header>

      <div style={{ display: 'flex', flex: 1, position: 'relative', overflow: 'hidden' }}>
        <ComfortMap
          data={intervenedData}
          wNoise={wNoise}
          wCanopy={wCanopy}
          wHeat={wHeat}
          wSafety={wSafety}
          wTraffic={wTraffic}
          selectedSegment={selectedSegment}
        />
        <DeficitPanel
          data={intervenedData}
          wNoise={wNoise}
          wCanopy={wCanopy}
          wHeat={wHeat}
          wSafety={wSafety}
          wTraffic={wTraffic}
          onSelectSegment={(lat, lon, properties) => {
            const f = { geometry: { type: 'LineString' as const, coordinates: [[lon, lat]] }, properties } as ComfortFeature;
            const id = getSegmentId(f);
            setSelectedSegment({ lat, lon, properties, id });
          }}
        />
        <InterventionCard
          segment={selectedSegment}
          intervention={selectedSegment ? interventions[selectedSegment.id] : undefined}
          onUpdateIntervention={handleUpdateIntervention}
          onClose={() => setSelectedSegment(null)}
        />
        {!data && !loading && !error && (
          <EmptyState onSelectCity={handleSearch} />
        )}
      </div>
      <StatsBar stats={adjustedStats} data={intervenedData} />
      <Legend />

      {loading && (
        <div className="loading-overlay active">
          <div className="spinner" />
        </div>
      )}
    </>
  );
};

export default App;
