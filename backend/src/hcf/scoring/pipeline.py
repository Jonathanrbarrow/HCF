"""
Pipeline module — orchestrates the full comfort scoring pipeline.

  City name → OSM network → Environmental data → Scoring → GeoJSON

This is the core integration layer. Every function is parameterized
by city name or bounding box — zero hardcoded coordinates.

Features:
  - Cached walk networks (24h TTL) and results (30d TTL)
  - Batch environmental data fetching (grouped by tile/region)
  - Per-segment data quality tracking
"""
import logging
import re
import time

import osmnx as ox
import pandas as pd
import geopandas as gpd
from shapely.geometry import mapping

from hcf.config import settings
from hcf.data.quality import REAL, DEFAULT, DISABLED
from hcf.data.network import fetch_walk_network, network_to_geodataframe
from hcf.data.noise import fetch_noise_batch
from hcf.data.canopy import fetch_canopy_batch, height_to_cover_pct
from hcf.data.heat import fetch_heat_batch
from hcf.data.traffic import fetch_traffic_batch
from hcf.data.aqi import fetch_aqi_batch
from hcf.scoring.engine import compute_comfort_score
from hcf.cache.store import (
    get_network_cache, set_network_cache,
    get_result_cache, set_result_cache,
)

logger = logging.getLogger(__name__)


def _fetch_network_cached(place_query: str):
    """Fetch walk network with 24h file cache."""
    cached = get_network_cache(place_query)
    if cached is not None:
        return cached
    graph = fetch_walk_network(place_query)
    set_network_cache(place_query, graph)
    return graph


def score_city_segments(place_query: str, max_segments: int = 200) -> gpd.GeoDataFrame:
    """
    Fetch a city's walk network, sample environmental data for each
    segment, and compute comfort scores.

    Args:
        place_query: OSMnx place string, e.g. "Denver, Colorado, USA"
        max_segments: Maximum number of segments to score.

    Returns:
        GeoDataFrame with columns: geometry, comfort_score, noise_dba,
        canopy_height_m, canopy_pct, heat_index, data_quality
    """
    # Step 1: Fetch pedestrian network (cached)
    graph = _fetch_network_cached(place_query)
    edges = network_to_geodataframe(graph)

    # Limit segments for API rate limiting
    # Deterministic sampling ensures cache hits — same city + max_segments
    # always returns the same set of segments.  Trade-off: some segments
    # are never scored.  Change seed or increase max_segments to explore.
    if max_segments and len(edges) > max_segments:
        edges = edges.sample(n=max_segments, random_state=42)

    if len(edges) == 0:
        logger.warning(
            "No walkable segments found for '%s'", place_query
        )
        return gpd.GeoDataFrame(columns=["geometry", "comfort_score"])

    # Step 2: Extract midpoints for batch fetching
    midpoints = []
    for _, row in edges.iterrows():
        midpoint = row.geometry.interpolate(0.5, normalized=True)
        midpoints.append((midpoint.y, midpoint.x))

    # Step 3: Batch fetch environmental data concurrently (respecting feature flags)
    from concurrent.futures import ThreadPoolExecutor

    def _get_noise():
        if settings.enable_noise_factor:
            return fetch_noise_batch(midpoints)
        return [{"value": None, "quality": DISABLED} for _ in midpoints]

    def _get_canopy():
        if settings.enable_canopy_factor:
            return fetch_canopy_batch(midpoints)
        return [{"value": None, "quality": DISABLED} for _ in midpoints]

    def _get_heat():
        if settings.enable_heat_factor:
            return fetch_heat_batch(midpoints)
        return [{"value": None, "quality": DISABLED} for _ in midpoints]

    def _get_traffic():
        return fetch_traffic_batch(midpoints)  # internally checks its own flag

    def _get_aqi():
        return fetch_aqi_batch(midpoints)  # internally checks its own flag

    with ThreadPoolExecutor(max_workers=5) as executor:
        noise_future = executor.submit(_get_noise)
        canopy_future = executor.submit(_get_canopy)
        heat_future = executor.submit(_get_heat)
        traffic_future = executor.submit(_get_traffic)
        aqi_future = executor.submit(_get_aqi)

        noise_results = noise_future.result()
        canopy_results = canopy_future.result()
        heat_results = heat_future.result()
        traffic_results = traffic_future.result()
        aqi_results = aqi_future.result()

    # Step 4: Assemble columns
    edges = edges.copy()
    edges["noise_dba"] = [r["value"] for r in noise_results]
    edges["canopy_height_m"] = [r["value"] for r in canopy_results]
    edges["heat_index"] = [r["value"] for r in heat_results]
    edges["traffic_volume"] = [r["value"] for r in traffic_results]
    edges["aqi"] = [r["value"] for r in aqi_results]

    # Extract street name safely
    if "name" in edges.columns:
        street_names = []
        for val in edges["name"]:
            if isinstance(val, list):
                street_names.append(str(val[0]) if val else "Unnamed Path")
            elif isinstance(val, str):
                street_names.append(val)
            else:
                street_names.append("Unnamed Path")
        edges["street_name"] = street_names
    else:
        edges["street_name"] = "Unnamed Path"

    # Convert canopy height to estimated cover percentage
    edges["canopy_pct"] = [
        height_to_cover_pct(r["value"]) if r["value"] is not None else 20.0  # default canopy cover % when data unavailable
        for r in canopy_results
    ]

    # Safety Scoring logic
    safety_scores = []
    for _, row in edges.iterrows():
        # 1. Base penalty by road classification (highway)
        highway = row.get("highway", "unclassified")
        if isinstance(highway, list):
            highway = str(highway[0]) if highway else "unclassified"
        else:
            highway = str(highway)

        if highway in {"motorway", "trunk", "motorway_link", "trunk_link"}:
            base = 0.0  # Hostile
        elif highway in {"primary", "primary_link"}:
            base = 20.0
        elif highway in {"secondary", "secondary_link"}:
            base = 40.0
        elif highway in {"tertiary", "tertiary_link"}:
            base = 60.0
        elif highway in {"residential", "living_street"}:
            base = 90.0
        elif highway in {"footway", "pedestrian", "path", "cycleway"}:
            base = 100.0  # Fully safe
        else:
            base = 70.0  # Moderate default

        # 2. Sidewalk adjustments
        sidewalk = row.get("sidewalk", "none")
        if isinstance(sidewalk, list):
            sidewalk = str(sidewalk[0]) if sidewalk else "none"
        else:
            sidewalk = str(sidewalk)

        if sidewalk in {"both", "left", "right", "yes"}:
            base = min(100.0, base + 20.0)
        elif sidewalk in {"none", "no"}:
            base = max(0.0, base - 20.0)

        # 3. Speed adjustments
        maxspeed = row.get("maxspeed", "NaN")
        if isinstance(maxspeed, list):
            maxspeed = str(maxspeed[0]) if maxspeed else "NaN"
        else:
            maxspeed = str(maxspeed)

        speed_nums = re.findall(r'\d+', maxspeed)
        if speed_nums:
            speed_val = int(speed_nums[0])
            if "km/h" in maxspeed or "kmh" in maxspeed:
                if speed_val > 55:
                    base = max(0.0, base - 10.0)
            else:
                if speed_val > 35:
                    base = max(0.0, base - 10.0)

        # 4. Lanes adjustments
        lanes = row.get("lanes", "NaN")
        if isinstance(lanes, list):
            lanes = str(lanes[0]) if lanes else "NaN"
        else:
            lanes = str(lanes)

        lane_nums = re.findall(r'\d+', lanes)
        if lane_nums:
            lane_val = int(lane_nums[0])
            if lane_val >= 4:
                base = max(0.0, base - 10.0)

        safety_scores.append(base)

    edges["safety_score"] = safety_scores

    # Build per-segment data quality dicts
    data_qualities = []
    for i, (_, row) in enumerate(edges.iterrows()):
        has_real_safety = ("sidewalk" in row.index and pd.notna(row.get("sidewalk")) and row["sidewalk"] not in ("none", "unknown")) or \
                           ("maxspeed" in row.index and pd.notna(row.get("maxspeed"))) or \
                           ("lanes" in row.index and pd.notna(row.get("lanes")))
        
        data_qualities.append({
            "noise": noise_results[i]["quality"],
            "canopy": canopy_results[i]["quality"],
            "heat": heat_results[i]["quality"],
            "safety": REAL if has_real_safety else DEFAULT,
            "traffic": traffic_results[i]["quality"],
            "aqi": aqi_results[i]["quality"],
        })
    edges["data_quality"] = data_qualities

    # Step 5: Compute comfort scores (disabled factors pass None → auto-excluded)
    scores = []
    for _, row in edges.iterrows():
        noise = row.get("noise_dba") if pd.notna(row.get("noise_dba")) else (
            settings.noise_default_dba if settings.enable_noise_factor else None
        )
        canopy = row.get("canopy_pct") if pd.notna(row.get("canopy_pct")) else (
            20.0 if settings.enable_canopy_factor else None
        )
        heat = row.get("heat_index") if pd.notna(row.get("heat_index")) else (
            settings.default_heat_index if settings.enable_heat_factor else None
        )
        safety = row.get("safety_score") if settings.enable_safety_factor else None
        traffic = row.get("traffic_volume") if pd.notna(row.get("traffic_volume")) else (
            settings.traffic_default_aadt if settings.enable_traffic_factor else None
        )
        aqi_val = row.get("aqi") if pd.notna(row.get("aqi")) else (
            settings.aqi_default if settings.enable_aqi_factor else None
        )

        score = compute_comfort_score(
            noise_dba=noise,
            canopy_pct=canopy,
            heat_index=heat,
            safety_score=safety,
            traffic_volume=traffic,
            aqi=aqi_val,
        )
        scores.append(score)

    edges["comfort_score"] = scores

    return edges[["geometry", "comfort_score", "noise_dba",
                   "canopy_height_m", "canopy_pct", "heat_index",
                   "safety_score", "traffic_volume", "aqi",
                   "street_name", "data_quality"]]


def generate_comfort_geojson(place_query: str, max_segments: int = 200) -> dict:
    """
    Generate a GeoJSON FeatureCollection of scored street segments.

    Uses result caching (30d TTL) to avoid re-computing for the same city.

    Args:
        place_query: OSMnx place string
        max_segments: Maximum segments to include

    Returns:
        dict: GeoJSON FeatureCollection ready for json.dumps()
    """
    # Check result cache
    cached = get_result_cache(place_query, max_segments)
    if cached is not None:
        import copy
        cached = copy.deepcopy(cached)
        cached.setdefault("metadata", {})["from_cache"] = True
        return cached

    t0 = time.time()
    scored = score_city_segments(place_query, max_segments=max_segments)
    elapsed = round(time.time() - t0, 2)

    features = []
    for _, row in scored.iterrows():
        feature = {
            "type": "Feature",
            "geometry": mapping(row.geometry),
            "properties": {
                "comfort_score": row["comfort_score"],
                "noise_dba": row["noise_dba"],
                "canopy_height_m": row["canopy_height_m"],
                "canopy_pct": row["canopy_pct"],
                "heat_index": row["heat_index"],
                "safety_score": row["safety_score"],
                "traffic_volume": row["traffic_volume"],
                "aqi": row["aqi"],
                "street_name": row["street_name"],
                "data_quality": row["data_quality"],
            },
        }
        features.append(feature)

    result = {

        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "place": place_query,
            "total_segments": len(features),
            "elapsed_seconds": elapsed,
            "from_cache": False,
            "data_note": "All data is historical/static. Heat = 3-year summer peak avg. Noise = 2020 DOT. Traffic = annual avg.",
        },
    }

    # Cache for 30 days (all data is static/historical)
    set_result_cache(place_query, max_segments, result)

    return result


