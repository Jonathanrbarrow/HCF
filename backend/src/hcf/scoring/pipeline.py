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
import osmnx as ox
import geopandas as gpd
from shapely.geometry import mapping

from hcf.config import settings
from hcf.data.network import fetch_walk_network, network_to_geodataframe
from hcf.data.noise import fetch_noise_batch
from hcf.data.canopy import fetch_canopy_batch, height_to_cover_pct
from hcf.data.heat import fetch_heat_batch
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

    # Step 3: Batch fetch environmental data
    noise_results = fetch_noise_batch(midpoints)
    canopy_results = fetch_canopy_batch(midpoints)
    heat_results = fetch_heat_batch(midpoints)

    # Step 4: Assemble columns
    edges = edges.copy()
    edges["noise_dba"] = [r["value"] for r in noise_results]
    edges["canopy_height_m"] = [r["value"] for r in canopy_results]
    edges["heat_index"] = [r["value"] for r in heat_results]

    # Convert canopy height to estimated cover percentage
    edges["canopy_pct"] = [
        height_to_cover_pct(r["value"]) if r["value"] is not None else 20.0
        for r in canopy_results
    ]

    # Build per-segment data quality dicts
    data_qualities = [
        {
            "noise": noise_results[i]["quality"],
            "canopy": canopy_results[i]["quality"],
            "heat": heat_results[i]["quality"],
        }
        for i in range(len(edges))
    ]
    edges["data_quality"] = data_qualities

    # Step 5: Compute comfort scores
    scores = []
    for _, row in edges.iterrows():
        noise = row["noise_dba"] if row["noise_dba"] is not None else settings.noise_default_dba
        canopy = row["canopy_pct"]
        heat = row["heat_index"] if row["heat_index"] is not None else settings.default_heat_index

        score = compute_comfort_score(
            noise_dba=noise,
            canopy_pct=canopy,
            heat_index=heat,
        )
        scores.append(score)

    edges["comfort_score"] = scores

    return edges[["geometry", "comfort_score", "noise_dba",
                   "canopy_height_m", "canopy_pct", "heat_index", "data_quality"]]


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


