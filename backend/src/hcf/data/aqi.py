"""
Air quality data module — fetches real-time AQI from EPA AirNow API.

Uses the AirNow Observation API to get current AQI and PM2.5
readings for given coordinates.  The API provides the nearest
monitoring station's reading for each location.

Feature-flagged via ``settings.enable_aqi_factor``.

API docs: https://docs.airnowapi.org/CurrentObservationsByLatLon/docs
"""
import logging

import requests

from hcf.config import settings
from hcf.data.quality import REAL, DEFAULT, UNAVAILABLE, DISABLED

logger = logging.getLogger(__name__)

# AirNow API endpoint
_AIRNOW_URL = "https://www.airnowapi.org/aq/observation/latLong/current/"

# Timeout for individual API calls (seconds)
_TIMEOUT = 8


def fetch_aqi_at_point(lat: float, lon: float) -> dict | None:
    """
    Fetch current AQI for a single point.

    Returns:
        dict with keys "aqi" (int) and "pm25" (float) or None on failure.
        Returns the PM2.5 observation if available, otherwise the
        highest-AQI observation for any pollutant.
    """
    if not settings.airnow_api_key:
        return None

    try:
        params = {
            "format": "application/json",
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "distance": 25,  # miles radius to search for stations
            "API_KEY": settings.airnow_api_key,
        }
        resp = requests.get(_AIRNOW_URL, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return None

        # Prefer PM2.5 observation if present
        pm25_obs = [d for d in data if d.get("ParameterName") == "PM2.5"]
        if pm25_obs:
            return {
                "aqi": int(pm25_obs[0]["AQI"]),
                "pm25": float(pm25_obs[0].get("Concentration", pm25_obs[0]["AQI"])),
                "category": pm25_obs[0].get("Category", {}).get("Name", ""),
            }

        # Fallback: highest AQI observation
        best = max(data, key=lambda d: d.get("AQI", 0))
        return {
            "aqi": int(best["AQI"]),
            "pm25": None,
            "category": best.get("Category", {}).get("Name", ""),
        }

    except Exception:
        logger.debug("Failed to fetch AQI for (%.4f, %.4f)", lat, lon)
        return None


def fetch_aqi_batch(
    points: list[tuple[float, float]],
) -> list[dict]:
    """
    Fetch AQI for a batch of points with quality tracking.

    Since nearby points share the same monitoring station, we deduplicate
    by rounding coordinates to 2 decimal places (~1km grid) to minimize
    API calls.

    Returns:
        List of dicts with keys:
          - "value": int (AQI) or None
          - "quality": "real" | "default" | "unavailable" | "disabled"
          - "category": str (AQI category name) or None
    """
    if not settings.enable_aqi_factor:
        return [{"value": None, "quality": DISABLED, "category": None}
                for _ in points]

    if not settings.airnow_api_key:
        logger.warning("AQI factor enabled but no AirNow API key set "
                       "(HCF_AIRNOW_API_KEY). Returning defaults.")
        return [{"value": None, "quality": UNAVAILABLE, "category": None}
                for _ in points]

    # Deduplicate: round to 2 decimal places (~1km grid).
    # All points within the same grid cell share one API call.
    from concurrent.futures import ThreadPoolExecutor, as_completed

    cache: dict[tuple[float, float], dict | None] = {}

    def _rounded(lat: float, lon: float) -> tuple[float, float]:
        return (round(lat, 2), round(lon, 2))

    # Find unique grid cells
    unique_cells: dict[tuple[float, float], tuple[float, float]] = {}
    for lat, lon in points:
        key = _rounded(lat, lon)
        if key not in unique_cells:
            unique_cells[key] = (lat, lon)  # use first actual point

    def _fetch_cell(item: tuple[tuple[float, float], tuple[float, float]]) -> tuple[tuple[float, float], dict | None]:
        cell_key, (lat, lon) = item
        return cell_key, fetch_aqi_at_point(lat, lon)

    # Fetch unique cells concurrently
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_fetch_cell, (k, v)): k
            for k, v in unique_cells.items()
        }
        for future in as_completed(futures):
            try:
                cell_key, result = future.result()
                cache[cell_key] = result
            except Exception:
                pass  # cell stays absent → will get default AQI

    # Map results back to all points
    results = []
    for lat, lon in points:
        key = _rounded(lat, lon)
        data = cache.get(key)
        if data is not None:
            results.append({
                "value": data["aqi"],
                "quality": REAL,
                "category": data.get("category"),
            })
        else:
            results.append({
                "value": settings.aqi_default,
                "quality": DEFAULT,
                "category": None,
            })

    return results


def check_aqi_api() -> bool:
    """Quick check if the AirNow API is reachable and key is valid."""
    if not settings.airnow_api_key:
        return False
    try:
        # Test with a known location (Washington DC)
        result = fetch_aqi_at_point(38.9072, -77.0369)
        return result is not None
    except Exception:
        return False
