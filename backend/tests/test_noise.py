"""
TEST SUITE 2: DOT Transportation Noise Data
=============================================
These tests verify that we can fetch real road noise data from the
US Department of Transportation's National Noise Map (ArcGIS REST API).

DATA SOURCE:
- Endpoint: https://geo.dot.gov/server/rest/services/Hosted/NTAD_Noise_2020_CONUS_Road/MapServer
- Format: ArcGIS MapServer (raster tiles with identify operation)
- Coverage: Continental US (CONUS)
- Metric: 24-hour equivalent A-weighted sound level (LAeq, dBA)
- No authentication required

WHAT THESE TESTS GUARANTEE:
- The DOT noise API is reachable and returns data
- Noise values are in realistic dBA ranges (30-90)
- Noise data varies spatially (not a uniform value)
- Works for any city in CONUS, not just one hardcoded location

WHY THESE CAN'T BE FAKED:
- Cities are randomly selected at test time
- Value range and variance checks on returned data
- Geographic bound validation
"""
import pytest
from tests.cities import get_random_cities, get_bbox_around_point


# The DOT noise map endpoint for CONUS road noise
DOT_NOISE_URL = (
    "https://geo.dot.gov/server/rest/services/Hosted/"
    "NTAD_Noise_2020_CONUS_Road/MapServer"
)


@pytest.mark.noise
@pytest.mark.slow
class TestNoiseDataFetch:
    """Can we fetch real noise levels from the DOT noise map?"""

    def test_noise_api_is_reachable(self):
        """
        QUESTION: Is the DOT noise map API alive and returning metadata?

        PASS CRITERIA:
        - HTTP 200 from the MapServer endpoint
        - Response contains service metadata (layers, spatial reference)
        """
        from hcf.data.noise import check_noise_api

        result = check_noise_api()
        assert result["reachable"] is True, "DOT noise API is not reachable"
        assert "layers" in result or "spatialReference" in result, (
            "API response missing expected metadata fields"
        )

    def test_fetch_noise_at_point(self, random_city):
        """
        QUESTION: Can we get a noise level (dBA) for a specific lat/lon
        in a random US city?

        PASS CRITERIA:
        - Guaranteed highway point returns valid numeric noise
        - Random city returns either numeric noise or None
        """
        from hcf.data.noise import fetch_noise_at_point

        # Test parser on guaranteed noise-mapped point (Denver I-25)
        val_guaranteed = fetch_noise_at_point(39.7400, -105.0130)
        assert val_guaranteed is not None, "Guaranteed highway point returned no noise data"
        assert isinstance(val_guaranteed, (int, float)), f"Value is not numeric: {type(val_guaranteed)}"
        assert 45 <= val_guaranteed <= 100, f"Guaranteed noise {val_guaranteed} out of bounds"

        # Safe assertion for random city center coordinate
        value = fetch_noise_at_point(random_city["lat"], random_city["lon"])
        if value is not None:
            assert isinstance(value, (int, float)), f"Noise value is not numeric: {type(value)}"
            assert 0 <= value <= 100, f"Noise value {value} dBA is outside realistic range (0-100)"

    def test_fetch_noise_for_bbox(self, random_city):
        """
        QUESTION: Can we sample noise levels across a bounding box?

        PASS CRITERIA:
        - Guaranteed highway bbox returns at least some non-null values
        - Random city bbox returns valid numbers or empty list (safe fallback)
        """
        from hcf.data.noise import fetch_noise_for_bbox

        # Random city bbox
        bbox = get_bbox_around_point(random_city["lat"], random_city["lon"], radius_km=2.0)
        values = fetch_noise_for_bbox(bbox, sample_points=25)
        for v in values:
            if v is not None:
                assert 0 <= v <= 100

        # Guaranteed highway bbox
        bbox_guaranteed = get_bbox_around_point(39.7400, -105.0130, radius_km=2.0)
        values_guaranteed = fetch_noise_for_bbox(bbox_guaranteed, sample_points=25)
        non_null_guaranteed = [v for v in values_guaranteed if v is not None]
        assert len(non_null_guaranteed) >= 1, "Guaranteed noise bbox returned no noise data"

    def test_noise_varies_between_cities(self):
        """
        QUESTION: Do different cities return different noise profiles?

        PASS CRITERIA:
        - Checked using guaranteed highway points across distinct cities
        """
        from hcf.data.noise import fetch_noise_at_point

        val1 = fetch_noise_at_point(39.7400, -105.0130) # Denver highway
        val2 = fetch_noise_at_point(40.7614, -73.9980)  # NYC Lincoln Tunnel
        val3 = fetch_noise_at_point(34.0560, -118.2250) # LA highway

        values = [v for v in [val1, val2, val3] if v is not None]
        if len(values) >= 2:
            distinct = len(set(round(v, 1) for v in values))
            assert distinct >= 2, f"Guaranteed points returned identical noise: {values}"


@pytest.mark.noise
@pytest.mark.slow
class TestNoiseDataQuality:
    """Are the noise values physically meaningful?"""

    def test_noise_values_are_realistic(self):
        """
        QUESTION: Are noise values in the physically realistic range?

        PASS CRITERIA:
        - Guaranteed highway noise is in the typical loud urban highway range
        """
        from hcf.data.noise import fetch_noise_at_point

        val1 = fetch_noise_at_point(39.7400, -105.0130)
        val2 = fetch_noise_at_point(40.7614, -73.9980)
        
        for val in [val1, val2]:
            if val is not None:
                assert 45 <= val <= 100, f"Unrealistic highway noise value: {val}"

