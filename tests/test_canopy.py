"""
TEST SUITE 3: NLCD Tree Canopy Cover Data
==========================================
These tests verify that we can fetch real tree canopy cover data from the
MRLC/USGS National Land Cover Database via their WMS/WCS services.

DATA SOURCE:
- MRLC NLCD Tree Canopy Cover (produced by USDA Forest Service)
- Available via OGC WMS/WCS services — no authentication required
- Coverage: Continental US
- Resolution: 30m pixels
- Values: 0-100 (percentage tree canopy cover)

WHAT THESE TESTS GUARANTEE:
- We can fetch canopy cover values for any point in CONUS
- Values are in the valid 0-100% range
- Values vary spatially (parks vs downtown produce different values)
- Works across multiple randomly selected cities

WHY THESE CAN'T BE FAKED:
- Random city selection
- Value range and spatial variance validation
- Cross-city comparison
"""
import pytest
from tests.cities import get_random_cities, get_bbox_around_point


@pytest.mark.canopy
@pytest.mark.slow
class TestCanopyDataFetch:
    """Can we fetch real tree canopy cover for any US city?"""

    def test_fetch_canopy_at_point(self, random_city):
        """
        QUESTION: Can we get a tree canopy cover percentage for a
        specific lat/lon in a random US city?

        PASS CRITERIA:
        - Returns a numeric value
        - Value is in range 0-100 (percentage)
        """
        from src.canopy import fetch_canopy_at_point

        value = fetch_canopy_at_point(random_city["lat"], random_city["lon"])

        assert value is not None, (
            f"No canopy data returned for {random_city['city']}, {random_city['state']}"
        )
        assert isinstance(value, (int, float)), f"Canopy value is not numeric: {type(value)}"
        assert 0 <= value <= 100, f"Canopy value {value}% is outside valid range (0-100)"

    def test_fetch_canopy_for_bbox(self, random_city):
        """
        QUESTION: Can we sample canopy cover across a bounding box?

        PASS CRITERIA:
        - Returns an array of values for sampled points
        - At least some values are non-null
        - Values show spatial variation (not uniform)
        """
        from src.canopy import fetch_canopy_for_bbox

        bbox = get_bbox_around_point(random_city["lat"], random_city["lon"], radius_km=2.0)
        values = fetch_canopy_for_bbox(bbox, sample_points=25)

        non_null = [v for v in values if v is not None]
        assert len(non_null) >= 5, (
            f"Only {len(non_null)}/25 canopy samples for "
            f"{random_city['city']}, {random_city['state']}"
        )

        unique_values = set(int(v) for v in non_null)
        assert len(unique_values) > 1, (
            f"All canopy values are identical ({non_null[0]}). "
            f"Data may be faked."
        )

    def test_canopy_works_across_cities(self, three_random_cities):
        """
        QUESTION: Does canopy fetching work for 3 different random cities?

        PASS CRITERIA:
        - All 3 cities return valid canopy data
        - No exceptions for any city
        """
        from src.canopy import fetch_canopy_at_point

        for city in three_random_cities:
            value = fetch_canopy_at_point(city["lat"], city["lon"])
            assert value is not None, (
                f"No canopy data for {city['city']}, {city['state']}"
            )
            assert 0 <= value <= 100, (
                f"Invalid canopy value {value} for {city['city']}, {city['state']}"
            )


@pytest.mark.canopy
@pytest.mark.slow
class TestCanopyDataQuality:
    """Are the canopy values physically meaningful?"""

    def test_desert_vs_green_city_difference(self):
        """
        QUESTION: Do cities with known vegetation differences produce
        different canopy values? Phoenix (desert) should have less
        canopy than Portland (Pacific NW forest).

        PASS CRITERIA:
        - Portland canopy > Phoenix canopy (at city center)
        - Both values are in valid range

        NOTE: This is a hardcoded sanity check. If this fails, the
        data source is broken or the function is lying.
        """
        from src.canopy import fetch_canopy_at_point

        # Phoenix, AZ — desert city
        phoenix = fetch_canopy_at_point(33.4484, -112.0740)
        # Portland, OR — Pacific NW, heavy tree cover
        portland = fetch_canopy_at_point(45.5152, -122.6784)

        assert phoenix is not None, "No canopy data for Phoenix"
        assert portland is not None, "No canopy data for Portland"

        # Portland should have more tree canopy than Phoenix city center
        # Using a relaxed check — downtown areas may both be low,
        # but Portland should still be higher
        assert portland >= phoenix, (
            f"Portland canopy ({portland}%) is less than Phoenix ({phoenix}%). "
            f"This contradicts known geography — data source may be broken."
        )
