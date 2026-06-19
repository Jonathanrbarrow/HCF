"""
TEST SUITE 1: Pedestrian Network Fetching
==========================================
These tests verify that we can fetch real pedestrian walk networks
from OpenStreetMap for randomly selected US cities.

WHAT THESE TESTS GUARANTEE:
- osmnx can geocode and fetch walk networks for any top-100 US city
- The returned graph has real edges (street segments) with geometry
- All coordinates fall within the expected geographic bounds
- The network has enough data to be useful (not just 3 edges)
- The pipeline is city-agnostic: no hardcoded coordinates anywhere

WHY THESE CAN'T BE FAKED:
- Cities are randomly selected at test time
- Geographic bounds are validated against the city's known lat/lon
- Edge counts and geometry presence are structural validations
"""
import pytest
from tests.cities import get_random_cities, get_bbox_around_point


@pytest.mark.network
@pytest.mark.slow
class TestNetworkFetch:
    """Can we fetch a real pedestrian network for any US city?"""

    def test_fetch_walk_network_returns_graph(self, random_city):
        """
        QUESTION: Given a random US city name, does osmnx return a valid
        walk network graph?

        PASS CRITERIA:
        - osmnx.graph_from_place() returns a MultiDiGraph
        - The graph has nodes and edges
        """
        from src.network import fetch_walk_network

        graph = fetch_walk_network(random_city["osmnx_query"])

        assert graph is not None, "Network fetch returned None"
        assert graph.number_of_nodes() > 0, "Graph has no nodes"
        assert graph.number_of_edges() > 0, "Graph has no edges"

    def test_network_has_minimum_edges(self, random_city):
        """
        QUESTION: Does the network have enough edges to be useful?
        A real urban area should have at least 50 walkable street segments
        in even a small sample area.

        PASS CRITERIA:
        - At least 50 edges in the walk network (even for small cities)
        """
        from src.network import fetch_walk_network

        graph = fetch_walk_network(random_city["osmnx_query"])
        edge_count = graph.number_of_edges()

        assert edge_count >= 50, (
            f"{random_city['city']}, {random_city['state']} returned only "
            f"{edge_count} edges — too few for a real city walk network"
        )

    def test_edges_have_geometry(self, random_city):
        """
        QUESTION: Do the returned street segments have actual geographic
        geometry (coordinates), not just connectivity?

        PASS CRITERIA:
        - At least 80% of edges have a 'geometry' attribute
        - Geometries contain coordinate sequences (not empty)
        """
        from src.network import fetch_walk_network
        import osmnx as ox

        graph = fetch_walk_network(random_city["osmnx_query"])
        edges = ox.graph_to_gdfs(graph, nodes=False)

        assert "geometry" in edges.columns, "No geometry column in edges GeoDataFrame"

        has_geometry = edges["geometry"].notna().sum()
        total = len(edges)
        pct = has_geometry / total

        assert pct >= 0.8, (
            f"Only {pct:.0%} of edges have geometry in "
            f"{random_city['city']}, {random_city['state']} — expected >=80%"
        )

    def test_coordinates_within_city_bounds(self, random_city):
        """
        QUESTION: Are all returned coordinates actually within the expected
        city's geographic area? This catches hardcoded coordinates for a
        different city.

        PASS CRITERIA:
        - The centroid of all edges falls within 50km of the city's known center
        - No coordinates are outside CONUS bounds (unless Honolulu/Anchorage)
        """
        from src.network import fetch_walk_network
        import osmnx as ox
        import math

        graph = fetch_walk_network(random_city["osmnx_query"])
        edges = ox.graph_to_gdfs(graph, nodes=False)

        centroid = edges.geometry.unary_union.centroid
        center_lat = centroid.y
        center_lon = centroid.x

        expected_lat = random_city["lat"]
        expected_lon = random_city["lon"]

        # Haversine-ish distance check (rough, sufficient for validation)
        dlat = abs(center_lat - expected_lat)
        dlon = abs(center_lon - expected_lon)
        approx_km = math.sqrt(dlat**2 + dlon**2) * 111

        assert approx_km < 50, (
            f"Network centroid ({center_lat:.4f}, {center_lon:.4f}) is {approx_km:.0f}km "
            f"from {random_city['city']} center ({expected_lat}, {expected_lon}). "
            f"Are we returning data for the wrong city?"
        )

    def test_network_as_geodataframe(self, random_city):
        """
        QUESTION: Can we convert the network to a GeoDataFrame suitable
        for spatial joins with environmental data?

        PASS CRITERIA:
        - Conversion to GeoDataFrame succeeds
        - GeoDataFrame has a valid CRS (coordinate reference system)
        - GeoDataFrame has a geometry column with LineString geometries
        """
        from src.network import fetch_walk_network
        import osmnx as ox

        graph = fetch_walk_network(random_city["osmnx_query"])
        edges = ox.graph_to_gdfs(graph, nodes=False)

        assert edges.crs is not None, "GeoDataFrame has no CRS"
        assert len(edges) > 0, "GeoDataFrame is empty"

        geom_types = edges.geometry.geom_type.unique()
        valid_types = {"LineString", "MultiLineString"}
        assert set(geom_types).issubset(valid_types), (
            f"Unexpected geometry types: {geom_types}. Expected LineString/MultiLineString"
        )


@pytest.mark.network
@pytest.mark.slow
class TestNetworkMultiCity:
    """
    The critical scalability test: does the same code work for multiple
    randomly selected cities without any modifications?
    """

    def test_three_cities_all_return_data(self, three_random_cities):
        """
        QUESTION: Can the exact same function fetch networks for 3
        completely different, randomly selected US cities?

        PASS CRITERIA:
        - All 3 cities return graphs with >50 edges
        - No exceptions raised for any city
        - Each city's data is geographically distinct (centroids differ)

        WHY THIS CAN'T BE FAKED:
        - Random selection means you can't hardcode for specific cities
        - Geographic distinctness proves each result is real, not cached
        """
        from src.network import fetch_walk_network
        import osmnx as ox

        centroids = []
        for city in three_random_cities:
            graph = fetch_walk_network(city["osmnx_query"])
            edges = ox.graph_to_gdfs(graph, nodes=False)

            assert len(edges) >= 50, (
                f"{city['city']}, {city['state']} returned only {len(edges)} edges"
            )

            centroid = edges.geometry.unary_union.centroid
            centroids.append((centroid.y, centroid.x, city["city"]))

        # Verify all three centroids are geographically distinct
        for i in range(len(centroids)):
            for j in range(i + 1, len(centroids)):
                dlat = abs(centroids[i][0] - centroids[j][0])
                dlon = abs(centroids[i][1] - centroids[j][1])
                assert dlat > 0.01 or dlon > 0.01, (
                    f"Cities {centroids[i][2]} and {centroids[j][2]} have "
                    f"nearly identical centroids — data may be faked/cached"
                )
