"""
Heat module — fetches **historical summer peak** apparent temperature
from the Open-Meteo Archive API.

Unlike the previous implementation which returned the *current* temperature
(useless for planning — changes every hour), this version computes
the average daily peak apparent temperature during summer months
(June–August) over the past 3 years.  This gives a stable, representative
"typical hot day" value for infrastructure planning.

No authentication required.
"""
import logging
from datetime import date

import requests

from hcf.config import settings

logger = logging.getLogger(__name__)

# Open-Meteo Historical Archive endpoint
_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def _summer_date_range() -> tuple[str, str]:
    """Return (start_date, end_date) covering the last 3 complete summers.

    NOTE: Assumes Northern Hemisphere (June-August = summer).
    This is correct for US cities but would need adjustment for
    Southern Hemisphere locations.
    """
    current_year = date.today().year
    # Use last 3 complete summers (June 1 – August 31)
    # If we're currently in summer, use the previous 3
    if date.today().month <= 8:
        end_year = current_year - 1
    else:
        end_year = current_year
    start_year = end_year - 2
    return (f"{start_year}-06-01", f"{end_year}-08-31")


def fetch_heat_at_point(lat: float, lon: float) -> float | None:
    """
    Fetch the average summer peak apparent temperature (°F) for a location.

    Queries the Open-Meteo Archive API for the last 3 summers of daily
    max apparent temperature and returns the mean.

    Returns:
        float: Mean daily peak apparent temp in °F over 3 summers, or None.
    """
    try:
        start, end = _summer_date_range()
        resp = requests.get(
            _ARCHIVE_URL,
            params={
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "start_date": start,
                "end_date": end,
                "daily": "apparent_temperature_max",
                "temperature_unit": "fahrenheit",
                "timezone": "auto",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning(
                "Heat archive API returned %d for (%.4f, %.4f)",
                resp.status_code, lat, lon,
            )
            return None

        data = resp.json()
        daily = data.get("daily", {})
        temps = daily.get("apparent_temperature_max", [])

        # Filter out nulls and compute mean
        valid = [t for t in temps if t is not None]
        if not valid:
            return None

        return sum(valid) / len(valid)

    except Exception as e:
        logger.error("Error fetching heat archive for (%.4f, %.4f): %s", lat, lon, e)
        return None


def fetch_heat_batch(points: list[tuple[float, float]]) -> list[dict]:
    """
    Fetch historical summer peak heat for a batch of points.

    Since nearby points share the same climate, we deduplicate by rounding
    to 1 decimal place (~11km grid) — all points within a grid cell get
    the same historical average.

    Returns:
        List of dicts: [{"value": float|None, "quality": "real"|"default"|"unavailable"}, ...]
    """
    if not points:
        return []

    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Deduplicate: round to 1 decimal (~11km grid cells).
    # Historical climate doesn't vary at street level.
    cache: dict[tuple[float, float], float | None] = {}

    def _rounded(lat: float, lon: float) -> tuple[float, float]:
        return (round(lat, 1), round(lon, 1))

    unique_cells: dict[tuple[float, float], tuple[float, float]] = {}
    for lat, lon in points:
        key = _rounded(lat, lon)
        if key not in unique_cells:
            unique_cells[key] = (lat, lon)

    def _fetch_cell(
        item: tuple[tuple[float, float], tuple[float, float]],
    ) -> tuple[tuple[float, float], float | None]:
        cell_key, (lat, lon) = item
        return cell_key, fetch_heat_at_point(lat, lon)

    # For small cities, most/all points will be in the same grid cell
    # → typically just 1-3 API calls instead of 200
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_fetch_cell, (k, v)): k
            for k, v in unique_cells.items()
        }
        for future in as_completed(futures):
            try:
                cell_key, value = future.result()
                cache[cell_key] = value
            except Exception:
                pass  # cell stays absent → will get default heat index

    # Map results back to all points
    results = []
    for lat, lon in points:
        key = _rounded(lat, lon)
        value = cache.get(key)
        if value is not None:
            results.append({"value": round(value, 1), "quality": "real"})
        else:
            results.append({"value": settings.default_heat_index, "quality": "default"})

    return results
