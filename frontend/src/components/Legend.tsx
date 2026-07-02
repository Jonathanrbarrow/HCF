import React from 'react';

const LEGEND_ITEMS = [
  { color: '#22c55e', label: '80–100 Excellent' },
  { color: '#84cc16', label: '60–80 Good' },
  { color: '#eab308', label: '40–60 Fair' },
  { color: '#f97316', label: '20–40 Poor' },
  { color: '#ef4444', label: '0–20 Hostile' },
];

const Legend: React.FC = () => (
  <div className="legend">
    <h3>Comfort Score</h3>
    {LEGEND_ITEMS.map((item) => (
      <div className="legend-item" key={item.color}>
        <div className="legend-color" style={{ background: item.color }} />
        {item.label}
      </div>
    ))}
    <div className="legend-item" style={{ marginTop: 8 }}>
      <div
        className="legend-color"
        style={{
          background: 'transparent',
          borderTop: '2px dashed #8b8fa3',
          height: 0,
        }}
      />
      <span style={{ color: '#8b8fa3', fontSize: 12 }}>Limited data</span>
    </div>
  </div>
);

export default Legend;
