"""
Heat module — fetches apparent temperature (heat index) from the Open-Meteo API.

No authentication is required. Apparent temperature combines temperature, relative humidity,
wind chill, and solar radiation to estimate feels-like temperature.
"""
import requests
import logging
from hcf.config import settings

logger = logging.getLogger(__name__)


def fetch_heat_at_point(lat: float, lon: float) -> float | None:
    """
    Fetch the apparent temperature (Fahrenheit) for a specific latitude and longitude.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        float apparent temperature in Fahrenheit, or None if the request fails.
    """
    try:
        url = (
            f"{settings.heat_api_url}?"
            f"latitude={lat}&longitude={lon}&"
            f"current=apparent_temperature&"
            f"temperature_unit=fahrenheit"
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "current" in data and "apparent_temperature" in data["current"]:
                return float(data["current"]["apparent_temperature"])
        logger.warning(f"Heat API returned status {resp.status_code} for point ({lat}, {lon})")
        return None
    except Exception as e:
        logger.error(f"Error fetching heat data at point ({lat}, {lon}): {str(e)}")
        return None


def fetch_heat_batch(points: list[tuple[float, float]]) -> list[dict]:
    """
    Fetch apparent temperature in batch for a list of (lat, lon) coordinates.
    Open-Meteo supports multi-point queries in a single request.

    Args:
        points: List of (lat, lon) coordinate tuples

    Returns:
        List of dicts: [{"value": float | None, "quality": "real" | "default" | "unavailable"}, ...]
    """
    if not points:
        return []

    # If single point, use the single point fetch wrapper to avoid list/dict return variation
    if len(points) == 1:
        lat, lon = points[0]
        val = fetch_heat_at_point(lat, lon)
        if val is not None:
            return [{"value": val, "quality": "real"}]
        else:
            return [{"value": settings.default_heat_index, "quality": "default"}]

    try:
        # Build batch parameters
        lats = ",".join(str(p[0]) for p in points)
        lons = ",".join(str(p[1]) for p in points)

        url = (
            f"{settings.heat_api_url}?"
            f"latitude={lats}&longitude={lons}&"
            f"current=apparent_temperature&"
            f"temperature_unit=fahrenheit"
        )
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # If multi-point, Open-Meteo returns a list of dictionaries
            if isinstance(data, list):
                results = []
                for item in data:
                    val = None
                    quality = "unavailable"
                    if "current" in item and "apparent_temperature" in item["current"]:
                        val = float(item["current"]["apparent_temperature"])
                        quality = "real"
                    else:
                        val = settings.default_heat_index
                        quality = "default"
                    results.append({"value": val, "quality": quality})
                return results

        # Fallback to per-point queries if API returned something else or failed
        logger.warning(f"Heat API batch query failed with status {resp.status_code}. Falling back to per-point.")
    except Exception as e:
        logger.error(f"Error fetching heat batch: {str(e)}. Falling back to per-point.")

    # Fallback path
    results = []
    for lat, lon in points:
        val = fetch_heat_at_point(lat, lon)
        if val is not None:
            results.append({"value": val, "quality": "real"})
        else:
            results.append({"value": settings.default_heat_index, "quality": "default"})
    return results
