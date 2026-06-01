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

- [計算式](docs/計算式.md)
- [Current Implementation](docs/current-implementation.md)
- [GSI SFTP Data Notes](docs/gsi-sftp-data-notes.md)
- [Reference](docs/reference.md)
- [Release v0.1](docs/release-v0.1.md)
- [v0.2 Plan](docs/v0.2-plan.md)

## Run

- `make test`
- `make sample-pipeline`
- `make national-pipeline MAX_STATIONS=5 WORKERS=2`

## CI

GitHub Actions では次を CI チェックとして扱う。

- backend: `pytest tests -q`
- frontend: `npm run build`

ローカルでは次を最低限の確認コマンドとする。

- `make test`
- `docker compose exec -T frontend npm run build`

## Development Workflow

`v0.2` 以降の開発は次のルールで進める。

1. 実装タスクは最初に GitHub Issue として登録する。
2. 1 issue = 1 feature branch を基本とする。
3. branch 名は `feature/#<issue_number>` とする。
4. feature branch から `v0.2` へ Pull Request を送る。
5. `v0.2` でレビュー・統合したあと、まとまった段階で `main` へマージする。
6. `main` は release 用の安定ブランチとして扱う。

要するに、

- issue を切る
- `feature/#<issue_number>` で実装する
- PR は `v0.2` に送る
- release 時に `main` へマージする

という流れで進める。
