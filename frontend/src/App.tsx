import React from 'react';
import SearchBar from './components/SearchBar';
import ComfortMap from './components/Map';
import Legend from './components/Legend';
import StatsBar from './components/StatsBar';
import { useComfortData } from './hooks/useComfortData';

const App: React.FC = () => {
  const { data, stats, loading, error, analyze } = useComfortData();

  const statusClass = loading ? 'loading' : error ? 'error' : data ? 'success' : '';
  const statusText = loading
    ? 'Fetching data...'
    : error
      ? `Error: ${error}`
      : data
        ? `${data.features.length} segments scored`
        : 'Ready';

  return (
    <>
      <header>
        <h1>
          <span>HCF</span> Human Comfort Factors
        </h1>
        <SearchBar onSearch={analyze} loading={loading} />
        <span id="status" className={statusClass}>
          {statusText}
        </span>
      </header>

      <ComfortMap data={data} />
      <StatsBar stats={stats} />
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
