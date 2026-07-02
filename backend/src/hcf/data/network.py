"""
Network module — fetches pedestrian walk networks from OpenStreetMap.

Uses OSMnx 2.x to query the Overpass API. All functions are parameterized
by place name or bounding box — zero hardcoded coordinates.

OSMnx 2.x API notes:
  - graph_from_bbox() takes a single bbox tuple: (west, south, east, north)
    i.e., (min_lon, min_lat, max_lon, max_lat)
  - Edge lengths are auto-calculated during graph creation
  - add_edge_lengths() is no longer needed
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
    return graph


def fetch_walk_network_bbox(bbox: tuple):
    """
    Fetch the pedestrian walk network for a bounding box.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat) — same as (west, south, east, north)

    Returns:
        networkx.MultiDiGraph: The walk network graph.
    """
    # OSMnx 2.x takes bbox as a single tuple: (west, south, east, north)
    # Our convention: (min_lon, min_lat, max_lon, max_lat)
    # These are the same order, so pass directly.
    graph = ox.graph_from_bbox(
        bbox=bbox,
        network_type="walk",
        simplify=True,
    )
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
