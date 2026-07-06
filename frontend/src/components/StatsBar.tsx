import React from 'react';
import type { CityStats, ComfortGeoJSON } from '../types/comfort';

interface StatsBarProps {
  stats: CityStats | null;
  data: ComfortGeoJSON | null;
}

const btnStyle: React.CSSProperties = {
  background: 'var(--accent)',
  color: '#fff',
  border: 'none',
  padding: '6px 12px',
  borderRadius: '6px',
  fontSize: '11px',
  fontWeight: 600,
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '4px',
};

const downloadBlob = (content: string, filename: string, type: string) => {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

const StatsBar: React.FC<StatsBarProps> = ({ stats, data }) => {
  if (!stats) return null;

  const handleDownloadGeoJSON = () => {
    if (!data) return;
    downloadBlob(JSON.stringify(data, null, 2), 'hcf-comfort.geojson', 'application/json');
  };

  const handleDownloadCSV = () => {
    if (!data) return;
    const headers = [
      'street_name',
      'comfort_score',
      'noise_dba',
      'canopy_pct',
      'heat_index',
      'safety_score',
      'traffic_volume',
      'data_quality',
    ];
    const rows = data.features.map((f) => {
      const p = f.properties;
      const dq = p.data_quality
        ? `noise=${p.data_quality.noise} canopy=${p.data_quality.canopy} heat=${p.data_quality.heat} safety=${p.data_quality.safety} traffic=${p.data_quality.traffic}`
        : '';
      return [
        `"${(p.street_name ?? '').replace(/"/g, '""')}"`,
        p.comfort_score,
        p.noise_dba,
        p.canopy_pct,
        p.heat_index,
        p.safety_score,
        p.traffic_volume,
        `"${dq}"`,
      ].join(',');
    });
    const csv = [headers.join(','), ...rows].join('\n');
    downloadBlob(csv, 'hcf-comfort.csv', 'text/csv');
  };

  return (
    <div className="stats-bar active">
      <span className="stat-item">
        Segments: <strong>{stats.segments}</strong>
      </span>
      <span className="stat-item">
        Avg Score: <strong>{stats.avg.toFixed(1)}</strong>
        {stats.baselineAvg !== stats.avg && (
          <span style={{ fontSize: 10, color: stats.avg > stats.baselineAvg ? '#22c55e' : '#f97316', marginLeft: 4 }}>
            ({stats.avg > stats.baselineAvg ? '+' : ''}{(stats.avg - stats.baselineAvg).toFixed(1)} from baseline)
          </span>
        )}
      </span>
      <span className="stat-item">
        Min: <strong>{stats.min.toFixed(1)}</strong>
      </span>
      <span className="stat-item">
        Max: <strong>{stats.max.toFixed(1)}</strong>
      </span>
      {data && data.features.length > 0 && data.features[0].properties.data_quality && (
        <span className="stat-item" style={{ fontSize: 10, color: 'var(--text-secondary)' }} title="% of segments with real data per factor">
          Data: {(['noise', 'canopy', 'heat', 'safety', 'traffic'] as const).map((key) => {
            const total = data.features.length;
            const real = data.features.filter((f) => f.properties.data_quality?.[key] === 'real').length;
            const pct = Math.round((real / total) * 100);
            const emoji = key === 'noise' ? '🔊' : key === 'canopy' ? '🌳' : key === 'heat' ? '🌡️' : key === 'safety' ? '🛡️' : '🚗';
            return <span key={key} style={{ marginRight: 6, color: pct > 70 ? '#22c55e' : pct > 30 ? '#f97316' : '#ef4444' }}>{emoji}{pct}%</span>;
          })}
        </span>
      )}
      <button
        onClick={() => window.print()}
        style={{ ...btnStyle, marginLeft: 'auto' }}
        aria-label="Print report"
      >
        🖨️ Export PDF Audit Report
      </button>
      <button
        onClick={handleDownloadGeoJSON}
        style={btnStyle}
        aria-label="Download GeoJSON"
      >
        📦 Download GeoJSON
      </button>
      <button
        onClick={handleDownloadCSV}
        style={btnStyle}
        aria-label="Download CSV"
      >
        📊 Download CSV
      </button>
    </div>
  );
};

export default StatsBar;
