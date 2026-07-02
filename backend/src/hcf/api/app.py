"""
HCF API application factory.

Run with: uvicorn hcf.api.app:create_app --factory --reload
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from hcf.config import settings
from hcf.api.routes import router


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title="HCF — Human Comfort Factors",
        description="Walk comfort scoring API for US cities",
        version="0.2.0",
    )

    # CORS — allow the frontend to call the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    # Serve the frontend if the frontend directory exists
    frontend_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "frontend",
    )
    if os.path.isdir(frontend_dir):
        app.mount("/static", StaticFiles(directory=frontend_dir), name="frontend")

        @app.get("/")
        def serve_frontend():
            return FileResponse(os.path.join(frontend_dir, "index.html"))

    return app


# Module-level instance for `uvicorn hcf.api.app:app`
app = create_app()
