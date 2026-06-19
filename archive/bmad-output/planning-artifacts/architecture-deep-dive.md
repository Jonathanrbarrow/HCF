# BMAD Deep-Dive Architecture: The Spatial Engine & Data Strategy

**Role:** Architect
**Project:** Comfort Factors
**Status:** Under Review (Phase 2 Planning)

## 1. Abstract Data Ingestion & Scalability (The Adapter Pattern)
To ensure the system can scale to **any city in the United States**, the architecture cannot rely on hardcoded API calls to specific, local GIS endpoints. 

Instead, the system utilizes a **Provider Adapter Pattern**:
- **Abstract Interfaces:** The core engine requests `HeatData(bbox)` or `NoiseData(bbox)`. It does not know *where* the data comes from.
- **MVP Focus (National Datasets):** For the initial prototype, the adapters will *only* plug into National APIs (e.g., `US_DOTNoiseAdapter`, `NOAA_HeatAdapter`) and global proxies (e.g., `OSMProxyAdapter`). This guarantees day-one functionality across the entire US.
- **Future Phase (Local Municipal Data):** As the product matures, we will build `MunicipalGISAdapter`s for specific cities that have high-fidelity local data. The adapter pattern ensures these can be plugged in later without rewriting the core scoring engine.

## 2. Data Layer Strategy
The system will utilize a "Tiered Data Model" to handle the variability of urban data availability across US cities.

| Factor | Tier 1 (Primary Source) | Tier 2 (Proxy/Estimation) | Tier 3 (Calibration/Validation) |
| :--- | :--- | :--- | :--- |
| **Connectivity** | OSM Pedestrian Network | Road Centerlines (with buffer) | Municipal GIS |
| **Noise** | US DOT National Noise Map (ArcGIS API) | Road Class (e.g., Motorway = 80dB, Res = 40dB) | Existing DOT Acoustic Monitors |
| **Heat** | Land Surface Temp (NOAA/NASA) | Simulated UHI based on impervious surface % (OSM) | Public Weather Stations / PurpleAir |
| **Shade** | High-Res Tree Canopy (Local GIS) | Geometric Simulation (OSM Building Footprints + Solar Angle/Time of Day) | N/A |
| **Safety** | Sidewalk Width/Presence (OSM) | Street Classification (Speed Limit/Lanes) | Google Street View / Mapillary (Visual API) |

*Note on Sensors:* The architecture strictly prohibits the deployment of *new* physical hardware. Tier 3 relies entirely on integrating APIs from **existing, public sensor networks** to provide ground-truth data that hardens and validates the Tier 1 & 2 simulations.

## 2. The Spatial Join Workflow (The "Corridor-Segment" Logic)
To maintain performance, the system will not use raw raster data for scoring. Instead, it will map all data onto the **OSM Graph**.

1.  **Graph Construction:** Use `OSMnx` to fetch a walk-simplified graph for the target bounding box.
2.  **Environmental Sampling:**
    - For **Noise:** Query the DOT ArcGIS REST API for the bbox. Perform a spatial join (nearest neighbor) to assign dB values to every edge in the graph.
    - For **Heat:** Sample a coarse temperature raster (e.g., Landsat 8) at the midpoint of each street segment.
3.  **Proxy Calculation:** If specific data is missing, the `ProxyModule` will infer values based on OSM tags (e.g., `maxspeed`, `lanes`, `surface`).

## 3. Scoring Algorithm (Multi-Objective)
The "Comfort Score" (CS) is a weighted sum of normalized penalties.

`CS = 100 - [ (wH * Heat_Penalty) + (wN * Noise_Penalty) + (wS * Safety_Penalty) ]`

- **Normalization:** All raw inputs (Celsius, Decibels, Meters) must be scaled to a 0.0 - 1.0 range based on human comfort thresholds.
  - *Example:* Noise > 70dB = 1.0 penalty; Noise < 45dB = 0.0 penalty.
- **Dynamic Weighting:** Planners can adjust `wH`, `wN`, and `wS` via the UI to simulate different priorities (e.g., "Heat Wave Mode").

## 4. Scalability & Compute Strategy
- **Client-Side vs Server-Side:** 
    - **Server:** Data ingestion, heavy spatial joins (GeoPandas), and graph pruning.
    - **Client:** Final score color-coding (Leaflet/Mapbox) and UI weight adjustments.
- **Caching:** The system will cache processed GeoJSON segments for 24 hours to avoid redundant API calls to DOT/NOAA.

## 5. Architectural Decision Records (ADR)
- **ADR 001: Vector over Raster.** We will store scores on vector segments (streets) rather than a continuous heatmap. This allows for direct integration into routing engines later.
- **ADR 002: Python Backend.** GeoPandas and OSMnx are the only libraries capable of handling this level of spatial complexity without a full GIS server (like ArcGIS or GeoServer).
