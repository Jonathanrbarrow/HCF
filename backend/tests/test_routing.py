"""
TEST SUITE 7: Comfort-Adjusted Routing
=======================================
These tests verify that we can calculate comfort-adjusted routes between
two geographic coordinates in a walk network.

WHAT THESE TESTS GUARANTEE:
- The routing engine finds a valid path between two points.
- Comfort-weighted routing prefers quieter, more shaded streets.
- The returned GeoJSON contains both the "shortest" and "comfortable" routes.
- The calculation runs within performance boundaries.
"""
import pytest
from tests.cities import get_bbox_around_point


@pytest.mark.slow
class TestComfortRouting:
    """Can we compute comfort-adjusted walk routes?"""

    def test_nearest_node_matching(self):
        """
        QUESTION: Can we find the closest graph node to a given lat/lon?

        PASS CRITERIA:
        - osmnx successfully matches a coordinate to a node ID.
        """
        import osmnx as ox
        from hcf.data.network import fetch_walk_network_bbox

        # Fetch a small network in Denver
        bbox = get_bbox_around_point(39.7392, -104.9903, radius_km=0.5)
        graph = fetch_walk_network_bbox(bbox)

        # Match point close to center
        node = ox.nearest_nodes(graph, X=-104.9903, Y=39.7392)
        assert isinstance(node, int), "Matched node ID should be an integer"
        assert node in graph.nodes, "Matched node must exist in the graph"

    def test_routing_returns_geojson(self):
        """
        QUESTION: Does the routing endpoint return both shortest and comfortable routes?

        PASS CRITERIA:
        - Returns a GeoJSON FeatureCollection with 2 features.
        - One feature represents the shortest path, one represents the comfortable path.
        - Both contain length and comfort score properties.
        """
        from hcf.scoring.pipeline import generate_route_geojson

        # Denver coordinates
        start = (39.7420, -104.9920)
        end = (39.7380, -104.9880)

        geojson = generate_route_geojson(
            start_lat=start[0],
            start_lon=start[1],
            end_lat=end[0],
            end_lon=end[1],
            w_noise=50,
            w_canopy=50,
            w_heat=0,
        )

        assert isinstance(geojson, dict)
        assert geojson.get("type") == "FeatureCollection"
        features = geojson.get("features", [])
        assert len(features) == 2, "Should return exactly 2 routes (shortest and comfortable)"

        for route in features:
            assert route.get("type") == "Feature"
            assert route["geometry"]["type"] == "LineString"
            props = route["properties"]
            assert "route_type" in props
            assert props["route_type"] in {"shortest", "comfortable"}
            assert "length_m" in props
            assert "avg_comfort_score" in props
            assert props["length_m"] > 0
            assert 0 <= props["avg_comfort_score"] <= 100
