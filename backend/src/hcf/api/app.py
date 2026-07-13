"""
HCF API application factory.

Run with: uvicorn hcf.api.app:create_app --factory --reload
"""
import logging
import os
import pathlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from hcf import __version__
from hcf.config import settings
from hcf.api.routes import router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title="HCF — Human Comfort Factors",
        description="Walk comfort scoring API for US cities",
        version=__version__,
    )

    # CORS — allow the frontend to call the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    # Warn if production is using default localhost CORS origins
    if settings.env == "production" and any("localhost" in o for o in settings.cors_origins):
        logger.warning(
            "Running in production with localhost in CORS origins. "
            "Set HCF_CORS_ORIGINS to your frontend domain(s)."
        )

    # Serve the frontend if the frontend directory exists
    frontend_dir = pathlib.Path(__file__).resolve().parents[3] / "frontend"
    if frontend_dir.is_dir():
        frontend_dir = str(frontend_dir)  # StaticFiles expects str
        app.mount("/static", StaticFiles(directory=frontend_dir), name="frontend")

        @app.get("/")
        def serve_frontend():
            return FileResponse(os.path.join(frontend_dir, "index.html"))

    return app


# Module-level instance for `uvicorn hcf.api.app:app` (without --factory).
# Note: If using `uvicorn hcf.api.app:create_app --factory`, the app
# will be created twice. The project uses the non-factory pattern.
app = create_app()
