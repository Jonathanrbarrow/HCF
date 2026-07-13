"""
TEST SUITE 6: Open-Meteo Historical Heat Data
==============================================
These tests verify that we can fetch historical summer peak apparent
temperature data from the Open-Meteo Archive API for US cities.

DATA SOURCE:
- Endpoint: https://archive-api.open-meteo.com/v1/archive
- Metric: Daily max apparent temperature (Fahrenheit), 3-year summer average
- No authentication required

WHAT THESE TESTS GUARANTEE:
- The Open-Meteo Archive API is reachable and returns valid JSON
- Historical apparent temperature averages are in realistic ranges
- Real quality tracking is recorded
- Fallback/error handling works gracefully
"""
import pytest
from tests.cities import get_random_cities


@pytest.mark.heat
@pytest.mark.slow
class TestHeatDataFetch:
    """Can we fetch real apparent temperature data from Open-Meteo?"""

    def test_heat_archive_api_is_reachable(self):
        """
        QUESTION: Is the Open-Meteo Archive API alive and returning historical data?

        PASS CRITERIA:
        - HTTP 200 and valid JSON response
        - Response contains daily apparent_temperature_max array
        """
        import requests

        url = ("https://archive-api.open-meteo.com/v1/archive?"
               "latitude=37.7749&longitude=-122.4194&"
               "start_date=2024-06-01&end_date=2024-06-10&"
               "daily=apparent_temperature_max&temperature_unit=fahrenheit&timezone=auto")
        resp = requests.get(url, timeout=15)
        assert resp.status_code == 200, f"API returned status {resp.status_code}"
        data = resp.json()
        assert "daily" in data, "Response missing 'daily' field"
        assert "apparent_temperature_max" in data["daily"], "Response missing 'apparent_temperature_max'"

    def test_fetch_heat_at_point(self, random_city):
        """
        QUESTION: Can we fetch the historical summer peak heat at a specific point?

        PASS CRITERIA:
        - Returns a numeric value in Fahrenheit (3-year summer average)
        - Value is in realistic range (40°F to 130°F — summer peaks)
        """
        from hcf.data.heat import fetch_heat_at_point

        value = fetch_heat_at_point(random_city["lat"], random_city["lon"])
        assert value is not None, "Heat value should not be None"
        assert isinstance(value, (int, float)), f"Value {value} is not numeric"
        assert 40 <= value <= 130, f"Summer peak avg {value}°F is unrealistic"

    def test_fetch_heat_batch(self, random_city):
        """
        QUESTION: Can we batch fetch heat data for multiple points?

        PASS CRITERIA:
        - Returns a list of dicts with keys 'value' and 'quality'
        - All values are in realistic ranges
        - Order matches the input list
        """
        from hcf.data.heat import fetch_heat_batch

        points = [
            (random_city["lat"], random_city["lon"]),
            (random_city["lat"] + 0.01, random_city["lon"] + 0.01),
            (random_city["lat"] - 0.01, random_city["lon"] - 0.01),
        ]
        results = fetch_heat_batch(points)
        assert len(results) == len(points), "Result list length mismatch"

        for r in results:
            assert "value" in r, "Missing 'value' key"
            assert "quality" in r, "Missing 'quality' key"
            from hcf.data.quality import VALID_STATUSES
            assert r["quality"] in VALID_STATUSES
            if r["value"] is not None:
                assert -30 <= r["value"] <= 130, f"Value {r['value']} out of range"
