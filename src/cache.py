"""
Cache module — file-based caching with TTL for network graphs and results.

Storage:
  - .cache/ directory in the project root
  - Pickle for graph objects (24h TTL)
  - JSON for scored GeoJSON results (1h TTL)

Thread safety via atomic temp-file renames.
"""
import hashlib
import json
import pickle
import tempfile
import time
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
TTL_NETWORK = 24 * 3600  # 24 hours
TTL_RESULT = 1 * 3600    # 1 hour


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cache_key(city_query: str, **params) -> str:
    """Build a deterministic cache key from a query string and optional params."""
    raw = city_query + json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _path_for(key: str, ext: str) -> Path:
    return CACHE_DIR / f"{key}.{ext}"


def _is_fresh(path: Path, ttl_seconds: int) -> bool:
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < ttl_seconds


def _atomic_write(path: Path, data: bytes) -> None:
    """Write data atomically by writing to a temp file then renaming."""
    _ensure_cache_dir()
    fd, tmp = tempfile.mkstemp(dir=CACHE_DIR)
    try:
        with open(fd, "wb") as f:
            f.write(data)
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# --- Generic API ---

def get_cached(key: str, ttl_seconds: int) -> object | None:
    """Return cached value (tries pickle then JSON) or None if stale/missing."""
    for ext, loader in [("pkl", pickle.loads), ("json", lambda b: json.loads(b))]:
        path = _path_for(key, ext)
        if _is_fresh(path, ttl_seconds):
            return loader(path.read_bytes())
    return None


def set_cached(key: str, value, fmt: str = "pkl") -> None:
    """Store a value in the cache. fmt: 'pkl' for pickle, 'json' for JSON."""
    if fmt == "json":
        data = json.dumps(value, default=str).encode()
    else:
        data = pickle.dumps(value)
    _atomic_write(_path_for(key, fmt), data)


# --- Network cache (pickle, 24h) ---

def get_network_cache(city_query: str):
    """Return cached network graph or None."""
    return get_cached(cache_key(city_query, _type="network"), TTL_NETWORK)


def set_network_cache(city_query: str, graph) -> None:
    """Cache a network graph."""
    set_cached(cache_key(city_query, _type="network"), graph, fmt="pkl")


# --- Result cache (JSON, 1h) ---

def get_result_cache(city_query: str, max_segments: int) -> dict | None:
    """Return cached scored GeoJSON result or None."""
    key = cache_key(city_query, _type="result", max_segments=max_segments)
    return get_cached(key, TTL_RESULT)


def set_result_cache(city_query: str, max_segments: int, geojson: dict) -> None:
    """Cache a scored GeoJSON result."""
    key = cache_key(city_query, _type="result", max_segments=max_segments)
    set_cached(key, geojson, fmt="json")
