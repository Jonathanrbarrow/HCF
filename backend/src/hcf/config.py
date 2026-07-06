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
    cache_ttl_result: int = 3600      # 1h

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

    # API
    max_segments_default: int = 200
    max_segments_limit: int = 1000
    # Production: set HCF_CORS_ORIGINS env var to your frontend domain(s)
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = SettingsConfigDict(env_prefix="HCF_", env_file=".env")


settings = Settings()
