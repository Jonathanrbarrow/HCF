import React from 'react';

interface EmptyStateProps {
  onSelectCity: (city: string) => void;
}

const SAMPLE_CITIES = [
  { label: 'Denver, CO', query: 'Denver, Colorado, USA' },
  { label: 'Miami, FL', query: 'Miami, Florida, USA' },
  { label: 'Portland, OR', query: 'Portland, Oregon, USA' },
  { label: 'Austin, TX', query: 'Austin, Texas, USA' },
];

const EmptyState: React.FC<EmptyStateProps> = ({ onSelectCity }) => {
  return (
    <div className="empty-state">
      <div className="empty-state-card">
        <h2 className="empty-state-hero">Search any US city to map pedestrian comfort</h2>
        <p className="empty-state-subtitle">
          HCF scores every walkable street on heat, noise, shade, safety, and traffic
        </p>
        <div className="empty-state-cities">
          {SAMPLE_CITIES.map((city) => (
            <button
              key={city.label}
              className="empty-state-city-btn"
              onClick={() => onSelectCity(city.query)}
            >
              {city.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default EmptyState;
