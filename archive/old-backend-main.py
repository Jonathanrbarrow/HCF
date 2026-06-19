from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Comfort Factors API", version="1.0.0")

# Configure CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BoundingBox(BaseModel):
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Comfort Factors API is running."}

@app.get("/api/v1/map")
def get_comfort_map(min_lon: float, min_lat: float, max_lon: float, max_lat: float):
    # TODO: Implement Spatial Engine logic (Story 1.2 and beyond)
    # 1. Fetch OSM Graph for bounding box
    # 2. Invoke Data Adapters (Noise, Heat proxies)
    # 3. Perform spatial join and compute score
    # 4. Return GeoJSON
    return {
        "type": "FeatureCollection",
        "features": [],
        "metadata": {
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "status": "Not Implemented Yet"
        }
    }
