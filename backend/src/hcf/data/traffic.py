"""
Traffic module — fetches AADT (Annual Average Daily Traffic) data from
the FHWA Highway Performance Monitoring System (HPMS) via ArcGIS REST.

Data source:
  https://geo.dot.gov/server/rest/services/Hosted/{State}_{Year}_PR/FeatureServer

The HPMS data is organized by state. We query the FeatureServer with
a spatial buffer around a point to find the nearest road segment's AADT.

No authentication required.

Feature-flagged: controlled by settings.enable_traffic_factor.
When disabled, fetch functions return default/None values without
making any API calls.
"""
import logging

import requests

from hcf.config import settings
from hcf.data.quality import REAL, DEFAULT, UNAVAILABLE, DISABLED

logger = logging.getLogger(__name__)

# State FIPS code to HPMS dataset name mapping
# Uses the most recent available year for each state
_STATE_DATASETS: dict[str, str] = {
    "AL": "Alabama_2020_PR", "AK": "Alaska_2020_PR",
    "AZ": "Arizona_2020_PR", "AR": "Arkansas_2020_PR",
    "CA": "California_2020_PR", "CO": "Colorado_2020_PR",
    "CT": "Connecticut_2020_PR", "DE": "Delaware_2020_PR",
    "FL": "Florida_2020_PR", "GA": "Georgia_2020_PR",
    "HI": "Hawaii_2020_PR", "ID": "Idaho_2020_PR",
    "IL": "Illinois_2020_PR", "IN": "Indiana_2020_PR",
    "IA": "Iowa_2020_PR", "KS": "Kansas_2020_PR",
    "KY": "Kentucky_2020_PR", "LA": "Louisiana_2020_PR",
    "ME": "Maine_2020_PR", "MD": "Maryland_2020_PR",
    "MA": "Massachusetts_2020_PR", "MI": "Michigan_2020_PR",
    "MN": "Minnesota_2020_PR", "MS": "Mississippi_2020_PR",
    "MO": "Missouri_2020_PR", "MT": "Montana_2020_PR",
    "NE": "Nebraska_2020_PR", "NV": "Nevada_2020_PR",
    "NH": "New_Hampshire_2020_PR", "NJ": "New_Jersey_2020_PR",
    "NM": "New_Mexico_2020_PR", "NY": "New_York_2020_PR",
    "NC": "North_Carolina_2020_PR", "ND": "North_Dakota_2020_PR",
    "OH": "Ohio_2020_PR", "OK": "Oklahoma_2020_PR",
    "OR": "Oregon_2020_PR", "PA": "Pennsylvania_2020_PR",
    "RI": "Rhode_Island_2020_PR", "SC": "South_Carolina_2020_PR",
    "SD": "South_Dakota_2020_PR", "TN": "Tennessee_2020_PR",
    "TX": "Texas_2020_PR", "UT": "Utah_2020_PR",
    "VT": "Vermont_2020_PR", "VA": "Virginia_2020_PR",
    "WA": "Washington_2020_PR", "WV": "West_Virginia_2020_PR",
    "WI": "Wisconsin_2020_PR", "WY": "Wyoming_2020_PR",
    "DC": "District_of_Columbia_2020_PR",
}


def _resolve_state(lat: float, lon: float) -> str | None:
    """
    Resolve a lat/lon to a US state abbreviation using a simple
    reverse geocode via the US Census geocoder (free, no auth).

    Falls back to None if geocoding fails.
    """
    try:
        resp = requests.get(
            "https://geocoding.geo.census.gov/geocoder/geographies/coordinates",
            params={
                "x": lon,
                "y": lat,
                "benchmark": "Public_AR_Current",
                "vintage": "Current_Current",
                "format": "json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        geographies = data.get("result", {}).get("geographies", {})
        states = geographies.get("States", [])
        if states:
            return states[0].get("STUSAB")
    except Exception:
        logger.debug("Failed to resolve state for (%.4f, %.4f)", lat, lon)
    return None


def check_traffic_api(state_abbr: str = "FL") -> dict:
    """
    Check that the HPMS traffic API is reachable for a given state.

    Returns:
        dict with "reachable" (bool) and service metadata.
    """
    dataset = _STATE_DATASETS.get(state_abbr)
    if not dataset:
        return {"reachable": False, "error": f"Unknown state: {state_abbr}"}

    url = f"{settings.traffic_api_url}/{dataset}/FeatureServer/0"
    try:
        resp = requests.get(url, params={"f": "json"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {
            "reachable": True,
            "name": data.get("name"),
            "fields": [f.get("name") for f in data.get("fields", [])[:10]],
        }
    except Exception as e:
        return {"reachable": False, "error": str(e)}


def fetch_traffic_at_point(
    lat: float, lon: float, state_abbr: str | None = None
) -> int | None:
    """
    Fetch AADT at a specific lat/lon from the HPMS FeatureServer.

    Uses a 100m spatial buffer to find the nearest road segment.
    Returns the highest AADT among matched segments (conservative —
    the busiest nearby road dominates pedestrian discomfort).

    Args:
        lat: Latitude (decimal degrees)
        lon: Longitude (decimal degrees)
        state_abbr: Optional 2-letter state code. If None, resolved
                    from coordinates (costs an extra API call).

    Returns:
        int: AADT value, or None if no data at this point.
    """
    if not settings.enable_traffic_factor:
        return None

    # Resolve state if not provided
    if state_abbr is None:
        state_abbr = _resolve_state(lat, lon)
    if state_abbr is None:
        return None

    dataset = _STATE_DATASETS.get(state_abbr)
    if not dataset:
        return None

    url = f"{settings.traffic_api_url}/{dataset}/FeatureServer/0/query"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "distance": 100,  # 100m buffer
        "units": "esriSRUnit_Meter",
        "outFields": "AADT",
        "returnGeometry": "false",
        "f": "json",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        if not features:
            return None

        # Return the highest AADT among matched segments
        aadt_values = []
        for feat in features:
            aadt = feat.get("attributes", {}).get("AADT")
            if aadt is not None:
                try:
                    val = int(aadt)
                    if val > 0:
                        aadt_values.append(val)
                except (ValueError, TypeError):
                    continue

        return max(aadt_values) if aadt_values else None

    except Exception:
        logger.debug("Failed to fetch AADT for (%.4f, %.4f)", lat, lon)
        return None


def fetch_traffic_batch(
    points: list[tuple[float, float]],
    state_abbr: str | None = None,
) -> list[dict]:
    """
    Fetch AADT for a batch of points with quality tracking.

    When the traffic factor is disabled, returns default values
    without making any API calls.

    Args:
        points: List of (lat, lon) tuples.
        state_abbr: Optional state code (avoids per-point geocoding).

    Returns:
        List of dicts with keys:
          - "value": int or None
          - "quality": "real" | "default" | "unavailable" | "disabled"
    """
    if not settings.enable_traffic_factor:
        return [{"value": None, "quality": DISABLED} for _ in points]

    # Resolve state from first point if not provided (single call)
    if state_abbr is None and points:
        state_abbr = _resolve_state(points[0][0], points[0][1])

    from concurrent.futures import ThreadPoolExecutor, as_completed

    resolved_state = state_abbr  # capture for closure

    def _fetch_one(idx_lat_lon: tuple[int, tuple[float, float]]) -> tuple[int, dict]:
        idx, (lat, lon) = idx_lat_lon
        try:
            value = fetch_traffic_at_point(lat, lon, state_abbr=resolved_state)
            if value is not None:
                return idx, {"value": value, "quality": REAL}
            else:
                return idx, {
                    "value": settings.traffic_default_aadt,
                    "quality": DEFAULT,
                }
        except Exception:
            return idx, {"value": None, "quality": UNAVAILABLE}

    results: list[dict | None] = [None] * len(points)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(_fetch_one, (i, pt)): i
            for i, pt in enumerate(points)
        }
        for future in as_completed(futures):
            idx, result = future.result()
            results[idx] = result

    # Safety net: replace any remaining None entries (thread execution failed)
    for i, r in enumerate(results):
        if r is None:
            results[i] = {"value": None, "quality": UNAVAILABLE}

    return results  # type: ignore[return-value]
