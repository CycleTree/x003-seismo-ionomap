# Release v0.1

## Scope

`v0.1` は、RINEX/CRX.GZ から Web 地図表示までを一通り通すための最初の実装版である。

目的は次の 3 点だった。

1. `RINGO` を用いた前処理パイプラインを実装する
2. `STEC -> IPP -> VTEC -> grid -> anomaly` の最小構成を作る
3. FastAPI と frontend で地図表示までつなぐ

## What is included

### Data pipeline

- `ringo qc`
- `ringo rnxcsv`
- RINGO CSV ingest
- GPS L1/L2 優先の観測コード選択
- geometry-free combination
- cycle slip / gap による arc segmentation
- code leveling
- station metadata 抽出
- `IPP / VTEC`
- `tec_grid / anomaly_grid`
- 単局パイプライン
- 複数局 national batch の初期版

### Backend

- FastAPI
- `/health`
- `/api/anomaly-grid/times`
- `/api/anomaly-grid`

### Frontend

- MapLibre による anomaly grid 表示
- 時刻選択
- cell popup
- ブラウザ上の viewer settings
  - API URL
  - min sample count
  - min abs z-score
  - fill opacity

### Developer workflow

- Docker ベースの実行環境
- `Makefile`
- unit / integration tests
- `make test`
- `make sample-pipeline`
- `make national-pipeline`

## Current limitations

`v0.1` は「全国の連続 VTEC 場」を推定する実装ではない。

現在の national map は、複数局の `IPP` を格子集約したものであり、主な制約は次の通り。

- GPS 中心で multi-GNSS が未完成
- receiver / satellite bias の明示的推定が弱い
- LLI / SNR / elevation を用いた厳密な品質管理が未完成
- anomaly は quiet-day baseline ではなく簡易 baseline
- 全国格子そのものを未知数とする逆問題は未実装
- そのため、地図は疎で海上や周辺部に欠測が残る

## Release intent

`v0.1` は production-ready な電離圏マップ生成系ではなく、次の段階へ進むための基盤版である。

この版では、次を確認できる。

- データ取得から Web 可視化までの技術経路
- モジュール分割
- テスト実行経路
- Docker での再現可能な開発環境
