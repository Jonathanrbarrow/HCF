"""
Network module — fetches pedestrian walk networks from OpenStreetMap.

Uses OSMnx to query the Overpass API. All functions are parameterized
by place name or bounding box — zero hardcoded coordinates.
"""
import osmnx as ox


def fetch_walk_network(place_query: str):
    """
    Fetch the pedestrian walk network for a named place.

    Args:
        place_query: OSMnx-compatible place string, e.g. "Denver, Colorado, USA"

    Returns:
        networkx.MultiDiGraph: The walk network graph with geometry attributes.

    Raises:
        Exception: If OSMnx cannot geocode or fetch the place.
    """
    graph = ox.graph_from_place(
        place_query,
        network_type="walk",
        simplify=True,
    )
    # Ensure all edges have geometry (not just start/end nodes)
    graph = ox.add_edge_lengths(graph)
    return graph


def fetch_walk_network_bbox(bbox: tuple):
    """
    Fetch the pedestrian walk network for a bounding box.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)

    Returns:
        networkx.MultiDiGraph: The walk network graph.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    # OSMnx uses (north, south, east, west) ordering
    graph = ox.graph_from_bbox(
        north=max_lat, south=min_lat,
        east=max_lon, west=min_lon,
        network_type="walk",
        simplify=True,
    )
    graph = ox.add_edge_lengths(graph)
    return graph


def network_to_geodataframe(graph):
    """
    Convert an OSMnx graph to a GeoDataFrame of edges (street segments).

    Args:
        graph: networkx.MultiDiGraph from fetch_walk_network

    Returns:
        geopandas.GeoDataFrame: Edges with geometry and attributes.
    """
    edges = ox.graph_to_gdfs(graph, nodes=False)
    return edges
