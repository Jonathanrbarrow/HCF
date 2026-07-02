import React from 'react';

interface SearchBarProps {
  onSearch: (city: string) => void;
  loading: boolean;
}

const SearchBar: React.FC<SearchBarProps> = ({ onSearch, loading }) => {
  const [value, setValue] = React.useState('');

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (trimmed) onSearch(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSubmit();
  };

  return (
    <div className="search-container">
      <input
        type="text"
        id="city-input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Enter a US city (e.g. Denver, Colorado, USA)"
        autoComplete="off"
        disabled={loading}
      />
      <button
        id="search-btn"
        onClick={handleSubmit}
        disabled={loading || !value.trim()}
      >
        Analyze
      </button>
    </div>
  );
};

export default SearchBar;
