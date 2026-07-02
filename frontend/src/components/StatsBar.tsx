import React from 'react';
import type { CityStats } from '../types/comfort';

interface StatsBarProps {
  stats: CityStats | null;
}

const StatsBar: React.FC<StatsBarProps> = ({ stats }) => {
  if (!stats) return null;

  return (
    <div className="stats-bar active">
      <span className="stat-item">
        Segments: <strong>{stats.segments}</strong>
      </span>
      <span className="stat-item">
        Avg Score: <strong>{stats.avg.toFixed(1)}</strong>
      </span>
      <span className="stat-item">
        Min: <strong>{stats.min.toFixed(1)}</strong>
      </span>
      <span className="stat-item">
        Max: <strong>{stats.max.toFixed(1)}</strong>
      </span>
      <button
        onClick={() => window.print()}
        style={{
          marginLeft: 'auto',
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
          gap: '4px'
        }}
      >
        🖨️ Export PDF Audit Report
      </button>
    </div>
  );
};

export default StatsBar;
