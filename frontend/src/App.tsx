import React, { useState, useMemo } from 'react';
import SearchBar from './components/SearchBar';
import ComfortMap from './components/Map';
import Legend from './components/Legend';
import StatsBar from './components/StatsBar';
import { useComfortData } from './hooks/useComfortData';
import { computeComfortScoreClient } from './utils/scoring';

const App: React.FC = () => {
  const { data, stats, loading, error, analyze } = useComfortData();

  // Weight states (default to equal weights, i.e. 33.3% each)
  const [wNoise, setWNoise] = useState(33);
  const [wCanopy, setWCanopy] = useState(33);
  const [wHeat, setWHeat] = useState(34);

  const statusClass = loading ? 'loading' : error ? 'error' : data ? 'success' : '';
  const statusText = loading
    ? 'Fetching data...'
    : error
      ? `Error: ${error}`
      : data
        ? `${data.features.length} segments scored`
        : 'Ready';

  // Dynamically compute stats based on active weights
  const adjustedStats = useMemo(() => {
    if (!data || data.features.length === 0) return null;
    const scores = data.features.map((f) => {
      const { noise_dba, canopy_pct, heat_index } = f.properties;
      return computeComfortScoreClient(
        noise_dba,
        canopy_pct,
        heat_index,
        wNoise,
        wCanopy,
        wHeat,
      );
    });

    const sum = scores.reduce((a, b) => a + b, 0);
    return {
      segments: scores.length,
      avg: sum / scores.length,
      min: Math.min(...scores),
      max: Math.max(...scores),
    };
  }, [data, wNoise, wCanopy, wHeat]);

  return (
    <>
      <header>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <h1>
            <span>HCF</span> Human Comfort Factors
          </h1>
          <SearchBar onSearch={analyze} loading={loading} />
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
            />
          </div>
        </div>

        <span id="status" className={statusClass}>
          {statusText}
        </span>
      </header>

      <ComfortMap data={data} wNoise={wNoise} wCanopy={wCanopy} wHeat={wHeat} />
      <StatsBar stats={adjustedStats} />
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
