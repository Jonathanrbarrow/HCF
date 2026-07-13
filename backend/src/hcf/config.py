"""
HCF configuration — Pydantic Settings with env_prefix='HCF_'.

All hardcoded values that were previously scattered across modules
are centralised here. Override any value via environment variables
(e.g. HCF_CACHE_DIR=".my_cache") or a .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "development"

    # Cache
    cache_dir: str = ".cache"
    cache_ttl_network: int = 86400    # 24h
    cache_ttl_result: int = 2592000   # 30 days — all data is static/historical
    cache_hmac_key: str = ""  # Set HCF_CACHE_HMAC_KEY for pickle signing; empty = auto-generated per-process key

    # Noise API
    noise_api_url: str = "https://geo.dot.gov/server/rest/services/Hosted/NTAD_Noise_2020_CONUS_Road/MapServer"
    noise_default_dba: float = 50.0

    # Canopy
    canopy_s3_bucket: str = "dataforgood-fb-data"
    canopy_s3_prefix: str = "forests/v1/alsgedi_global_v6_float/chm"
    canopy_tile_zoom: int = 9
    canopy_shade_max_height: float = 15.0

    # Scoring
    default_heat_index: float = 85.0
    heat_api_url: str = "https://api.open-meteo.com/v1/forecast"

    # Traffic
    traffic_api_url: str = "https://geo.dot.gov/server/rest/services/Hosted"
    traffic_default_aadt: int = 5000

    # Air Quality (EPA AirNow)
    airnow_api_key: str = ""  # Set via HCF_AIRNOW_API_KEY env var
    aqi_default: int = 50  # "Good" AQI as default

    # Feature toggles — disable any factor for troubleshooting
    # (set via env: HCF_ENABLE_NOISE_FACTOR=false, etc.)
    enable_noise_factor: bool = True
    enable_canopy_factor: bool = True
    enable_heat_factor: bool = True
    enable_safety_factor: bool = True
    enable_traffic_factor: bool = True
    enable_aqi_factor: bool = False  # off by default — no street-level intervention model

    # API
    max_segments_default: int = 200
    max_segments_limit: int = 1000
    # Production: set HCF_CORS_ORIGINS env var to your frontend domain(s)
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = SettingsConfigDict(env_prefix="HCF_", env_file=".env")


settings = Settings()
