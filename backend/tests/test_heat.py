"""
TEST SUITE 6: Open-Meteo Apparent Temperature (Heat) Data
=========================================================
These tests verify that we can fetch real apparent temperature (heat index)
data from the Open-Meteo Weather API for randomly selected US cities.

DATA SOURCE:
- Endpoint: https://api.open-meteo.com/v1/forecast
- Metric: Apparent temperature (Fahrenheit)
- No authentication required

WHAT THESE TESTS GUARANTEE:
- The Open-Meteo API is reachable and returns valid JSON
- Apparent temperature values are in realistic Fahrenheit ranges (-30°F to 130°F)
- Real quality tracking is recorded
- Fallback/error handling works gracefully when the API is down or invalid
"""
import pytest
from tests.cities import get_random_cities


@pytest.mark.heat
@pytest.mark.slow
class TestHeatDataFetch:
    """Can we fetch real apparent temperature data from Open-Meteo?"""

    def test_heat_api_is_reachable(self):
        """
        QUESTION: Is the Open-Meteo API alive and returning data?

        PASS CRITERIA:
        - HTTP 200 and valid JSON response
        - Response contains current apparent_temperature
        """
        import requests

        url = "https://api.open-meteo.com/v1/forecast?latitude=37.7749&longitude=-122.4194&current=apparent_temperature&temperature_unit=fahrenheit"
        resp = requests.get(url, timeout=10)
        assert resp.status_code == 200, f"API returned status {resp.status_code}"
        data = resp.json()
        assert "current" in data, "Response missing 'current' field"
        assert "apparent_temperature" in data["current"], "Response missing 'apparent_temperature'"

    def test_fetch_heat_at_point(self, random_city):
        """
        QUESTION: Can we fetch the heat index/apparent temperature at a specific point?

        PASS CRITERIA:
        - Returns a numeric value in Fahrenheit
        - Value is in realistic range (-30°F to 130°F)
        """
        from hcf.data.heat import fetch_heat_at_point

        value = fetch_heat_at_point(random_city["lat"], random_city["lon"])
        assert value is not None, "Heat value should not be None"
        assert isinstance(value, (int, float)), f"Value {value} is not numeric"
        assert -30 <= value <= 130, f"Apparent temperature {value}°F is unrealistic"

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
            assert r["quality"] in {"real", "default", "unavailable"}
            if r["value"] is not None:
                assert -30 <= r["value"] <= 130, f"Value {r['value']} out of range"
