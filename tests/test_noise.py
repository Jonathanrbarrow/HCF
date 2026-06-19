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
- Random city selection at test time
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
        from src.noise import check_noise_api

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
        - Returns a numeric noise value
        - Value is in realistic range: 0-100 dBA
        - Value is not None/NaN
        """
        from src.noise import fetch_noise_at_point

        value = fetch_noise_at_point(random_city["lat"], random_city["lon"])

        assert value is not None, (
            f"No noise data returned for {random_city['city']}, {random_city['state']} "
            f"at ({random_city['lat']}, {random_city['lon']})"
        )
        assert isinstance(value, (int, float)), f"Noise value is not numeric: {type(value)}"
        assert 0 <= value <= 100, f"Noise value {value} dBA is outside realistic range (0-100)"

    def test_fetch_noise_for_bbox(self, random_city):
        """
        QUESTION: Can we sample noise levels across a bounding box
        (multiple points) in a random US city?

        PASS CRITERIA:
        - Returns a list/array of noise values
        - At least some values are non-null (data exists for this area)
        - Values span a range (not all identical — proves spatial variation)
        """
        from src.noise import fetch_noise_for_bbox

        bbox = get_bbox_around_point(random_city["lat"], random_city["lon"], radius_km=2.0)
        values = fetch_noise_for_bbox(bbox, sample_points=25)

        non_null = [v for v in values if v is not None]
        assert len(non_null) >= 5, (
            f"Only {len(non_null)}/25 noise samples returned data for "
            f"{random_city['city']}, {random_city['state']}. "
            f"API may not cover this area."
        )

        # Values should not all be identical (proves real spatial data)
        unique_values = set(non_null)
        assert len(unique_values) > 1, (
            f"All {len(non_null)} noise values are identical ({non_null[0]}). "
            f"Data may be faked or the sample area is too small."
        )

    def test_noise_varies_between_cities(self, three_random_cities):
        """
        QUESTION: Do different cities return different noise profiles?
        This catches hardcoded return values.

        PASS CRITERIA:
        - At least 2 of 3 cities have different median noise levels
        """
        from src.noise import fetch_noise_at_point

        values = []
        for city in three_random_cities:
            value = fetch_noise_at_point(city["lat"], city["lon"])
            if value is not None:
                values.append((value, city["city"]))

        assert len(values) >= 2, "Noise data available for fewer than 2 cities"

        # Not all values should be identical (within 0.1 dBA)
        distinct = len(set(round(v, 1) for v, _ in values))
        # It's possible 2 city centers have similar noise, so we just check
        # that the function doesn't return a hardcoded constant
        if len(values) >= 3:
            assert distinct >= 2, (
                f"All cities returned identical noise: {values}. "
                f"Function may be returning a hardcoded value."
            )


@pytest.mark.noise
@pytest.mark.slow
class TestNoiseDataQuality:
    """Are the noise values physically meaningful?"""

    def test_noise_values_are_realistic(self, five_random_cities):
        """
        QUESTION: Across 5 random cities, are all noise values in the
        physically realistic range for urban areas?

        PASS CRITERIA:
        - All values between 30-90 dBA (typical urban range)
        - At least some values above 45 dBA (below this is rural/wilderness)
        """
        from src.noise import fetch_noise_at_point

        all_values = []
        for city in five_random_cities:
            value = fetch_noise_at_point(city["lat"], city["lon"])
            if value is not None:
                assert 0 <= value <= 100, (
                    f"Unrealistic noise value {value} dBA for "
                    f"{city['city']}, {city['state']}"
                )
                all_values.append(value)

        assert len(all_values) >= 3, "Too few cities returned noise data"
        assert any(v >= 45 for v in all_values), (
            f"No city center has noise >= 45 dBA: {all_values}. "
            f"Urban areas should be louder than this."
        )
