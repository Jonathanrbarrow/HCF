# HCF — Human Comfort Factors

> A scalable walk-comfort scoring tool for any city in the United States.  
> This document is the single source of truth for project goals. It is updated with every meaningful addition to the repo.

---

## The Problem

Traditional walkability metrics (e.g., Walk Score) measure **proximity** — how close you are to destinations. They ignore the **experience** of getting there. A 5-minute walk along a sun-baked, 80dB highway with no shade is scored the same as a 5-minute walk through a tree-lined, quiet residential street. Planners and developers need a tool that captures the difference.

## The Solution

Score every walkable street segment in a US city on a **0–100 Comfort Scale** by layering environmental stressors — heat, noise, and shade — on top of the pedestrian network. Deliver results through a lightweight browser frontend as a color-coded interactive map designed for urban planning and corridor-level spatial analysis.

**Scoring formula:**

```
Comfort Score = 100 - [(wH × Heat_Penalty) + (wN × Noise_Penalty) + (wS × Shade_Penalty)]
```

- All penalties normalized to 0.0–1.0 against human comfort thresholds
- Weights (w) are adjustable by the user
- Scored per street segment (vector road centerlines) for precise block-by-block planning audits


---

## Success Criteria

| Milestone | Definition of Done |
|-----------|-------------------|
| **"Lines on a map"** | User enters a US city → colored street segments appear in the browser, driven by real data from at least one environmental source |
| **Multi-factor scoring** | At least two environmental layers (e.g., noise + heat) contribute to the comfort score |
| **Any US city** | Works for any city searchable via OpenStreetMap, not hardcoded to one location |
| **Lightweight frontend** | Loads in a standard browser, no install required, sub-3s initial map render for a mid-size city |

---

## Technical Constraints

1. **No proprietary hardware or sensors.** All data from existing public APIs and open datasets. *(Lesson from predecessor v1: IoT sensors created regulatory/scaling nightmares.)*
2. **Python backend** for geospatial processing (OSMnx, GeoPandas). These are the only viable tools short of a full GIS server.
3. **Lightweight browser frontend.** Keep it simple — Leaflet or similar. No GPU-rendering frameworks unless proven necessary.
4. **Validate data sources before building on them.** Every API gets a throwaway test script before any architecture depends on it.
5. **Vertical slices over horizontal layers.** Each phase delivers a working, demoable increment — not "all backend, then all frontend."
6. **Multi-city validation from day one.** Every backend feature must be tested against at least 2 different US cities before it's considered done. No city-specific assumptions in the pipeline. *(Lesson from predecessor v2: see Anti-Goals #1.)*

---

## Phased Scope

### Phase 1 — Vertical Slice (MVP)
> Goal: Colored lines on a map from real data, proven across multiple cities.

- [ ] Validate that `osmnx` + `geopandas` install and run on the dev environment
- [ ] Validate at least one environmental data source API (noise or heat) returns usable street-level data for multiple US cities
- [ ] Backend: Fetch pedestrian network for a given US city via OSMnx (city-agnostic — no hardcoded coordinates)
- [ ] Backend: Fetch environmental data and spatial-join to street segments
- [ ] Backend: Compute comfort score per segment
- [ ] Frontend: Render scored segments as colored lines on an interactive map
- [ ] End-to-end: User types a city name → sees scored map
- [ ] **Scalability gate: Verify end-to-end works for at least 3 different cities before moving to Phase 2**

### Phase 2 — Multi-Factor & Polish
> Goal: Multiple data layers, user controls, production-ready.

- [ ] Add second environmental data source
- [ ] User-adjustable weight sliders in the UI
- [ ] Data caching (avoid re-fetching on every request)
- [ ] Error handling and loading states
- [ ] Mobile-responsive layout

### Phase 3 — Scale & Extend
> Goal: Power-user features and broader adoption.

- [ ] Deficit Analysis (highlighting and listing streets with highest environmental stress)
- [ ] Exportable reports (PDF/image for planner presentations)
- [ ] Comparison mode (side-by-side cities or before/after scenarios)
- [ ] Additional data layers (air quality, safety/sidewalk width)

---

## Anti-Goals (Lessons from Predecessor)

The predecessor project (archived in `/archive`) had two iterations. Both failed for different reasons. These anti-goals encode the real lessons.

### What actually killed it

The predecessor **worked for Gainesville, FL.** It had a polished frontend and produced convincing results — for that one city. But the backend was faking too much of the computation: hardcoded data, city-specific assumptions, mock values where real data pipelines should have been. When we tried to point it at a different city, the entire foundation collapsed. By the time we realized the backend couldn't generalize, too much had been built on top of it to salvage.

### Rules to prevent repeating it

1. **No faking the hard parts.** The backend computation pipeline must use real data, real spatial joins, and real scoring from day one. No mock data, no hardcoded coordinates, no city-specific shortcuts that look right for one place but break everywhere else. If a data source isn't ready, the feature waits — we don't stub it with fake numbers and move on.
2. **Backend before polish.** The previous project had a great frontend on top of a hollow backend. This time: get the computation pipeline working and generalizing *first*. The frontend can be ugly until the engine is proven.
3. **Test with multiple cities immediately.** Every feature gets validated against at least 2-3 different US cities (varying size, region, data availability) before it's marked complete. A feature that only works for one city is a bug, not a feature.
4. **No Individual Routing/Navigation.** HCF is a spatial analysis, arborist planning, and real estate design audit tool. It is NOT a Google Maps replacement for turn-by-turn navigation. We explicitly prioritize whole-corridor comfort mapping, deficit analysis, and planning tools over pedestrian pathfinding.
5. **No city-specific assumptions in the pipeline.** The data fetching, spatial joining, and scoring must be purely parameterized by city name or bounding box. Zero hardcoded lat/lon, zero city-name conditionals, zero locally cached datasets for one specific place.
6. **Validate the geospatial stack early.** `osmnx` and `geopandas` have notoriously difficult Windows installs (GDAL/GEOS C dependencies). Confirm these actually run on the dev machine before building anything on top of them.

---

## Changelog

| Date | Change | Commit |
|------|--------|--------|
| 2026-06-18 | Initial Goals.md — project bootstrapped | `0a14eab` |
| 2026-06-18 | Corrected anti-goals based on actual predecessor failure mode (faked backend, not overplanning) | `b3a1d2f` |
| 2026-06-18 | TDD test suite: 5 test files (network, noise, canopy, scoring, integration) with random city selection from top 100 US cities | `87ab10c` |
| 2026-06-18 | Source modules: network, noise, canopy, scoring, pipeline — all city-agnostic, real API data | `87ab10c` |
| 2026-06-18 | FastAPI server, Leaflet frontend, GitHub Actions CI (tests run in cloud since work PC blocks Python) | `cd493d0` |
| 2026-06-23 | Switched canopy data from NLCD Tree Canopy Cover (30m, %) to Meta/WRI Global Canopy Height (1m, meters). 30× resolution improvement. | `cf2052b` |
| 2026-06-24 | C4 architecture diagrams (docs/c4/) — living doc updated with every push. Added ADRs. | `a11b953` |
| 2026-06-24 | File-based caching (cache.py): walk networks 24h TTL, scored results 1h TTL | `a11b953` |
| 2026-06-24 | Batch data fetching: noise + canopy batch functions, canopy grouped by QuadKey tile | `a11b953` |
| 2026-06-24 | Per-segment data quality tracking: real/default/unavailable status for noise, canopy, heat | `a11b953` |
| 2026-06-24 | Frontend: configurable API base URL, dashed/dimmed segments for low-quality data | `a11b953` |
| 2026-07-02 | Startup Restructure: Moved backend to structured package, migrated frontend to Vite + React + TypeScript, set up Docker dev environment, and updated CI | `2e6f4bb` |
| 2026-07-02 | Feature: Integrated Open-Meteo apparent temperature (heat index) API with batch support, Pydantic settings, and React popups | `decc451` |
| 2026-07-02 | Feature: Implemented comfort-adjusted routing engine (NetworkX/Dijkstra) with endpoint, automated test suite, and React weight sliders | `7781934` |
| 2026-07-02 | Refactor: Removed routing stubs to align with 'mapping for comfort' planning goal | `98046b9` |
| 2026-07-02 | Feature: Implemented Deficit Analysis side panel to list high-stress corridors, map panning, and street name matching | `d1ff0ba` |
| 2026-07-02 | Feature: Added Scenario Modeler, Safety factor, PDF Report exports, and released v0.3.0 | `7a2e8cc` |





