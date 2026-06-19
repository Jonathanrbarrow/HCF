"""
HCF API Server — serves comfort-scored GeoJSON to the frontend.

Run with: uvicorn src.server:app --reload
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from src.pipeline import generate_comfort_geojson

app = FastAPI(
    title="HCF — Human Comfort Factors",
    description="Walk comfort scoring API for US cities",
    version="0.1.0",
)

# CORS — allow the frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/comfort")
def get_comfort_map(
    city: str = Query(..., description="City name, e.g. 'Denver, Colorado, USA'"),
    max_segments: int = Query(200, description="Maximum street segments to return", ge=10, le=1000),
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


# Serve the frontend if the frontend directory exists
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="frontend")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))
