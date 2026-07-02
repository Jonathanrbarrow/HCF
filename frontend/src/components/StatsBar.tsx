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
    </div>
  );
};

export default StatsBar;
