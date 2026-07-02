"""
HCF API routes — serves comfort-scored GeoJSON to the frontend.
"""
from fastapi import APIRouter, HTTPException, Query

from hcf.config import settings
from hcf.scoring.pipeline import generate_comfort_geojson, generate_route_geojson

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


@router.get("/api/v1/route")
def get_comfort_route(
    start_lat: float = Query(..., description="Start latitude"),
    start_lon: float = Query(..., description="Start longitude"),
    end_lat: float = Query(..., description="End latitude"),
    end_lon: float = Query(..., description="End longitude"),
    w_noise: float = Query(33.3, description="Noise weight"),
    w_canopy: float = Query(33.3, description="Canopy/shade weight"),
    w_heat: float = Query(33.3, description="Heat weight"),
):
    """
    Compute two walking paths between start and end points:
    1. Shortest path (by physical distance)
    2. Comfort-adjusted path (maximizing comfort based on weights)
    """
    try:
        geojson = generate_route_geojson(
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            w_noise=w_noise,
            w_canopy=w_canopy,
            w_heat=w_heat,
        )
        return geojson
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute route: {str(e)}",
        )

