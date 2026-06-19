"""
Canopy module — fetches tree canopy cover data from the MRLC/USGS
National Land Cover Database via OGC WMS service.

Data source:
  MRLC NLCD Tree Canopy Cover (USDA Forest Service)
  Available via WMS at https://www.mrlc.gov/geoserver/mrlc_display/wms

The tree canopy cover product provides 30m resolution percentage
canopy cover (0-100%) across the continental US.

No authentication required.
"""
import requests
import math
import struct
from io import BytesIO

# MRLC WMS endpoint for NLCD products
MRLC_WMS_URL = "https://www.mrlc.gov/geoserver/mrlc_display/wms"

# The tree canopy cover layer name
CANOPY_LAYER = "NLCD_2021_Tree_Canopy_L48"


def fetch_canopy_at_point(lat: float, lon: float) -> float | None:
    """
    Fetch tree canopy cover percentage at a specific lat/lon.

    Uses WMS GetFeatureInfo to query the canopy raster at a point.

    Args:
        lat: Latitude (decimal degrees)
        lon: Longitude (decimal degrees)

    Returns:
        float: Canopy cover percentage (0-100), or None if no data.
    """
    # Build a small bbox around the point (1 pixel at ~30m)
    offset = 0.001  # ~111m, enough for a small WMS window
    bbox = f"{lon - offset},{lat - offset},{lon + offset},{lat + offset}"

    params = {
        "service": "WMS",
        "version": "1.1.1",
        "request": "GetFeatureInfo",
        "layers": CANOPY_LAYER,
        "query_layers": CANOPY_LAYER,
        "info_format": "application/json",
        "srs": "EPSG:4326",
        "bbox": bbox,
        "width": 3,
        "height": 3,
        "x": 1,  # center pixel
        "y": 1,
        "feature_count": 1,
    }

    try:
        resp = requests.get(MRLC_WMS_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        if not features:
            return None

        props = features[0].get("properties", {})
        # Try common field names for the raster value
        for key in ["GRAY_INDEX", "Gray_Index", "gray_index", "value", "Value",
                     "PIXEL_VALUE", "pixel_value", "Band1"]:
            if key in props:
                try:
                    val = float(props[key])
                    if val >= 0:
                        return min(val, 100.0)  # Clamp to valid range
                except (ValueError, TypeError):
                    continue

        # Try first numeric value in properties
        for key, val in props.items():
            try:
                fval = float(val)
                if 0 <= fval <= 100:
                    return fval
            except (ValueError, TypeError):
                continue

        return None

    except Exception:
        # Fallback: try GetMap and read the pixel value directly
        return _fetch_canopy_via_getmap(lat, lon)


def _fetch_canopy_via_getmap(lat: float, lon: float) -> float | None:
    """
    Fallback: Fetch canopy by getting a tiny raster image and reading
    the center pixel value directly.
    """
    offset = 0.0005
    bbox = f"{lon - offset},{lat - offset},{lon + offset},{lat + offset}"

    params = {
        "service": "WMS",
        "version": "1.1.1",
        "request": "GetMap",
        "layers": CANOPY_LAYER,
        "styles": "",
        "srs": "EPSG:4326",
        "bbox": bbox,
        "width": 3,
        "height": 3,
        "format": "image/tiff",
    }

    try:
        resp = requests.get(MRLC_WMS_URL, params=params, timeout=20)
        resp.raise_for_status()

        # Try to read with rasterio if available
        try:
            import rasterio
            from rasterio.io import MemoryFile
            with MemoryFile(resp.content) as memfile:
                with memfile.open() as dataset:
                    data = dataset.read(1)  # Read first band
                    center_val = data[1, 1]  # Center pixel of 3x3
                    if center_val >= 0:
                        return float(min(center_val, 100))
        except ImportError:
            pass

        # Ultra-fallback: try PIL
        try:
            from PIL import Image
            img = Image.open(BytesIO(resp.content))
            pixel = img.getpixel((1, 1))
            if isinstance(pixel, tuple):
                pixel = pixel[0]
            return float(min(max(pixel, 0), 100))
        except ImportError:
            pass

        return None

    except Exception:
        return None


def fetch_canopy_for_bbox(bbox: tuple, sample_points: int = 25) -> list:
    """
    Sample canopy cover across a bounding box on a grid.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        sample_points: Number of points to sample

    Returns:
        list of float|None: Canopy cover percentages at each sample point.
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


def get_shade_penalty(canopy_pct: float) -> float:
    """
    Convert canopy cover percentage to a shade penalty (0.0 - 1.0).

    More canopy = less penalty (more shade = more comfortable).

    Args:
        canopy_pct: Tree canopy cover percentage (0-100)

    Returns:
        float: Penalty value between 0.0 (full shade) and 1.0 (no shade)
    """
    canopy_pct = max(0, min(100, canopy_pct))  # Clamp to 0-100
    return 1.0 - (canopy_pct / 100.0)
