"""
Pipeline module — orchestrates the full comfort scoring pipeline.

  City name → OSM network → Environmental data → Scoring → GeoJSON

This is the core integration layer. Every function is parameterized
by city name or bounding box — zero hardcoded coordinates.

Features:
  - Cached walk networks (24h TTL) and results (1h TTL)
  - Batch environmental data fetching (grouped by tile/region)
  - Per-segment data quality tracking
"""
import re

import osmnx as ox
import pandas as pd
import geopandas as gpd
from shapely.geometry import mapping

from hcf.config import settings
from hcf.data.network import fetch_walk_network, network_to_geodataframe
from hcf.data.noise import fetch_noise_batch
from hcf.data.canopy import fetch_canopy_batch, height_to_cover_pct
from hcf.data.heat import fetch_heat_batch
from hcf.data.traffic import fetch_traffic_batch
from hcf.scoring.engine import compute_comfort_score
from hcf.cache.store import (
    get_network_cache, set_network_cache,
    get_result_cache, set_result_cache,
)


def _fetch_network_cached(place_query: str):
    """Fetch walk network with 24h file cache."""
    cached = get_network_cache(place_query)
    if cached is not None:
        return cached
    graph = fetch_walk_network(place_query)
    set_network_cache(place_query, graph)
    return graph


def score_city_segments(place_query: str, max_segments: int = 500) -> gpd.GeoDataFrame:
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
    if max_segments and len(edges) > max_segments:
        edges = edges.sample(n=max_segments, random_state=42)

    # Step 2: Extract midpoints for batch fetching
    midpoints = []
    for _, row in edges.iterrows():
        midpoint = row.geometry.interpolate(0.5, normalized=True)
        midpoints.append((midpoint.y, midpoint.x))

    # Step 3: Batch fetch environmental data (respecting feature flags)
    if settings.enable_noise_factor:
        noise_results = fetch_noise_batch(midpoints)
    else:
        noise_results = [{"value": None, "quality": "disabled"} for _ in midpoints]

    if settings.enable_canopy_factor:
        canopy_results = fetch_canopy_batch(midpoints)
    else:
        canopy_results = [{"value": None, "quality": "disabled"} for _ in midpoints]

    if settings.enable_heat_factor:
        heat_results = fetch_heat_batch(midpoints)
    else:
        heat_results = [{"value": None, "quality": "disabled"} for _ in midpoints]

    traffic_results = fetch_traffic_batch(midpoints)  # internally checks its own flag

    # Step 4: Assemble columns
    edges = edges.copy()
    edges["noise_dba"] = [r["value"] for r in noise_results]
    edges["canopy_height_m"] = [r["value"] for r in canopy_results]
    edges["heat_index"] = [r["value"] for r in heat_results]
    edges["traffic_volume"] = [r["value"] for r in traffic_results]

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
        height_to_cover_pct(r["value"]) if r["value"] is not None else 20.0
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
            "safety": "real" if has_real_safety else "default",
            "traffic": traffic_results[i]["quality"],
        })
    edges["data_quality"] = data_qualities

    # Step 5: Compute comfort scores (disabled factors pass None → auto-excluded)
    scores = []
    for _, row in edges.iterrows():
        noise = row["noise_dba"] if pd.notna(row["noise_dba"]) else (
            settings.noise_default_dba if settings.enable_noise_factor else None
        )
        canopy = row["canopy_pct"] if settings.enable_canopy_factor else None
        heat = row["heat_index"] if pd.notna(row["heat_index"]) else (
            settings.default_heat_index if settings.enable_heat_factor else None
        )
        safety = row["safety_score"] if settings.enable_safety_factor else None
        traffic = row["traffic_volume"] if pd.notna(row.get("traffic_volume")) else (
            None  # engine handles None → excluded
        )

        score = compute_comfort_score(
            noise_dba=noise,
            canopy_pct=canopy,
            heat_index=heat,
            safety_score=safety,
            traffic_volume=traffic,
        )
        scores.append(score)

    edges["comfort_score"] = scores

    return edges[["geometry", "comfort_score", "noise_dba",
                   "canopy_height_m", "canopy_pct", "heat_index",
                   "safety_score", "traffic_volume",
                   "street_name", "data_quality"]]


def generate_comfort_geojson(place_query: str, max_segments: int = 200) -> dict:
    """
    Generate a GeoJSON FeatureCollection of scored street segments.

    Uses result caching (1h TTL) to avoid re-computing for the same city.

    Args:
        place_query: OSMnx place string
        max_segments: Maximum segments to include

    Returns:
        dict: GeoJSON FeatureCollection ready for json.dumps()
    """
    # Check result cache
    cached = get_result_cache(place_query, max_segments)
    if cached is not None:
        return cached

    scored = score_city_segments(place_query, max_segments=max_segments)

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
        },
    }

    # Cache for 1 hour
    set_result_cache(place_query, max_segments, result)

    return result


