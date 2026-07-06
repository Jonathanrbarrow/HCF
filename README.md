# HCF — Human Comfort Factors

Walk comfort scoring for any US city. See how comfortable every street really is.

## What It Does

Type a US city name → get a color-coded map showing how comfortable each street is to walk on, scored by:
- 🔊 **Noise** — US DOT transportation noise data (dBA)
- 🌳 **Canopy** — Meta/WRI tree canopy height at 1m resolution
- 🌡️ **Heat** — (Phase 2: NOAA weather data)

## Quick Start

### Docker (recommended)

```bash
docker compose up
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Manual

**Backend:**
```bash
cd backend
pip install -e ".[dev]"
uvicorn hcf.api.app:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Architecture

See [docs/c4/](docs/c4/) for the full C4 architecture diagrams.

```
HCF/
├── backend/          Python API (FastAPI + geospatial pipeline)
├── frontend/         React + TypeScript + Leaflet
├── docs/c4/          Architecture diagrams (living docs)
├── docker-compose.yml   Local dev environment
└── Goals.md          Project goals and changelog
```

## Deployment

| Component | Platform | Why |
|-----------|----------|-----|
| Frontend  | Vercel   | Free CDN, scales infinitely for static/SSR |
| Backend   | Railway  | $5/mo start, Docker-native, scales to multi-instance |

## Contributing

1. Branch from `develop` (never commit directly to `main`)
2. Name branches `feature/xxx` or `fix/xxx`
3. All tests must pass before merging
4. Update [docs/c4/](docs/c4/) if architecture changes
