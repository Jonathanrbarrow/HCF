# HCF — Human Comfort Factors

> A scalable walk-comfort scoring tool for any city in the United States.  
> This document is the single source of truth for project goals. It is updated with every meaningful addition to the repo.

---

## The Problem

Traditional walkability metrics (e.g., Walk Score) measure **proximity** — how close you are to destinations. They ignore the **experience** of getting there. A 5-minute walk along a sun-baked, 80dB highway with no shade is scored the same as a 5-minute walk through a tree-lined, quiet residential street. Planners and developers need a tool that captures the difference.

## The Solution

Score every walkable street segment in a US city on a **0–100 Comfort Scale** by layering environmental stressors — heat, noise, and shade — on top of the pedestrian network. Deliver results through a lightweight browser frontend as a color-coded interactive map.

**Scoring formula:**

```
Comfort Score = 100 - [(wH × Heat_Penalty) + (wN × Noise_Penalty) + (wS × Shade_Penalty)]
```

- All penalties normalized to 0.0–1.0 against human comfort thresholds
- Weights (w) are adjustable by the user
- Scored per street segment (vector, not raster) for future routing compatibility

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

1. **No proprietary hardware or sensors.** All data from existing public APIs and open datasets. *(Lesson from predecessor: IoT sensors created regulatory/scaling nightmares.)*
2. **Python backend** for geospatial processing (OSMnx, GeoPandas). These are the only viable tools short of a full GIS server.
3. **Lightweight browser frontend.** Keep it simple — Leaflet or similar. No GPU-rendering frameworks unless proven necessary.
4. **Validate data sources before building on them.** Every API gets a throwaway test script before any architecture depends on it.
5. **Vertical slices over horizontal layers.** Each phase delivers a working, demoable increment — not "all backend, then all frontend."

---

## Phased Scope

### Phase 1 — Vertical Slice (MVP)
> Goal: Colored lines on a map from real data.

- [ ] Validate that `osmnx` + `geopandas` install and run on the dev environment
- [ ] Validate at least one environmental data source API (noise or heat) returns usable street-level data
- [ ] Backend: Fetch pedestrian network for a given US city via OSMnx
- [ ] Backend: Fetch environmental data and spatial-join to street segments
- [ ] Backend: Compute comfort score per segment
- [ ] Frontend: Render scored segments as colored lines on an interactive map
- [ ] End-to-end: User types a city name → sees scored map

### Phase 2 — Multi-Factor & Polish
> Goal: Multiple data layers, user controls, production-ready.

- [ ] Add second environmental data source
- [ ] User-adjustable weight sliders in the UI
- [ ] Data caching (avoid re-fetching on every request)
- [ ] Error handling and loading states
- [ ] Mobile-responsive layout

### Phase 3 — Scale & Extend
> Goal: Power-user features and broader adoption.

- [ ] Comfort-weighted routing ("find the most comfortable walk")
- [ ] Exportable reports (PDF/image for planner presentations)
- [ ] Comparison mode (side-by-side cities or before/after scenarios)
- [ ] Additional data layers (air quality, shade/canopy, safety)

---

## Anti-Goals (Lessons from Predecessor)

These are things we will **not** do:

1. **No multi-document planning frameworks.** One Goals.md, updated as we go. No separate PRD, architecture doc, deep-dive, and backlog that contradict each other.
2. **No architecture astronautics.** No adapter patterns, tiered data models, or provider abstractions until the MVP works end-to-end.
3. **No untested data source assumptions.** If we can't hit an API and get usable data back in a test script, it doesn't go in the architecture.
4. **No frontend framework overhead.** Start with vanilla HTML + JS + Leaflet. Upgrade only when there's a proven need.
5. **No deployment planning before local works.** Docker, AWS, S3 are Phase 3 concerns at the earliest.

---

## Changelog

| Date | Change | Commit |
|------|--------|--------|
| 2026-06-18 | Initial Goals.md — project bootstrapped | *(initial commit)* |
