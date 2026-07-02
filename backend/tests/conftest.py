"""
Shared pytest fixtures for HCF tests.

Key design principle: Tests randomly select cities from the top 100 US cities
to prevent any hardcoding for a single location. The random seed is logged so
failures can be reproduced.
"""
import pytest
import random
import time
from .cities import TOP_100_US_CITIES, get_random_cities, get_bbox_around_point


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "network: tests that fetch OSM pedestrian network data")
    config.addinivalue_line("markers", "noise: tests that fetch DOT noise map data")
    config.addinivalue_line("markers", "canopy: tests that fetch NLCD tree canopy data")
    config.addinivalue_line("markers", "scoring: tests for the comfort scoring engine")
    config.addinivalue_line("markers", "integration: end-to-end pipeline tests")
    config.addinivalue_line("markers", "slow: tests that may take >30s due to API calls")


@pytest.fixture(scope="session")
def random_seed():
    """Generate and log a random seed for the test session so failures are reproducible."""
    seed = int(time.time())
    print(f"\n{'='*60}")
    print(f"  TEST SESSION RANDOM SEED: {seed}")
    print(f"  Re-run with this seed to reproduce: --random-seed={seed}")
    print(f"{'='*60}\n")
    return seed


@pytest.fixture
def random_city(random_seed):
    """Pick one random city from the top 100. Different for each test function."""
    city = get_random_cities(n=1, seed=random_seed + id(random_city))[0]
    print(f"  [Random City] {city['city']}, {city['state']}")
    return city


@pytest.fixture
def three_random_cities(random_seed):
    """Pick 3 random cities from different regions of the top 100."""
    cities = get_random_cities(n=3, seed=random_seed)
    names = [f"{c['city']}, {c['state']}" for c in cities]
    print(f"  [Random Cities] {', '.join(names)}")
    return cities


@pytest.fixture
def five_random_cities(random_seed):
    """Pick 5 random cities for broader cross-city validation."""
    cities = get_random_cities(n=5, seed=random_seed)
    names = [f"{c['city']}, {c['state']}" for c in cities]
    print(f"  [Random Cities] {', '.join(names)}")
    return cities


@pytest.fixture
def city_bbox(random_city):
    """Return a 2km-radius bounding box around a random city center."""
    bbox = get_bbox_around_point(random_city["lat"], random_city["lon"], radius_km=2.0)
    return bbox


@pytest.fixture
def small_city_bbox(random_city):
    """Return a small (500m radius) bounding box for quick API tests."""
    bbox = get_bbox_around_point(random_city["lat"], random_city["lon"], radius_km=0.5)
    return bbox
