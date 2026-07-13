"""
Noise module — fetches transportation noise data from the US DOT
National Transportation Noise Map via ArcGIS REST API.

Data source:
  https://geo.dot.gov/server/rest/services/Hosted/NTAD_Noise_2020_CONUS_Road/MapServer

The noise map is a raster tile service. We use the "identify" operation
to sample pixel values at specific lat/lon points.

No authentication required.
"""
import logging
import requests
import math

logger = logging.getLogger(__name__)

from hcf.config import settings

# DOT noise map raster service — CONUS road noise (2020)
NOISE_MAP_URL = settings.noise_api_url

# identify endpoint for sampling pixel values
NOISE_IDENTIFY_URL = f"{NOISE_MAP_URL}/identify"


def check_noise_api() -> dict:
    """
    Check that the DOT noise map API is reachable and returning metadata.

    Returns:
        dict with "reachable" (bool) and service metadata.
    """
    try:
        resp = requests.get(NOISE_MAP_URL, params={"f": "json"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {
            "reachable": True,
            "layers": data.get("layers"),
            "spatialReference": data.get("spatialReference"),
        }
    except Exception as e:
        return {"reachable": False, "error": str(e)}


def fetch_noise_at_point(lat: float, lon: float) -> float | None:
    """
    Fetch the noise level (dBA) at a specific lat/lon from the DOT noise map.

    Uses the ArcGIS MapServer identify operation to sample the raster
    pixel value at the given location.

    Args:
        lat: Latitude (decimal degrees)
        lon: Longitude (decimal degrees)

    Returns:
        float: Noise level in dBA, or None if no data at this point.
    """
    # Build a tiny envelope around the point for the identify operation
    tolerance = 0.0001  # ~11 meters
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "sr": "4326",
        "layers": "all",
        "tolerance": 2,
        "mapExtent": f"{lon - tolerance},{lat - tolerance},{lon + tolerance},{lat + tolerance}",
        "imageDisplay": "100,100,96",
        "returnGeometry": "false",
        "f": "json",
    }

    try:
        resp = requests.get(NOISE_IDENTIFY_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if not results:
            return None

        # Extract the pixel value from the first result
        for result in results:
            attrs = result.get("attributes", {})
            # The pixel value field name varies — try common patterns
            for key in ["Pixel Value", "pixel_value", "Pixel value", "value", "Value"]:
                if key in attrs:
                    val = attrs[key]
                    try:
                        fval = float(val)
                        if fval > 0:  # 0 or NoData means no coverage
                            return fval
                    except (ValueError, TypeError):
                        continue

            # Try the "Stretched value" or class value
            for key in attrs:
                if "value" in key.lower() or "class" in key.lower():
                    try:
                        fval = float(attrs[key])
                        if fval > 0:
                            return fval
                    except (ValueError, TypeError):
                        continue

        return None

    except Exception:
        logger.debug("Failed to fetch noise for (%.4f, %.4f)", lat, lon, exc_info=True)
        return None


def fetch_noise_batch(points: list[tuple[float, float]]) -> list[dict]:
    """
    Fetch noise levels for a batch of points with quality tracking.

    Calls fetch_noise_at_point() per point using a thread pool for
    concurrent execution.

    Args:
        points: List of (lat, lon) tuples.

    Returns:
        List of dicts with keys:
          - "value": float or None
          - "quality": "real" | "default" | "unavailable"
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_one(idx_lat_lon: tuple[int, tuple[float, float]]) -> tuple[int, dict]:
        idx, (lat, lon) = idx_lat_lon
        try:
            value = fetch_noise_at_point(lat, lon)
            if value is not None:
                return idx, {"value": value, "quality": "real"}
            else:
                return idx, {"value": settings.noise_default_dba, "quality": "default"}
        except Exception:
            return idx, {"value": None, "quality": "unavailable"}

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
            results[i] = {"value": None, "quality": "unavailable"}

    return results  # type: ignore[return-value]


def fetch_noise_for_bbox(bbox: tuple, sample_points: int = 25) -> list:
    """
    Sample noise levels across a bounding box on a grid.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        sample_points: Number of points to sample (arranged in a grid)

    Returns:
        list of float|None: Noise values at each sample point.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    grid_size = int(math.sqrt(sample_points))

    values = []
    for i in range(grid_size):
        for j in range(grid_size):
            lat = min_lat + (max_lat - min_lat) * (i + 0.5) / grid_size
            lon = min_lon + (max_lon - min_lon) * (j + 0.5) / grid_size
            val = fetch_noise_at_point(lat, lon)
            values.append(val)

    return values


def get_noise_penalty(noise_dba: float) -> float:
    """
    Convert a noise level in dBA to a penalty value (0.0 - 1.0).

    Thresholds based on WHO/EPA noise guidelines:
    - <= 45 dBA: No penalty (quiet residential)
    - >= 80 dBA: Maximum penalty (highway/industrial)
    - Linear interpolation between

    Args:
        noise_dba: Noise level in dBA

    Returns:
        float: Penalty value between 0.0 and 1.0
    """
    noise_dba = max(0, noise_dba)  # Clamp negatives
    if noise_dba <= 45:
        return 0.0
    elif noise_dba >= 80:
        return 1.0
    else:
        return (noise_dba - 45) / (80 - 45)
