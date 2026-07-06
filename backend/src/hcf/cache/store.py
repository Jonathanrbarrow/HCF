"""
Cache module — file-based caching with TTL for network graphs and results.

Storage:
  - Directory configurable via HCF_CACHE_DIR (default: .cache)
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

from hcf.config import settings

CACHE_DIR = Path(settings.cache_dir).resolve()
TTL_NETWORK = settings.cache_ttl_network
TTL_RESULT = settings.cache_ttl_result


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
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


# --- Generic API ---

def get_cached(key: str, ttl_seconds: int) -> object | None:
    """Return cached value (tries pickle then JSON) or None if stale/missing."""
    for ext, loader in [("pkl", pickle.loads), ("json", lambda b: json.loads(b))]:
        path = _path_for(key, ext)
        if _is_fresh(path, ttl_seconds):
            # SECURITY: pickle.loads can execute arbitrary code.
            # Ensure the cache directory is trusted and not world-writable.
            return loader(path.read_bytes())
    return None


def set_cached(key: str, value, fmt: str = "pkl") -> None:
    """Store a value in the cache. fmt: 'pkl' for pickle, 'json' for JSON."""
    if fmt == "json":
        data = json.dumps(value, default=str).encode()
    else:
        data = pickle.dumps(value)
    _atomic_write(_path_for(key, fmt), data)
    # Probabilistic cache cleanup (1 in 20 calls)
    import random
    if random.randint(1, 20) == 1:
        cleanup_cache()


def cleanup_cache(max_age_seconds: int | None = None) -> None:
    """Remove stale cache files older than max_age_seconds."""
    if max_age_seconds is None:
        max_age_seconds = max(TTL_NETWORK, TTL_RESULT) * 2
    if not CACHE_DIR.exists():
        return
    now = time.time()
    for path in CACHE_DIR.iterdir():
        if path.is_file() and (now - path.stat().st_mtime) > max_age_seconds:
            path.unlink(missing_ok=True)


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
