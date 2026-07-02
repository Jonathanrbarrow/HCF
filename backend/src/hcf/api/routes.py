"""
HCF API routes — serves comfort-scored GeoJSON to the frontend.
"""
from fastapi import APIRouter, HTTPException, Query

from hcf.config import settings
from hcf.scoring.pipeline import generate_comfort_geojson

router = APIRouter()


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.2.0"}


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
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate comfort map for '{city}': {str(e)}",
        )


