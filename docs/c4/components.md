# Level 3 — Component Diagram

> What are the internal modules and how do they interact?

```mermaid
graph TB
    subgraph server["server.py — API Layer"]
        EP["/api/v1/comfort\nFastAPI endpoint"]
        HEALTH["/health"]
        STATIC["Static file serving\n(frontend/)"]
    end

    subgraph cache_layer["cache.py — Caching"]
        NC["NetworkCache\nfile-based, 24h TTL"]
        RC["ResultCache\nfile-based, 1h TTL"]
    end

    subgraph pipeline["pipeline.py — Orchestrator"]
        SCS["score_city_segments()\nBatch-fetches env data,\nscores each segment"]
        GCG["generate_comfort_geojson()\nConverts scored GDF → GeoJSON\n+ data_quality metadata"]
    end

    subgraph data_fetchers["Data Fetcher Modules"]
        NET["network.py\n\nfetch_walk_network()\nnetwork_to_geodataframe()"]
        NOISE["noise.py\n\nfetch_noise_at_point()\nfetch_noise_batch()\nget_noise_penalty()"]
        CANOPY["canopy.py\n\nfetch_canopy_at_point()\nfetch_canopy_batch()\nheight_to_cover_pct()\n_latlon_to_quadkey()"]
        HEAT["heat.py\n\nfetch_heat_at_point()\nfetch_heat_batch()"]
    end

    subgraph scoring_engine["scoring.py — Pure Computation"]
        SCORE["compute_comfort_score()\n\n100 - weighted penalties\nnoise + canopy + heat"]
    end

    EP --> RC
    RC -->|miss| GCG
    GCG --> SCS
    SCS --> NC
    NC -->|miss| NET
    SCS --> NOISE
    SCS --> CANOPY
    SCS --> HEAT
    SCS --> SCORE

    style EP fill:#6c63ff,color:#fff
    style NC fill:#f97316,color:#fff
    style RC fill:#f97316,color:#fff
    style SCS fill:#4a3fc7,color:#fff
    style GCG fill:#4a3fc7,color:#fff
    style NET fill:#22c55e,color:#fff
    style NOISE fill:#eab308,color:#000
    style CANOPY fill:#22c55e,color:#fff
    style HEAT fill:#22c55e,color:#fff
    style SCORE fill:#8b5cf6,color:#fff
```

## Request Lifecycle

```mermaid
sequenceDiagram
    participant U as Browser
    participant S as FastAPI
    participant RC as ResultCache
    participant P as Pipeline
    participant NC as NetworkCache
    participant N as network.py
    participant NZ as noise.py
    participant C as canopy.py
    participant H as heat.py
    participant SC as scoring.py

    U->>S: GET /api/v1/comfort?city=Denver
    S->>RC: check cache(city, max_segments)
    alt cache hit
        RC-->>S: cached GeoJSON
    else cache miss
        RC-->>S: miss
        S->>P: generate_comfort_geojson()
        P->>NC: check cache(city)
        alt network cached
            NC-->>P: cached graph
        else network not cached
            NC->>N: fetch_walk_network()
            N-->>NC: graph (cached for 24h)
            NC-->>P: graph
        end
        P->>P: extract midpoints from edges

        P->>NZ: fetch_noise_batch(midpoints)
        NZ-->>P: noise_dba[] + quality[]

        P->>C: fetch_canopy_batch(midpoints)
        C->>C: group by QuadKey
        C-->>P: canopy_height[] + quality[]

        P->>H: fetch_heat_batch(midpoints)
        H-->>P: apparent_temp[] + quality[]

        loop per segment
            P->>SC: compute_comfort_score()
            SC-->>P: score
        end

        P-->>S: GeoJSON + data_quality
        S->>RC: store in cache (1h TTL)
    end
    S-->>U: GeoJSON response
```

## Module Inventory

| Module | Lines | Responsibility | External Deps |
|--------|-------|---------------|---------------|
| `server.py` | ~70 | HTTP API, static files, CORS | FastAPI, uvicorn |
| `pipeline.py` | ~120 | Orchestration, GeoJSON assembly | osmnx, geopandas, shapely |
| `network.py` | ~50 | Walk network fetching | osmnx |
| `noise.py` | ~130 | DOT noise map queries | requests |
| `canopy.py` | ~220 | Meta/WRI canopy height reads | rasterio, boto3 |
| `heat.py` | ~100 | Open-Meteo apparent temperature reads | requests |
| `scoring.py` | ~100 | Comfort formula (pure math) | none |
| `cache.py` | ~80 | File-based caching with TTL | none (stdlib) |
