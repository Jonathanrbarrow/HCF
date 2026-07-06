"""
HCF API routes — serves comfort-scored GeoJSON to the frontend.
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from hcf import __version__
from hcf.config import settings
from hcf.scoring.pipeline import generate_comfort_geojson

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health_check():
    """Health check endpoint — also reports feature flag status."""
    return {
        "status": "ok",
        "version": __version__,
        "factors": {
            "noise": settings.enable_noise_factor,
            "canopy": settings.enable_canopy_factor,
            "heat": settings.enable_heat_factor,
            "safety": settings.enable_safety_factor,
            "traffic": settings.enable_traffic_factor,
            "aqi": settings.enable_aqi_factor,
        },
    }


@router.get("/api/v1/comfort")
def get_comfort_map(
    city: str = Query(..., description="City name, e.g. 'Denver, Colorado, USA'"),
    max_segments: int = Query(
        settings.max_segments_default,
        description="Maximum street segments to return",
        ge=10,
        le=settings.max_segments_limit,
    ),
):
    """
    Generate comfort-scored GeoJSON for a US city.

    Returns a FeatureCollection of street segments with comfort scores.
    Each feature has properties: comfort_score, noise_dba, canopy_pct.
    """
    try:
        geojson = generate_comfort_geojson(
            place_query=city,
            max_segments=max_segments,
        )
        return geojson
    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid city query: '{city}'. Please provide a valid US city name.",
        )
    except Exception as e:
        logger.exception("Failed to generate comfort map for '%s'", city)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while generating the comfort map. Please try again.",
        )


