"""
Canopy module — fetches tree canopy HEIGHT data from the Meta/WRI
Global Canopy Height Map via Cloud Optimized GeoTIFFs on AWS S3.

Data source:
  Meta & World Resources Institute (WRI) Global Canopy Height Map
  S3: s3://dataforgood-fb-data/forests/v1/alsgedi_global_v6_float/chm/
  Format: Cloud Optimized GeoTIFF (COG), QuadKey-named tiles
  Resolution: 1 meter
  Values: Canopy height in meters (0 = no canopy)
  Coverage: Global
  No authentication required (anonymous S3 access)

Why canopy HEIGHT instead of canopy cover %:
  - 1m resolution vs 30m (NLCD) — can distinguish individual trees from bare sidewalk
  - Height is a better shade proxy — a 20m oak provides far more shade than a 3m shrub
  - Global coverage — not limited to CONUS

QuadKey tile system:
  The dataset uses Bing Maps QuadKey tiling. We compute the QuadKey
  directly from lat/lon using the standard algorithm, no index file needed.
"""
import logging
import math
import os
import requests

from hcf.config import settings

logger = logging.getLogger(__name__)

# We try rasterio first (for direct COG reads from S3).
# If not available, fall back to HTTP range requests.
try:
    import rasterio
    from rasterio.session import AWSSession
    from rasterio.windows import Window
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

# S3 base path for the Meta/WRI canopy height tiles (from settings)
S3_BUCKET = settings.canopy_s3_bucket
S3_PREFIX = settings.canopy_s3_prefix
S3_HTTP_BASE = f"https://{S3_BUCKET}.s3.amazonaws.com/{S3_PREFIX}"

# QuadKey zoom level used by the dataset (from settings)
TILE_ZOOM = settings.canopy_tile_zoom

# Maximum canopy height treated as full shade (from settings)
SHADE_MAX_HEIGHT = settings.canopy_shade_max_height


# ── QuadKey Computation ──────────────────────────────────────────────

def _latlon_to_quadkey(lat: float, lon: float, zoom: int = TILE_ZOOM) -> str:
    """
    Convert lat/lon to a Bing Maps QuadKey at the given zoom level.

    Uses the standard Web Mercator tile pyramid:
      lat/lon → pixel XY → tile XY → QuadKey

    Args:
        lat: Latitude in decimal degrees (-85.05 to 85.05)
        lon: Longitude in decimal degrees (-180 to 180)
        zoom: Tile zoom level

    Returns:
        str: QuadKey string (e.g. "021301332")
    """
    lat = max(min(lat, 85.05112878), -85.05112878)
    lon = max(min(lon, 180.0), -180.0)

    sin_lat = math.sin(lat * math.pi / 180.0)
    n = 2.0 ** zoom

    pixel_x = ((lon + 180.0) / 360.0) * 256 * n
    pixel_y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * 256 * n

    tile_x = int(pixel_x // 256)
    tile_y = int(pixel_y // 256)

    # Clamp to valid range
    tile_x = max(0, min(tile_x, int(n) - 1))
    tile_y = max(0, min(tile_y, int(n) - 1))

    quadkey = ""
    for i in range(zoom, 0, -1):
        digit = 0
        mask = 1 << (i - 1)
        if (tile_x & mask) != 0:
            digit += 1
        if (tile_y & mask) != 0:
            digit += 2
        quadkey += str(digit)

    return quadkey


def _get_tile_url(quadkey: str) -> str:
    """Return the HTTPS URL for a canopy height tile by QuadKey."""
    return f"{S3_HTTP_BASE}/{quadkey}.tif"


def _get_tile_s3_path(quadkey: str) -> str:
    """Return the S3 URI for a canopy height tile by QuadKey."""
    return f"s3://{S3_BUCKET}/{S3_PREFIX}/{quadkey}.tif"


# ── Data Fetching ────────────────────────────────────────────────────

def fetch_canopy_at_point(lat: float, lon: float) -> float | None:
    """
    Fetch tree canopy height (meters) at a specific lat/lon.

    Strategy:
    1. Compute the QuadKey for the given coordinates
    2. Open the corresponding COG tile from S3
    3. Read the single pixel at the point's location

    Args:
        lat: Latitude (decimal degrees)
        lon: Longitude (decimal degrees)

    Returns:
        float: Canopy height in meters (0 = no trees), or None if no data.
    """
    quadkey = _latlon_to_quadkey(lat, lon)

    if HAS_RASTERIO:
        return _fetch_via_rasterio(lat, lon, quadkey)
    else:
        return _fetch_via_http(lat, lon, quadkey)


def fetch_canopy_batch(points: list[tuple[float, float]]) -> list[dict]:
    """
    Fetch canopy heights for a batch of points with quality tracking.

    Groups points by QuadKey so each COG tile is opened only once.
    Falls back to per-point fetching if the batch read fails.

    Args:
        points: List of (lat, lon) tuples.

    Returns:
        List of dicts (same order as input) with keys:
          - "value": float or None
          - "quality": "real" | "default" | "unavailable"
    """
    from collections import defaultdict

    # Map each input index to its QuadKey and coordinates
    quadkey_groups: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
    for idx, (lat, lon) in enumerate(points):
        qk = _latlon_to_quadkey(lat, lon)
        quadkey_groups[qk].append((idx, lat, lon))

    results: list[dict | None] = [None] * len(points)

    for quadkey, group in quadkey_groups.items():
        if HAS_RASTERIO:
            try:
                _batch_read_tile(quadkey, group, results)
                continue
            except Exception:
                pass  # fall through to per-point

        # Per-point fallback (no rasterio, or batch read failed)
        for idx, lat, lon in group:
            try:
                value = fetch_canopy_at_point(lat, lon)
                if value is not None:
                    results[idx] = {"value": value, "quality": "real"}
                else:
                    results[idx] = {"value": None, "quality": "default"}
            except Exception:
                results[idx] = {"value": None, "quality": "unavailable"}

    return results  # type: ignore[return-value]


def _batch_read_tile(
    quadkey: str,
    group: list[tuple[int, float, float]],
    results: list[dict | None],
) -> None:
    """
    Open a single COG tile and read pixel values for all points in *group*.

    Populates *results* in-place. Raises on tile-level failures so the
    caller can fall back to per-point fetching.
    """
    tile_url = _get_tile_s3_path(quadkey)

    env_kwargs = {}
    try:
        import boto3
        from botocore.config import Config as BotoConfig  # noqa: F811
        session = boto3.Session()
        aws_session = AWSSession(session, aws_unsigned=True)
        env_kwargs["session"] = aws_session
    except ImportError:
        tile_url = _get_tile_url(quadkey)

    with rasterio.Env(**env_kwargs):
        with rasterio.open(tile_url) as src:
            for idx, lat, lon in group:
                try:
                    row, col = src.index(lon, lat)
                    if row < 0 or row >= src.height or col < 0 or col >= src.width:
                        results[idx] = {"value": None, "quality": "default"}
                        continue
                    window = Window(col, row, 1, 1)
                    data = src.read(1, window=window)
                    value = float(data[0, 0])
                    if src.nodata is not None and value == src.nodata:
                        results[idx] = {"value": None, "quality": "default"}
                    elif value < 0:
                        results[idx] = {"value": None, "quality": "default"}
                    else:
                        results[idx] = {"value": value, "quality": "real"}
                except Exception:
                    results[idx] = {"value": None, "quality": "unavailable"}


def _fetch_via_rasterio(lat: float, lon: float, quadkey: str) -> float | None:
    """Read a single pixel from the COG using rasterio (efficient)."""
    tile_url = _get_tile_s3_path(quadkey)

    try:
        env_kwargs = {}
        # Configure anonymous S3 access
        import boto3
        from botocore.config import Config as BotoConfig
        session = boto3.Session()
        aws_session = AWSSession(session, aws_unsigned=True)
        env_kwargs["session"] = aws_session
    except ImportError:
        # Fall back to HTTPS if boto3 is not available
        tile_url = _get_tile_url(quadkey)
        env_kwargs = {}

    try:
        with rasterio.Env(**env_kwargs):
            with rasterio.open(tile_url) as src:
                # Transform lat/lon to the raster's CRS pixel coordinates
                row, col = src.index(lon, lat)

                # Bounds check
                if row < 0 or row >= src.height or col < 0 or col >= src.width:
                    return None

                # Windowed read — only fetches the needed COG block
                window = Window(col, row, 1, 1)
                data = src.read(1, window=window)
                value = float(data[0, 0])

                # NoData handling
                if src.nodata is not None and value == src.nodata:
                    return None
                if value < 0:
                    return None

                return value

    except Exception:
        # Tile may not exist for this location (e.g., ocean)
        return None


def _fetch_via_http(lat: float, lon: float, quadkey: str) -> float | None:
    """
    Fallback: Check if the tile exists via HTTP HEAD request.
    Can't read pixel values without rasterio, but can confirm data coverage.

    Returns a rough estimate based on tile existence (placeholder until
    rasterio is available in the environment).
    """
    tile_url = _get_tile_url(quadkey)

    try:
        resp = requests.head(tile_url, timeout=10)
        if resp.status_code == 200:
            # Tile exists — we know there's data here, but can't read
            # the exact pixel without rasterio. Return a sentinel that
            # indicates "data available but value unknown".
            # The pipeline should handle this gracefully.
            logger.warning(
                "Canopy tile exists for quadkey %s but cannot be read "
                "without rasterio. Install rasterio for actual canopy data.",
                quadkey,
            )
            return None  # TODO: implement HTTP range-based COG reading
        else:
            return None
    except Exception:
        return None


def fetch_canopy_for_bbox(bbox: tuple, sample_points: int = 25) -> list:
    """
    Sample canopy height across a bounding box on a grid.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        sample_points: Number of points to sample

    Returns:
        list of float|None: Canopy heights (meters) at each sample point.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    grid_size = int(math.sqrt(sample_points))

    values = []
    for i in range(grid_size):
        for j in range(grid_size):
            lat = min_lat + (max_lat - min_lat) * (i + 0.5) / grid_size
            lon = min_lon + (max_lon - min_lon) * (j + 0.5) / grid_size
            val = fetch_canopy_at_point(lat, lon)
            values.append(val)

    return values


def get_shade_penalty(canopy_height_m: float) -> float:
    """
    Convert canopy height (meters) to a shade penalty (0.0 - 1.0).

    Taller trees = more shade = less penalty.
    Thresholds based on urban forestry shade studies:
    - >= SHADE_MAX_HEIGHT: Full shade canopy (large deciduous/evergreen) → 0.0 penalty
    - 0m: No trees at all → 1.0 penalty
    - Linear interpolation between

    Args:
        canopy_height_m: Tree canopy height in meters

    Returns:
        float: Penalty value between 0.0 (full shade) and 1.0 (no shade)
    """
    canopy_height_m = max(0.0, float(canopy_height_m))
    if canopy_height_m >= SHADE_MAX_HEIGHT:
        return 0.0
    else:
        return 1.0 - (canopy_height_m / SHADE_MAX_HEIGHT)


def height_to_cover_pct(canopy_height_m: float) -> float:
    """
    Convert canopy height to an estimated canopy cover percentage (0-100).

    This is a rough mapping used by the scoring engine which expects
    a 0-100 percentage input. Based on the relationship:
    - 0m height → 0% cover
    - >= SHADE_MAX_HEIGHT height → 100% cover (mature tree providing full shade)
    - Linear interpolation between

    Args:
        canopy_height_m: Tree canopy height in meters

    Returns:
        float: Estimated canopy cover percentage (0-100)
    """
    canopy_height_m = max(0.0, float(canopy_height_m))
    if canopy_height_m >= SHADE_MAX_HEIGHT:
        return 100.0
    return (canopy_height_m / SHADE_MAX_HEIGHT) * 100.0
