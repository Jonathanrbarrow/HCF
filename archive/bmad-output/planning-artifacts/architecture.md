# BMAD System Architecture: Comfort Factors MVP

**Role:** Architect
**Project Name:** Comfort Factors
**Status:** Draft

## 1. High-Level Tech Stack
- **Backend:** Python (FastAPI or Flask)
  - **Reasoning:** Superior libraries for geospatial analysis (OSMnx, GeoPandas, PySAL).
- **Frontend:** React with TypeScript + `react-map-gl` (MapLibre) + `deck.gl`
  - **Reasoning:** Basic Leaflet or OpenStreetMap implementations choke on large GeoJSON datasets (e.g., thousands of street segments). 
  - **MapLibre GL JS:** An open-source, highly performant base map provider (avoids Mapbox API costs).
  - **Deck.gl:** A WebGL-powered framework by Uber specifically designed to render large-scale spatial datasets (millions of points/lines) at 60fps. It sits on top of MapLibre and offloads rendering to the GPU.
- **Database:** PostgreSQL + PostGIS (Optional for MVP; can start with GeoJSON/Flat files).
  - **Reasoning:** Industry standard for spatial queries.
- **Data APIs:**
  - **OpenStreetMap (via Overpass API):** Road network and POIs.
  - **Google Earth Engine or Planetary Computer:** For satellite-derived Heat data.
  - **DOT National Noise Map:** For acoustic stress.

## 2. Component Diagram
1.  **UI (Frontend):** Handles city search, score toggles, and map rendering.
2.  **API Gateway (FastAPI):** Orchestrates data fetching and score computation.
3.  **Data Ingestion Layer (Adapter Pattern):**
    - A modular, redundant system of "Data Adapters" that abstracts the underlying API or database.
    - If a primary source (e.g., DOT ArcGIS API) fails or lacks coverage for a specific city, the system automatically falls back to an alternative adapter or proxy data source.
4.  **Spatial Engine:**
    - `NetworkFetcher`: Retrieves OSM pedestrian paths.
    - `StressProcessor`: Joins network segments with Noise and Heat data layers provided by the Ingestion Layer.
    - `ScoringModule`: Applies the weighted formula to each segment.
5.  **Data Cache:** Stores recently processed cities to improve performance.

## 3. Data Flow
1.  User inputs city.
2.  Backend fetches OSM network for the bounding box.
3.  Backend queries environmental data (Heat/Noise) for the same bounding box.
4.  Spatial join: Map noise/heat values to the nearest street segments.
5.  Scoring: Calculate 0-100 score per segment.
6.  JSON Response: Return a GeoJSON with `comfort_score` property.
7.  Frontend renders the GeoJSON on the map.

## 4. API Endpoints
### `GET /api/v1/map?bbox={min_lon,min_lat,max_lon,max_lat}`
- **Request:** Bounding box coordinates defining the district/neighborhood.
- **Response:** GeoJSON FeatureCollection of street segments with metadata and computed comfort scores.

### `POST /api/v1/analyze`
- **Request:** Bounding box and custom weights (e.g., `{"bbox": [...], "weights": {"heat": 0.5, "noise": 0.5}}`).
- **Response:** Re-calculated scores for the specific area.

## 5. Security & Compliance
- Ensure no PII (Personally Identifiable Information) is collected.
- Adhere to OpenStreetMap's usage policy for the Overpass API.

## 6. Infrastructure
- Initial deployment: Dockerized container on a cloud provider (e.g., AWS App Runner or GCP Cloud Run).
- Data storage: S3 for static GeoJSON caches.
