"""Data quality status constants for consistent labeling across all data modules."""

# Valid data quality statuses
REAL = "real"           # Actual observed data from the source API
DEFAULT = "default"     # Default/fallback value used when data is unavailable
UNAVAILABLE = "unavailable"  # Data source returned no result and no default applied
FIXED = "fixed"         # Value is a fixed constant (e.g., heat_index in archive mode)
DISABLED = "disabled"   # Factor is disabled via feature toggle

VALID_STATUSES = frozenset({REAL, DEFAULT, UNAVAILABLE, FIXED, DISABLED})
