# Level 1 — System Context

> Who uses HCF and what external systems does it depend on?

```mermaid
graph TB
    User["👤 Pedestrian / Urban Planner\n(Browser user)"]

    HCF["🏗️ HCF System\n\nComputes walk comfort scores\nfor any US city street segment"]

    OSM["🌐 OpenStreetMap\nOverpass API\n(Street network data)"]
    DOT["🏛️ US DOT Noise Map\nArcGIS REST API\n(Transportation noise dBA)"]
    META["📡 Meta/WRI S3\nCloud Optimized GeoTIFFs\n(1m canopy height)"]

    User -->|"Enters city name,\nviews scored map"| HCF
    HCF -->|"Fetches walk network\n(via OSMnx)"| OSM
    HCF -->|"Samples noise at\nstreet midpoints"| DOT
    HCF -->|"Reads canopy height\nat street midpoints"| META

    style HCF fill:#6c63ff,color:#fff,stroke:#5a52e0
    style User fill:#1a1d27,color:#e4e6ed,stroke:#2d3040
    style OSM fill:#2d3040,color:#e4e6ed,stroke:#4a5568
    style DOT fill:#2d3040,color:#e4e6ed,stroke:#4a5568
    style META fill:#2d3040,color:#e4e6ed,stroke:#4a5568
```

## External Dependencies

| System | Protocol | Auth | Data | Rate Limits |
|--------|----------|------|------|-------------|
| OpenStreetMap Overpass | HTTP (via OSMnx) | None | Walk network graph (nodes + edges) | Soft — be polite, cache results |
| US DOT Noise Map | ArcGIS REST `identify` | None | Road noise dBA (raster pixel values) | None published, ~200ms/req |
| Meta/WRI Canopy Height | S3 (anonymous) via rasterio | None | Canopy height meters (COG pixel values) | S3 standard — effectively unlimited |

## Planned External Dependencies (Phase 2)

| System | Protocol | Auth | Data |
|--------|----------|------|------|
| NOAA Weather API | REST | API key (free) | Current temperature / heat index |
