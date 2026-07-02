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
import networkx as nx
from shapely.geometry import mapping, LineString

from hcf.config import settings
from hcf.data.network import fetch_walk_network, fetch_walk_network_bbox, network_to_geodataframe
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


def _score_graph_edges(graph, w_noise: float, w_canopy: float, w_heat: float):
    """
    Score all edges in a graph and assign length + comfort weights.
    Modifies graph in-place.
    """
    # Extract edges as GDF
    edges = network_to_geodataframe(graph)
    if len(edges) == 0:
        return

    # Extract midpoints
    midpoints = []
    for _, row in edges.iterrows():
        midpoint = row.geometry.interpolate(0.5, normalized=True)
        midpoints.append((midpoint.y, midpoint.x))

    # Batch query environment
    noise_results = fetch_noise_batch(midpoints)
    canopy_results = fetch_canopy_batch(midpoints)
    heat_results = fetch_heat_batch(midpoints)

    # Calculate comfort scores for all edges
    edge_scores = {}
    for idx, (u, v, key) in enumerate(graph.edges(keys=True)):
        noise = noise_results[idx]["value"] if noise_results[idx]["value"] is not None else settings.noise_default_dba
        canopy_val = canopy_results[idx]["value"]
        canopy_pct = height_to_cover_pct(canopy_val) if canopy_val is not None else 20.0
        heat = heat_results[idx]["value"] if heat_results[idx]["value"] is not None else settings.default_heat_index

        score = compute_comfort_score(
            noise_dba=noise,
            canopy_pct=canopy_pct,
            heat_index=heat,
            weights={"noise": w_noise, "canopy": w_canopy, "heat": w_heat}
        )

        edge_scores[(u, v, key)] = score

    # Write weights to the graph edges
    for u, v, k, d in graph.edges(keys=True, data=True):
        score = edge_scores.get((u, v, k), 50.0)
        length = float(d.get("length", 1.0))
        
        # Penalize low-comfort streets (up to 3x length penalty)
        penalty_factor = (1.0 - (score / 100.0)) * 2.0
        comfort_weight = length * (1.0 + penalty_factor)

        d["comfort_score"] = score
        d["comfort_weight"] = comfort_weight


def generate_route_geojson(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    w_noise: float = 33.3,
    w_canopy: float = 33.3,
    w_heat: float = 33.3,
) -> dict:
    """
    Generate a GeoJSON FeatureCollection containing two walk routes:
    1. Shortest path (by physical distance)
    2. Comfortable path (adjusted by noise/shade/heat weights)

    Returns:
        dict: GeoJSON FeatureCollection
    """
    # 1. Bounding box enclosing the start and end coordinates with a margin (~1.5 km)
    min_lat = min(start_lat, end_lat) - 0.015
    max_lat = max(start_lat, end_lat) + 0.015
    min_lon = min(start_lon, end_lon) - 0.015
    max_lon = max(start_lon, end_lon) + 0.015

    bbox = (min_lon, min_lat, max_lon, max_lat)

    # 2. Fetch network graph for the bounding box
    graph = fetch_walk_network_bbox(bbox)

    # 3. Score all edges in the graph
    _score_graph_edges(graph, w_noise, w_canopy, w_heat)

    # 4. Match start/end coordinates to closest graph nodes
    source_node = ox.nearest_nodes(graph, X=start_lon, Y=start_lat)
    target_node = ox.nearest_nodes(graph, X=end_lon, Y=end_lat)

    # 5. Compute shortest and comfortable paths
    try:
        shortest_path = nx.shortest_path(graph, source_node, target_node, weight="length")
        comfortable_path = nx.shortest_path(graph, source_node, target_node, weight="comfort_weight")
    except nx.NetworkXNoPath:
        # Fallback if no path exists
        return {
            "type": "FeatureCollection",
            "features": [],
            "metadata": {"error": "No walking route found between these points"}
        }

    # Helper to convert list of node IDs to LineString geometry & compute stats
    def build_route_feature(node_list, route_type):
        coords = []
        lengths = []
        scores = []
        for idx in range(len(node_list) - 1):
            u, v = node_list[idx], node_list[idx + 1]
            # Match edge data
            edge_data = graph.get_edge_data(u, v)
            if edge_data:
                # Use first edge if multiple keys
                data = list(edge_data.values())[0]
                lengths.append(data.get("length", 0.0))
                scores.append(data.get("comfort_score", 50.0))
            
            node_data = graph.nodes[u]
            coords.append((node_data["x"], node_data["y"]))

        # Add the final node coordinate
        last_node_data = graph.nodes[node_list[-1]]
        coords.append((last_node_data["x"], last_node_data["y"]))

        # Build feature properties
        total_len = sum(lengths)
        avg_score = sum(scores) / len(scores) if scores else 50.0

        return {
            "type": "Feature",
            "geometry": mapping(LineString(coords)),
            "properties": {
                "route_type": route_type,
                "length_m": total_len,
                "avg_comfort_score": round(avg_score, 1),
            }
        }

    shortest_feature = build_route_feature(shortest_path, "shortest")
    comfortable_feature = build_route_feature(comfortable_path, "comfortable")

    return {
        "type": "FeatureCollection",
        "features": [shortest_feature, comfortable_feature],
        "metadata": {
            "start": [start_lon, start_lat],
            "end": [end_lon, end_lat],
        }
    }

