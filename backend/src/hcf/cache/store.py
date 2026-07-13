"""
Cache module — file-based caching with TTL for network graphs and results.

Storage:
  - Directory configurable via HCF_CACHE_DIR (default: .cache)
  - Pickle for graph objects (24h TTL), HMAC-SHA256 signed to prevent
    deserialisation of tampered files (key via HCF_CACHE_HMAC_KEY)
  - JSON for scored GeoJSON results (30d TTL)

Thread safety via atomic temp-file renames.
"""
import hashlib
import hmac
import json
import logging
import os
import pickle
import random
import tempfile
import time
from pathlib import Path

from hcf.config import settings

log = logging.getLogger(__name__)

_HMAC_KEY: bytes = (
    settings.cache_hmac_key.encode()
    if settings.cache_hmac_key
    else os.urandom(32)
)

_CACHE_DIR: Path | None = None
TTL_NETWORK = settings.cache_ttl_network
TTL_RESULT = settings.cache_ttl_result


def _get_cache_dir() -> Path:
    """Lazily resolve the cache directory on first access."""
    global _CACHE_DIR
    if _CACHE_DIR is None:
        _CACHE_DIR = Path(settings.cache_dir).resolve()
    return _CACHE_DIR


def _ensure_cache_dir() -> None:
    _get_cache_dir().mkdir(parents=True, exist_ok=True)


def cache_key(city_query: str, **params) -> str:
    """Build a deterministic cache key from a query string and optional params."""
    raw = city_query + json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _path_for(key: str, ext: str) -> Path:
    return _get_cache_dir() / f"{key}.{ext}"


def _is_fresh(path: Path, ttl_seconds: int) -> bool:
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < ttl_seconds


def _atomic_write(path: Path, data: bytes) -> None:
    """Write data atomically by writing to a temp file then renaming."""
    _ensure_cache_dir()
    fd, tmp = tempfile.mkstemp(dir=_get_cache_dir())
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
    # JSON first — json.loads cannot execute code, no HMAC needed.
    json_path = _path_for(key, "json")
    if _is_fresh(json_path, ttl_seconds):
        return json.loads(json_path.read_bytes())

    # Pickle — HMAC-SHA256 verified before deserialising.
    pkl_path = _path_for(key, "pkl")
    if _is_fresh(pkl_path, ttl_seconds):
        raw = pkl_path.read_bytes()
        if len(raw) < 32:
            log.warning("Cache file too small (missing HMAC), deleting: %s", pkl_path)
            pkl_path.unlink(missing_ok=True)
            return None
        stored_sig, payload = raw[:32], raw[32:]
        expected_sig = hmac.new(_HMAC_KEY, payload, "sha256").digest()
        if not hmac.compare_digest(stored_sig, expected_sig):
            log.warning("HMAC verification failed for cache file, deleting: %s", pkl_path)
            pkl_path.unlink(missing_ok=True)
            return None
        return pickle.loads(payload)

    return None


def set_cached(key: str, value, fmt: str = "pkl") -> None:
    """Store a value in the cache. fmt: 'pkl' for pickle, 'json' for JSON."""
    if fmt == "json":
        data = json.dumps(value, default=str).encode()
    else:
        payload = pickle.dumps(value)
        sig = hmac.new(_HMAC_KEY, payload, "sha256").digest()
        data = sig + payload
    _atomic_write(_path_for(key, fmt), data)
    # Probabilistic cache cleanup (1 in 20 calls)
    if random.randint(1, 20) == 1:
        cleanup_cache()


def cleanup_cache(max_age_seconds: int | None = None) -> None:
    """Remove stale cache files older than max_age_seconds."""
    if max_age_seconds is None:
        max_age_seconds = max(TTL_NETWORK, TTL_RESULT) * 2
    if not _get_cache_dir().exists():
        return
    now = time.time()
    for path in _get_cache_dir().iterdir():
        if path.is_file() and path.suffix in (".json", ".pkl") and (now - path.stat().st_mtime) > max_age_seconds:
            path.unlink(missing_ok=True)


# --- Network cache (pickle, 24h) ---

def get_network_cache(city_query: str):
    """Return cached network graph or None."""
    return get_cached(cache_key(city_query, _type="network"), TTL_NETWORK)


def set_network_cache(city_query: str, graph) -> None:
    """Cache a network graph."""
    set_cached(cache_key(city_query, _type="network"), graph, fmt="pkl")


# --- Result cache (JSON, 30d) ---

def get_result_cache(city_query: str, max_segments: int) -> dict | None:
    """Return cached scored GeoJSON result or None."""
    key = cache_key(city_query, _type="result", max_segments=max_segments)
    return get_cached(key, TTL_RESULT)


def set_result_cache(city_query: str, max_segments: int, geojson: dict) -> None:
    """Cache a scored GeoJSON result."""
    key = cache_key(city_query, _type="result", max_segments=max_segments)
    set_cached(key, geojson, fmt="json")
