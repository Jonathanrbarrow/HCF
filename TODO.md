# HCF — Future Improvements & Technical Debt
# ============================================
# Captured during the July 2026 code review session.
# These are ideas that were identified but not implemented.
# Organized by priority and category.


## Production Readiness
## --------------------

### P0: Must-do before real deployment

- [ ] **Set persistent HMAC cache key**
      When HCF_CACHE_HMAC_KEY is empty (the default), a random key is
      generated per-process via os.urandom(32). This means every server
      restart invalidates ALL pickle caches (network graphs). Set a
      stable key in production env vars or it defeats the purpose of
      caching.
      File: backend/src/hcf/cache/store.py (line 27-31)

- [ ] **Set production CORS origins**
      CORS still defaults to localhost:5173 and localhost:3000. The
      warning log was added, but the actual origins need to be configured
      via HCF_CORS_ORIGINS for the deployed frontend domain.
      File: backend/src/hcf/config.py (line 55)

- [ ] **Add API rate limiting**
      No rate limiting on /api/v1/comfort. A single user can trigger
      hundreds of concurrent OSMnx + API calls. Consider:
        - slowapi (FastAPI-compatible)
        - Per-IP limit: ~5 requests/minute
        - Global concurrency limit on the scoring pipeline


## Backend Improvements
## --------------------

### P1: Should-do for robustness

- [ ] **Deduplicate concurrent cache misses**
      Two simultaneous requests for the same uncached city will both
      fetch the network, score all segments, and write to cache. The
      second write wins but the work is wasted. Consider a lock or
      "in-flight" registry per cache key.
      File: backend/src/hcf/scoring/pipeline.py (generate_comfort_geojson)

- [ ] **Sanitize NaN before JSON serialization**
      If any pandas NaN values leak into the GeoJSON properties,
      json.dumps() will produce JavaScript NaN which is technically
      invalid JSON (and will break strict parsers). Add a pass like:
        scored = scored.fillna(value=pd.NA)  # or explicit None
      File: backend/src/hcf/scoring/pipeline.py (line ~302-320)

- [ ] **Non-editable pip install in Docker**
      The Dockerfile uses `pip install -e .` which creates .egg-link
      symlinks. In production, a standard `pip install .` is cleaner,
      produces faster imports, and doesn't depend on the source dir
      structure at runtime.
      File: Dockerfile.backend

- [ ] **Unit tests for cache HMAC signing**
      The HMAC signing/verification in store.py has no dedicated tests.
      Should test: valid signature loads, tampered payload rejects,
      truncated file rejects, missing HMAC rejects.
      Suggested file: backend/tests/test_cache.py

- [ ] **Unit tests for quality.py**
      The quality constants module is trivial but VALID_STATUSES should
      have a test confirming it matches the set of all constant values
      (prevents drift if a new status is added but not registered).
      Suggested file: backend/tests/test_quality.py


### P2: Nice-to-have

- [ ] **Southern Hemisphere support**
      _summer_date_range() assumes Northern Hemisphere (June-August).
      The docstring notes this. For international expansion, detect
      hemisphere from latitude and flip to Dec-Feb for southern cities.
      File: backend/src/hcf/data/heat.py (line 27-42)

- [ ] **Streaming/chunked GeoJSON for large cities**
      Cities with max_segments=1000 hold the entire GeoDataFrame +
      GeoJSON dict in memory. For very large requests, consider
      streaming the FeatureCollection or paginating the API response.

- [ ] **Frontend static file serving config**
      app.py uses `pathlib.Path(__file__).parents[3] / "frontend"` to
      find the frontend dir. This works in development but silently
      fails inside Docker (the guard handles it). Consider making it
      a config setting: HCF_FRONTEND_DIR.
      File: backend/src/hcf/api/app.py (line 48)

- [ ] **Structured logging (JSON)**
      Production logs use Python's default text format. For log
      aggregation (CloudWatch, Datadog, etc.), structured JSON logs
      would be more useful. Consider python-json-logger or structlog.


## Frontend Improvements
## ---------------------

### P1: Should-do

- [ ] **Add wAqi to URL params**
      URL params support wNoise/wCanopy/wHeat/wSafety/wTraffic but
      not wAqi. When AQI gets fully enabled, shareable URLs won't
      preserve the AQI weight setting.
      File: frontend/src/App.tsx (line 25-36)

- [ ] **Client vs backend score rounding mismatch**
      Backend: round(score, 2) → e.g. 73.45
      Client:  Math.round()   → e.g. 73
      The popup shows the client-rounded integer, which is fine for
      display, but the CSV export and stats may show slightly different
      values than the server-side score. Consider aligning.
      File: frontend/src/utils/scoring.ts (line 86)

### P2: Nice-to-have

- [ ] **Accessibility audit**
      Some interactive elements (deficit panel items, pill buttons)
      could use more descriptive ARIA labels. The map itself has no
      screen-reader support for segment data. Consider an accessible
      data table view as an alternative to the map.

- [ ] **Error retry with backoff**
      The useComfortData hook shows errors but doesn't offer retry.
      Add a "Try Again" button with exponential backoff for transient
      failures (network timeouts, 503s from external APIs).
      File: frontend/src/hooks/useComfortData.ts

- [ ] **Service worker / offline support**
      Once a city is scored, the GeoJSON could be cached in the
      browser via a service worker for offline viewing. The data is
      static/historical so staleness isn't a concern.

- [ ] **Dark/light theme toggle**
      The UI is dark-only. A theme toggle would improve accessibility
      and user preference support. The CSS already uses custom
      properties so the infrastructure is there.


## CI/CD
## -----

- [ ] **Pin Python package versions**
      pyproject.toml has unpinned deps (e.g. "fastapi", "osmnx").
      For reproducible builds, consider a requirements.lock or
      pip-compile output. At minimum, pin major versions.
      File: backend/pyproject.toml

- [ ] **Add Docker build to CI**
      The Dockerfile.backend is never tested in CI. A simple
      `docker build` step would catch Dockerfile syntax errors and
      missing system deps before they reach production.

- [ ] **Coverage reporting**
      No coverage tracking. Consider pytest-cov with a minimum
      threshold (e.g. 60%) to prevent regression.
