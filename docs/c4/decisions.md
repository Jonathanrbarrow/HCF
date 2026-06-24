# Architecture Decision Records

> Record significant architecture decisions here. Format: context → decision → consequences.

---

## ADR-001: Test-Driven Development with Random City Selection

**Date:** 2026-06-18
**Status:** Active

**Context:** The predecessor project worked for Gainesville, FL but collapsed when pointed at any other city. The backend faked data with hardcoded coordinates and mock values.

**Decision:** Every test randomly selects cities from a hardcoded list of the top 100 US cities. Tests validate geographic bounds, spatial variation, and cross-city distinctness. No test can pass with faked data.

**Consequences:** Tests are slower (real API calls) but impossible to fake. CI must have network access.

---

## ADR-002: Meta/WRI Canopy Height over NLCD Tree Canopy Cover

**Date:** 2026-06-23
**Status:** Active

**Context:** NLCD provides 30m resolution canopy cover percentage. Meta/WRI provides 1m resolution canopy height. Street-level comfort scoring needs sub-block resolution.

**Decision:** Use Meta/WRI Global Canopy Height (1m, COGs on S3). Convert height to estimated shade coverage for the scoring engine.

**Consequences:** Requires `rasterio` + `boto3` (heavier deps). Height→shade conversion is an approximation. 30× resolution improvement is decisive for street-level accuracy.

---

## ADR-003: File-Based Caching over Redis

**Date:** 2026-06-24
**Status:** Active

**Context:** Walk networks are expensive to fetch (10-30s) and change slowly. Scored results are expensive to compute (60-80s) due to API calls. Need caching but don't want infrastructure overhead.

**Decision:** File-based cache using stdlib (json/pickle). Walk networks cached 24h, scored results cached 1h. Cache keyed by city query string + parameters hash.

**Consequences:** No Redis/Memcached dependency. Single-server only (no shared cache). Sufficient for MVP. Can migrate to Redis later if needed.

---

## ADR-004: Batch Data Fetching over Per-Point Queries

**Date:** 2026-06-24
**Status:** Active

**Context:** Per-point API queries for 200 segments = 400 sequential HTTP calls = ~80 seconds. Unacceptable for a web application.

**Decision:** Batch noise queries using multi-point geometry. Group canopy reads by QuadKey tile (open each COG once, read all contained points). Track data quality per-segment.

**Consequences:** Significantly faster (est. 10-15s vs 80s). More complex fetching code. Need to handle partial failures gracefully.

---

## ADR-005: Data Quality Tracking per Feature

**Date:** 2026-06-24
**Status:** Active

**Context:** When environmental data is unavailable (API timeout, no coverage), the pipeline silently substitutes defaults. Users can't tell which segments have real data.

**Decision:** Add a `data_quality` object to each GeoJSON feature's properties: `{"noise": "real|default|unavailable", "canopy": "real|default|unavailable", "heat": "fixed"}`. Frontend dims segments with low quality.

**Consequences:** Full transparency on data provenance. More complex pipeline code. Frontend needs quality-aware styling.

---

## ADR-006: CI Testing over Local Testing

**Date:** 2026-06-18
**Status:** Active (constraint-driven)

**Context:** The development PC (work machine) blocks Python executable execution via security policy.

**Decision:** Run all tests in GitHub Actions CI on Ubuntu. Local development is write-only; validation happens in CI.

**Consequences:** Cannot iterate locally on test failures. Must push to see test results. Forces good commit discipline.
