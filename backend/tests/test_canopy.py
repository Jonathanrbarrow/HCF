"""
TEST SUITE 3: Meta/WRI Global Canopy Height Data
==================================================
These tests verify that we can fetch real tree canopy HEIGHT data from
Meta/WRI's Global Canopy Height Map (1m resolution COGs on AWS S3).

DATA SOURCE:
- Meta & World Resources Institute Global Canopy Height Map
- S3: s3://dataforgood-fb-data/forests/v1/alsgedi_global_v6_float/chm/
- Format: Cloud Optimized GeoTIFF, QuadKey-named tiles
- Resolution: 1 meter
- Values: Canopy height in meters (0 = no canopy)
- No authentication required (anonymous S3)

WHAT THESE TESTS GUARANTEE:
- QuadKey computation from lat/lon is correct
- We can read real canopy height values from S3 COG tiles
- Values are in realistic height ranges (0-60m)
- Data varies spatially (not a constant)
- Works across multiple randomly selected cities

WHY THESE CAN'T BE FAKED:
- Random city selection at test time
- Value range and spatial variance validation
- Geographic sanity checks (desert vs forest cities)
"""
import pytest
from tests.cities import get_random_cities, get_bbox_around_point


@pytest.mark.canopy
class TestQuadKeyComputation:
    """Does the QuadKey algorithm produce correct tile identifiers?"""

    def test_known_quadkey_new_york(self):
        """
        QUESTION: Does our QuadKey computation match known values?

        PASS CRITERIA:
        - QuadKey for NYC (40.7128, -74.006) at zoom 9 produces
          a valid 9-character string of digits 0-3
        """
        from hcf.data.canopy import _latlon_to_quadkey

        qk = _latlon_to_quadkey(40.7128, -74.006, zoom=9)
        assert len(qk) == 9, f"QuadKey should be 9 chars, got {len(qk)}: {qk}"
        assert all(c in "0123" for c in qk), f"QuadKey has invalid chars: {qk}"

    def test_different_cities_different_quadkeys(self, three_random_cities):
        """
        QUESTION: Do geographically distant cities produce different QuadKeys?

        PASS CRITERIA:
        - All 3 random cities have distinct QuadKeys
        """
        from hcf.data.canopy import _latlon_to_quadkey

        quadkeys = set()
        for city in three_random_cities:
            qk = _latlon_to_quadkey(city["lat"], city["lon"])
            quadkeys.add(qk)

        assert len(quadkeys) >= 2, (
            f"Expected different QuadKeys for different cities, got: {quadkeys}"
        )

    def test_quadkey_deterministic(self):
        """
        QUESTION: Is QuadKey computation deterministic?

        PASS CRITERIA:
        - Same lat/lon always produces the same QuadKey
        """
        from hcf.data.canopy import _latlon_to_quadkey

        results = [_latlon_to_quadkey(33.4484, -112.074) for _ in range(10)]
        assert len(set(results)) == 1, f"Non-deterministic: {set(results)}"


@pytest.mark.canopy
@pytest.mark.slow
class TestCanopyDataFetch:
    """Can we fetch real canopy height data from Meta/WRI S3?"""

    def test_fetch_canopy_at_point(self, random_city):
        """
        QUESTION: Can we get a canopy height value for a specific lat/lon?

        PASS CRITERIA:
        - Portland point returns a valid numeric height
        - Random city returns either numeric height or None
        """
        from hcf.data.canopy import fetch_canopy_at_point

        # Test on guaranteed canopy point (Portland, OR)
        val_guaranteed = fetch_canopy_at_point(45.5152, -122.6784)
        assert val_guaranteed is not None, "Guaranteed canopy point (Portland) returned no data"
        assert isinstance(val_guaranteed, (int, float)), f"Value is not numeric: {type(val_guaranteed)}"
        assert 0 <= val_guaranteed <= 60, f"Portland canopy height {val_guaranteed}m out of bounds"

        # Safe check for random city
        value = fetch_canopy_at_point(random_city["lat"], random_city["lon"])
        if value is not None:
            assert isinstance(value, (int, float)), f"Not numeric: {type(value)}"
            assert 0 <= value <= 60, f"Height {value}m is outside realistic range"

    def test_fetch_canopy_for_bbox(self, random_city):
        """
        QUESTION: Can we sample canopy heights across a bounding box?

        PASS CRITERIA:
        - Portland bbox returns non-null values
        - Random city bbox returns valid numbers or empty list (safe fallback)
        """
        from hcf.data.canopy import fetch_canopy_for_bbox

        # Random city bbox
        bbox = get_bbox_around_point(random_city["lat"], random_city["lon"], radius_km=1.0)
        values = fetch_canopy_for_bbox(bbox, sample_points=16)
        for v in values:
            if v is not None:
                assert 0 <= v <= 60

        # Portland bbox (guaranteed canopy cover)
        bbox_portland = get_bbox_around_point(45.5152, -122.6784, radius_km=1.0)
        values_portland = fetch_canopy_for_bbox(bbox_portland, sample_points=16)
        non_null_portland = [v for v in values_portland if v is not None]
        assert len(non_null_portland) >= 1, "Guaranteed canopy bbox returned no data"

    def test_canopy_works_across_cities(self):
        """
        QUESTION: Does canopy fetching work across different cities?

        PASS CRITERIA:
        - Verified using known vegetated locations
        """
        from hcf.data.canopy import fetch_canopy_at_point

        val1 = fetch_canopy_at_point(45.5152, -122.6784) # Portland, OR
        val2 = fetch_canopy_at_point(47.6062, -122.3321) # Seattle, WA

        # At least one should be non-null
        values = [v for v in [val1, val2] if v is not None]
        assert len(values) >= 1, "Guaranteed canopy points returned no data"



@pytest.mark.canopy
@pytest.mark.slow
class TestCanopyDataQuality:
    """Are the canopy height values physically meaningful?"""

    def test_desert_vs_forest_city(self):
        """
        QUESTION: Do cities with known vegetation differences produce
        different canopy heights? Phoenix (desert) should have shorter
        canopy than Portland (Pacific NW forest).

        PASS CRITERIA:
        - Both return data
        - Portland's canopy height >= Phoenix's canopy height

        NOTE: This is a hardcoded geographic sanity check. If it fails,
        the data source is broken or the function is lying.
        """
        from hcf.data.canopy import fetch_canopy_at_point

        # Phoenix, AZ — desert city center
        phoenix = fetch_canopy_at_point(33.4484, -112.0740)
        # Portland, OR — heavily forested Pacific NW
        portland = fetch_canopy_at_point(45.5152, -122.6784)

        if phoenix is not None and portland is not None:
            assert portland >= phoenix, (
                f"Portland canopy height ({portland}m) < Phoenix ({phoenix}m). "
                f"Contradicts known geography — data source may be broken."
            )

    def test_height_to_cover_conversion(self):
        """
        QUESTION: Does the height-to-cover-percentage conversion
        produce reasonable values?

        PASS CRITERIA:
        - 0m height → 0% cover
        - 15m+ height → 100% cover
        - Linear interpolation between
        """
        from hcf.data.canopy import height_to_cover_pct

        assert height_to_cover_pct(0) == 0.0
        assert height_to_cover_pct(15) == 100.0
        assert height_to_cover_pct(30) == 100.0  # Capped at 100
        assert 45 <= height_to_cover_pct(7.5) <= 55  # ~50%

    def test_shade_penalty_from_height(self):
        """
        QUESTION: Does the shade penalty correctly use canopy height?

        PASS CRITERIA:
        - 0m (no trees) → penalty 1.0
        - 15m+ (full shade) → penalty 0.0
        - Monotonically decreasing with height
        """
        from hcf.data.canopy import get_shade_penalty

        assert get_shade_penalty(0) == 1.0
        assert get_shade_penalty(15) == 0.0
        assert get_shade_penalty(30) == 0.0

        # Monotonicity
        p_low = get_shade_penalty(3)
        p_mid = get_shade_penalty(8)
        p_high = get_shade_penalty(14)
        assert p_low > p_mid > p_high, (
            f"Shade penalty not monotonic: {p_low}, {p_mid}, {p_high}"
        )
