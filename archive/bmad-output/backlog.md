# BMAD Implementation Backlog: Comfort Factors MVP

**Role:** Scrum Master
**Project Name:** Comfort Factors
**Status:** Initial Draft

## Sprint 1: Foundation & Data Ingestion

### STORY 1.1: Project Scaffolding
- **As a** Developer,
- **I want** to set up the basic project structure (Frontend and Backend),
- **So that** I have a clean foundation for implementation.
- **Acceptance Criteria:**
  - FastAPI backend initialized with a basic `/health` endpoint.
  - React/TypeScript frontend initialized.
  - Basic Leaflet map displayed on the home page.

### STORY 1.2: OSM Network Fetcher
- **As a** User,
- **I want** to see the pedestrian network of a city on the map,
- **So that** I know where walking is possible.
- **Acceptance Criteria:**
  - Backend endpoint `GET /api/v1/network?city={name}` returns GeoJSON from OSM.
  - Frontend renders the network segments as blue lines.

### STORY 1.3: Static Environmental Data Layer
- **As a** Planner,
- **I want** to overlay a static noise or heat map,
- **So that** I can visually correlate the network with stress factors.
- **Acceptance Criteria:**
  - Prototype noise data (Mock or static GeoJSON) can be toggled on the map.
  - Network segments color-coded based on a dummy "Comfort Score."

## Sprint 2: The Scoring Engine

### STORY 2.1: Heat Data Integration
- **As a** Developer,
- **I want** to fetch real heat data for a city bounding box,
- **So that** I can calculate thermal stress.
- **Acceptance Criteria:**
  - Integration with a temperature API or static dataset.
  - Data mapped to OSM segments via spatial join.

### STORY 2.2: Noise Data Integration
- **As a** Developer,
- **I want** to fetch or calculate noise levels for city segments,
- **So that** I can calculate acoustic stress.
- **Acceptance Criteria:**
  - Use road hierarchy (Motorway = High Noise, Residential = Low) to assign noise weights if real data is unavailable.

### STORY 2.3: Comfort Score Calculation
- **As a** User,
- **I want** to see a "Comfort Score" (0-100) for every street segment,
- **So that** I can identify the most/least comfortable paths.
- **Acceptance Criteria:**
  - Formula implemented: `Score = 100 - (Heat_Factor + Noise_Factor)`.
  - Map segments color-coded (Red-to-Green gradient).
