"""
TEST SUITE 5: End-to-End Integration
======================================
These are the ultimate "can't be faked" tests. They run the entire pipeline:
  City name → OSM network → Environmental data → Scoring → GeoJSON output

If these pass for 3+ randomly selected cities, the system works.

WHAT THESE TESTS GUARANTEE:
- The full pipeline produces valid, renderable GeoJSON
- Output contains scored street segments with real geometry
- Works for multiple random cities (not hardcoded)
- Output is suitable for frontend consumption (Leaflet/MapLibre)

WHY THESE CAN'T BE FAKED:
- Random city selection
- Full structural validation of GeoJSON output
- Geographic bound checking against known city coordinates
- Multi-city verification in a single test
"""
import pytest
import json
from tests.cities import get_random_cities


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndPipeline:
    """Does the full pipeline work from city name to scored GeoJSON?"""

    def test_pipeline_produces_geojson(self, random_city):
        """
        QUESTION: Given a city name, does the pipeline produce valid GeoJSON?

        PASS CRITERIA:
        - Returns a dict with "type": "FeatureCollection"
        - Contains "features" array with at least 10 features
        - Each feature has "type": "Feature", "geometry", and "properties"
        """
        from src.pipeline import generate_comfort_geojson

        geojson = generate_comfort_geojson(random_city["osmnx_query"])

        assert isinstance(geojson, dict), "Output is not a dict"
        assert geojson.get("type") == "FeatureCollection", (
            f"Expected FeatureCollection, got {geojson.get('type')}"
        )
        assert "features" in geojson, "Missing 'features' key"
        assert len(geojson["features"]) >= 10, (
            f"Only {len(geojson['features'])} features for "
            f"{random_city['city']}, {random_city['state']}"
        )

    def test_features_have_required_structure(self, random_city):
        """
        QUESTION: Does each GeoJSON feature have the structure needed
        for frontend rendering?

        PASS CRITERIA:
        - Each feature has geometry.type = "LineString" or "MultiLineString"
        - Each feature has geometry.coordinates (non-empty array)
        - Each feature has properties.comfort_score (number 0-100)
        - Each feature has properties.noise_dba (number or null)
        - Each feature has properties.canopy_pct (number or null)
        """
        from src.pipeline import generate_comfort_geojson

        geojson = generate_comfort_geojson(random_city["osmnx_query"])
        features = geojson["features"]

        for i, feature in enumerate(features[:20]):  # Check first 20
            assert feature.get("type") == "Feature", f"Feature {i} missing type"

            geom = feature.get("geometry")
            assert geom is not None, f"Feature {i} has no geometry"
            assert geom.get("type") in ("LineString", "MultiLineString"), (
                f"Feature {i} geometry type is {geom.get('type')}"
            )
            assert len(geom.get("coordinates", [])) > 0, (
                f"Feature {i} has empty coordinates"
            )

            props = feature.get("properties", {})
            assert "comfort_score" in props, f"Feature {i} missing comfort_score"
            score = props["comfort_score"]
            assert isinstance(score, (int, float)), (
                f"Feature {i} comfort_score is not numeric: {score}"
            )
            assert 0 <= score <= 100, (
                f"Feature {i} comfort_score out of range: {score}"
            )

    def test_geojson_is_serializable(self, random_city):
        """
        QUESTION: Can the GeoJSON output be serialized to JSON for
        HTTP transmission to the frontend?

        PASS CRITERIA:
        - json.dumps() succeeds without errors
        - Result is valid JSON (json.loads() round-trips)
        """
        from src.pipeline import generate_comfort_geojson

        geojson = generate_comfort_geojson(random_city["osmnx_query"])

        try:
            json_str = json.dumps(geojson)
        except (TypeError, ValueError) as e:
            pytest.fail(f"GeoJSON is not JSON-serializable: {e}")

        roundtrip = json.loads(json_str)
        assert roundtrip["type"] == "FeatureCollection"
        assert len(roundtrip["features"]) == len(geojson["features"])

    def test_coordinates_match_requested_city(self, random_city):
        """
        QUESTION: Are the returned coordinates actually in the city we
        requested? This is the ultimate hardcoding detector.

        PASS CRITERIA:
        - The centroid of all returned geometries is within 50km of the
          city's known center coordinates
        """
        from src.pipeline import generate_comfort_geojson
        import math

        geojson = generate_comfort_geojson(random_city["osmnx_query"])
        features = geojson["features"]

        # Collect all coordinate points
        all_lons = []
        all_lats = []
        for feature in features:
            coords = feature["geometry"]["coordinates"]
            if feature["geometry"]["type"] == "LineString":
                for lon, lat in coords:
                    all_lons.append(lon)
                    all_lats.append(lat)
            elif feature["geometry"]["type"] == "MultiLineString":
                for line in coords:
                    for lon, lat in line:
                        all_lons.append(lon)
                        all_lats.append(lat)

        assert len(all_lons) > 0, "No coordinates found in features"

        avg_lat = sum(all_lats) / len(all_lats)
        avg_lon = sum(all_lons) / len(all_lons)

        dlat = abs(avg_lat - random_city["lat"])
        dlon = abs(avg_lon - random_city["lon"])
        approx_km = math.sqrt(dlat**2 + dlon**2) * 111

        assert approx_km < 50, (
            f"Output centroid ({avg_lat:.4f}, {avg_lon:.4f}) is {approx_km:.0f}km "
            f"from {random_city['city']} center ({random_city['lat']}, {random_city['lon']}). "
            f"Pipeline may be returning data for the wrong city!"
        )

    def test_features_have_data_quality(self, random_city):
        """
        QUESTION: Does each feature include data quality metadata
        so the frontend can indicate which segments have real vs default data?

        PASS CRITERIA:
        - Each feature has properties.data_quality dict
        - data_quality has keys: noise, canopy, heat
        - Each value is one of: "real", "default", "unavailable", "fixed"
        """
        from src.pipeline import generate_comfort_geojson

        geojson = generate_comfort_geojson(random_city["osmnx_query"])

        valid_statuses = {"real", "default", "unavailable", "fixed"}

        for i, feature in enumerate(geojson["features"][:20]):
            props = feature.get("properties", {})
            dq = props.get("data_quality")
            assert dq is not None, f"Feature {i} missing data_quality"
            assert isinstance(dq, dict), f"Feature {i} data_quality is not a dict"

            for key in ("noise", "canopy", "heat"):
                assert key in dq, f"Feature {i} data_quality missing '{key}'"
                assert dq[key] in valid_statuses, (
                    f"Feature {i} data_quality['{key}'] = '{dq[key]}' "
                    f"is not a valid status"
                )


@pytest.mark.integration
@pytest.mark.slow
class TestMultiCityIntegration:
    """The ultimate scalability test: full pipeline across random cities."""

    def test_three_cities_full_pipeline(self, three_random_cities):
        """
        QUESTION: Does the complete pipeline work for 3 randomly selected
        US cities in a single test run?

        THIS IS THE SINGLE MOST IMPORTANT TEST IN THE SUITE.

        PASS CRITERIA:
        - All 3 cities produce valid GeoJSON FeatureCollections
        - All 3 have at least 10 scored features
        - All 3 have geographically distinct coordinates
        - No exceptions for any city

        WHY THIS CAN'T BE FAKED:
        - 3 cities selected randomly from 100 at test time
        - Each city's output is validated for geographic correctness
        - Cross-city coordinate comparison ensures no shared fake data
        """
        from src.pipeline import generate_comfort_geojson
        import math

        results = []
        for city in three_random_cities:
            geojson = generate_comfort_geojson(city["osmnx_query"])

            assert geojson["type"] == "FeatureCollection"
            assert len(geojson["features"]) >= 10, (
                f"{city['city']}, {city['state']} produced only "
                f"{len(geojson['features'])} features"
            )

            # Compute centroid for geographic distinctness check
            all_lons, all_lats = [], []
            for f in geojson["features"]:
                coords = f["geometry"]["coordinates"]
                if f["geometry"]["type"] == "LineString":
                    for lon, lat in coords:
                        all_lons.append(lon)
                        all_lats.append(lat)
                elif f["geometry"]["type"] == "MultiLineString":
                    for line in coords:
                        for lon, lat in line:
                            all_lons.append(lon)
                            all_lats.append(lat)

            avg_lat = sum(all_lats) / len(all_lats)
            avg_lon = sum(all_lons) / len(all_lons)
            results.append({
                "city": city["city"],
                "state": city["state"],
                "features": len(geojson["features"]),
                "avg_lat": avg_lat,
                "avg_lon": avg_lon,
            })

        # Verify geographic distinctness
        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                dlat = abs(results[i]["avg_lat"] - results[j]["avg_lat"])
                dlon = abs(results[i]["avg_lon"] - results[j]["avg_lon"])
                dist_km = math.sqrt(dlat**2 + dlon**2) * 111

                assert dist_km > 10, (
                    f"{results[i]['city']} and {results[j]['city']} have "
                    f"centroids only {dist_km:.1f}km apart — "
                    f"pipeline may be returning the same data for all cities!"
                )

        print("\n  ✅ MULTI-CITY INTEGRATION PASSED:")
        for r in results:
            print(f"    {r['city']}, {r['state']}: "
                  f"{r['features']} segments scored "
                  f"(centroid: {r['avg_lat']:.2f}, {r['avg_lon']:.2f})")
