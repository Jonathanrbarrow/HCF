# Level 2 — Container Diagram

> What are the deployable units and how do they communicate?

```mermaid
graph TB
    subgraph Browser["🖥️ Browser"]
        FE["📄 Frontend\nindex.html\n\nVanilla HTML + JS\nLeaflet map rendering\nConfigurable API base"]
    end

    subgraph Server["⚙️ Python Backend"]
        API["🔌 FastAPI Server\nserver.py\n\nGET /api/v1/comfort\nGET /health"]
        CACHE["💾 File Cache\ncache.py\n\nWalk networks: 24h TTL\nScored results: 1h TTL"]
        PIPE["🔧 Pipeline\npipeline.py\n\nBatch data fetching\nPer-segment scoring\nData quality tracking"]
    end

    subgraph ExternalAPIs["☁️ External Data Sources"]
        OSM["🌐 Overpass API\n(OpenStreetMap)"]
        DOT["🏛️ DOT ArcGIS\n(Noise Map)"]
        S3["📡 AWS S3\n(Meta/WRI COGs)"]
    end

    FE -->|"HTTP GET\n/api/v1/comfort?city=..."| API
    API --> CACHE
    CACHE -->|cache miss| PIPE
    PIPE -->|"OSMnx\ngraph_from_place()"| OSM
    PIPE -->|"Batch identify\n(multi-point)"| DOT
    PIPE -->|"rasterio\ngrouped by QuadKey"| S3
    API -->|"GeoJSON\nFeatureCollection\n+ data_quality"| FE

    style FE fill:#1a1d27,color:#e4e6ed,stroke:#6c63ff
    style API fill:#6c63ff,color:#fff,stroke:#5a52e0
    style CACHE fill:#f97316,color:#fff,stroke:#d97706
    style PIPE fill:#6c63ff,color:#fff,stroke:#5a52e0
    style OSM fill:#2d3040,color:#e4e6ed,stroke:#4a5568
    style DOT fill:#2d3040,color:#e4e6ed,stroke:#4a5568
    style S3 fill:#2d3040,color:#e4e6ed,stroke:#4a5568
```

## Containers

| Container | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | HTML + JS + Leaflet | Renders scored map, handles user input |
| **FastAPI Server** | Python / uvicorn | REST API, serves frontend static files |
| **File Cache** | JSON/pickle on disk | Caches walk networks (24h) and scored results (1h) |
| **Pipeline** | Python (osmnx, rasterio, requests) | Orchestrates data fetching, scoring, GeoJSON assembly |
