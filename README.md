# x003-seismo-ionomap

## Tech Stack

### Frontend

- React
- TypeScript
- Vite
- MapLibre
- deck.gl
- Recharts / ECharts
- Zustand
- TanStack Query

### Backend

- Python FastAPI
- venv
- DuckDB
- Parquet / GeoJSON

### Infra

- Docker Compose

## Docs

- [TEC Processing Pipeline](docs/tec-processing-pipeline.md)
- [Current Implementation](docs/current-implementation.md)
- [GSI SFTP Data Notes](docs/gsi-sftp-data-notes.md)
- [Release v0.1](docs/release-v0.1.md)
- [v0.2 Plan](docs/v0.2-plan.md)

## Run

- `make test`
- `make sample-pipeline`
- `make national-pipeline MAX_STATIONS=5 WORKERS=2`
