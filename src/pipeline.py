"""
Pipeline module — orchestrates the full comfort scoring pipeline.

  City name → OSM network → Environmental data → Scoring → GeoJSON

This is the core integration layer. Every function is parameterized
by city name or bounding box — zero hardcoded coordinates.
"""
import json
import osmnx as ox
import geopandas as gpd
from shapely.geometry import mapping

from src.network import fetch_walk_network, network_to_geodataframe
from src.noise import fetch_noise_at_point, get_noise_penalty
from src.canopy import fetch_canopy_at_point, height_to_cover_pct
from src.scoring import compute_comfort_score


def score_city_segments(place_query: str, max_segments: int = 500) -> gpd.GeoDataFrame:
    """
    Fetch a city's walk network, sample environmental data for each
    segment, and compute comfort scores.

    Args:
        place_query: OSMnx place string, e.g. "Denver, Colorado, USA"
        max_segments: Maximum number of segments to score (for API rate limiting).
                      Set to None to score all segments.

    Returns:
        GeoDataFrame with columns: geometry, comfort_score, noise_dba, canopy_height_m, canopy_pct
    """
    # Step 1: Fetch pedestrian network
    graph = fetch_walk_network(place_query)
    edges = network_to_geodataframe(graph)

    # Limit segments for API rate limiting during MVP
    if max_segments and len(edges) > max_segments:
        edges = edges.sample(n=max_segments, random_state=42)

    # Step 2: Sample environmental data at each segment's midpoint
    noise_values = []
    canopy_height_values = []

    for idx, row in edges.iterrows():
        # Get the midpoint of each street segment
        midpoint = row.geometry.interpolate(0.5, normalized=True)
        lat, lon = midpoint.y, midpoint.x

        # Fetch real environmental data
        noise = fetch_noise_at_point(lat, lon)
        canopy_height = fetch_canopy_at_point(lat, lon)  # meters

        noise_values.append(noise)
        canopy_height_values.append(canopy_height)

    edges = edges.copy()
    edges["noise_dba"] = noise_values
    edges["canopy_height_m"] = canopy_height_values

    # Convert canopy height (meters) to estimated cover percentage for scoring
    edges["canopy_pct"] = [
        height_to_cover_pct(h) if h is not None else 20.0
        for h in canopy_height_values
    ]

    # Step 3: Compute comfort scores
    scores = []
    for _, row in edges.iterrows():
        noise = row["noise_dba"] if row["noise_dba"] is not None else 50.0  # default moderate
        canopy = row["canopy_pct"]  # already defaulted above

        score = compute_comfort_score(
            noise_dba=noise,
            canopy_pct=canopy,
            heat_index=85.0,  # MVP: use a fixed moderate heat value
        )
        scores.append(score)

    edges["comfort_score"] = scores

    return edges[["geometry", "comfort_score", "noise_dba", "canopy_height_m", "canopy_pct"]]


def generate_comfort_geojson(place_query: str, max_segments: int = 200) -> dict:
    """
    Generate a complete GeoJSON FeatureCollection of scored street segments.

    This is the function the API endpoint calls.

    Args:
        place_query: OSMnx place string
        max_segments: Maximum segments to include

    Returns:
        dict: GeoJSON FeatureCollection ready for json.dumps()
    """
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
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "place": place_query,
            "total_segments": len(features),
        },
    }
