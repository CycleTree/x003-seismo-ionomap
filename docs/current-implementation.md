# Current Implementation

## Purpose

この文書は、現在リポジトリに実装済みの前処理内容を説明する。

対象は次の 5 段階である。

1. `ringo rnxcsv` の CSV を観測 Parquet に変換する ingest
2. 選択済み観測から leveled STEC arc を生成する処理
3. `ringo qc` から観測局位置を抽出する処理
4. `stec_arcs` から `IPP / VTEC / grid / anomaly grid` を生成する処理
5. 複数観測局を並列に処理して national grid を作る処理

計算の理論背景は [TEC Processing Pipeline](./tec-processing-pipeline.md) を参照する。

## Implemented Files

### Ingest

- [backend/app/config/gnss.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/app/config/gnss.py:1)
- [backend/app/processing/ringo_ingest.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/app/processing/ringo_ingest.py:1)
- [backend/scripts/ingest_ringo_csv.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/scripts/ingest_ringo_csv.py:1)

### STEC arcs

- [backend/app/processing/stec.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/app/processing/stec.py:1)
- [backend/scripts/build_stec_arcs.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/scripts/build_stec_arcs.py:1)

### Station metadata, IPP, grid, anomaly

- [backend/app/processing/station_metadata.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/app/processing/station_metadata.py:1)
- [backend/app/processing/bias.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/app/processing/bias.py:1)
- [backend/app/processing/ipp.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/app/processing/ipp.py:1)
- [backend/app/processing/grid.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/app/processing/grid.py:1)
- [backend/app/processing/anomaly.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/app/processing/anomaly.py:1)
- [backend/app/processing/multi_station.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/app/processing/multi_station.py:1)
- [backend/scripts/build_station_metadata.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/scripts/build_station_metadata.py:1)
- [backend/scripts/build_bias_tables.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/scripts/build_bias_tables.py:1)
- [backend/scripts/build_ipp_points.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/scripts/build_ipp_points.py:1)
- [backend/scripts/build_tec_grid.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/scripts/build_tec_grid.py:1)
- [backend/scripts/build_anomaly_grid.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/scripts/build_anomaly_grid.py:1)
- [backend/scripts/run_full_pipeline.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/scripts/run_full_pipeline.py:1)
- [backend/scripts/run_multi_station_pipeline.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/scripts/run_multi_station_pipeline.py:1)

## Stage 1: RINGO CSV Ingest

### Input

入力は `ringo rnxcsv` の CSV。

例:

```bash
ringo rnxcsv data/140/00011400.26d.gz -o data/intermediate/ringo_csv/00011400.csv
```

CSV は衛星ごとの wide 形式で、先頭列に `PRN`, `time` があり、その後ろに観測コード列が並ぶ。

例:

```text
PRN,time,C1C,L1C,D1C,S1C,C2W,L2W,...
G01,2026-05-20 00:00:00.000,20097557.797,105613442.765,...
```

### What the code does

`load_ringo_csv()` は以下を行う。

- 区切り `", "` を前提に CSV 読み込み
- ヘッダの `>` 除去
- 混入しうる擬似ヘッダ行の除去
- `time` を UTC datetime に変換
- 観測列を `float64` に変換

`normalize_wide_observations()` は以下を付加する。

- `station_id`
- `system`
- `sat_id`
- `source_path`

`wide_to_long_observations()` は wide を long に変換する。

```text
station_id, system, sat_id, time, obs_code, value
```

`select_priority_observations()` は GPS を対象に、優先順位で 1 本ずつ選ぶ。

- `L1_value`, `L1_code`
- `L2_value`, `L2_code`
- `C1_value`, `C1_code`
- `C2_value`, `C2_code`
- `S1_value`, `S1_code`
- `S2_value`, `S2_code`

優先順位は [backend/app/config/gnss.py](/home/mtdnot/dev/x003-seismo-ionomap/backend/app/config/gnss.py:1) で定義している。

### Output

`ingest_ringo_csv.py` は次の 3 つを出力する。

- `<prefix>.wide.parquet`
- `<prefix>.long.parquet`
- `<prefix>.selected.parquet`

例:

```bash
docker compose exec -T backend python scripts/ingest_ringo_csv.py \
  /data/intermediate/ringo_csv/00011400.csv \
  --output-dir /data/intermediate/observations
```

生成物:

```text
data/intermediate/observations/00011400.wide.parquet
data/intermediate/observations/00011400.long.parquet
data/intermediate/observations/00011400.selected.parquet
```

### Current assumptions

- 現在の観測コード選択は GPS 優先
- RINGO CSV の列構造が大きく変わらない前提
- LLI はまだ ingest に含めていない
- `rnxcsv obs nav` の `az`, `el` が利用できる前提

## Stage 2: STEC Arc Build

### Input

入力は `selected.parquet`。

主に使う列:

- `L1_value`
- `L2_value`
- `C1_value`
- `C2_value`
- `time`
- `station_id`
- `sat_id`
- `system`

### Step 1: Filter valid dual-frequency rows

`prepare_dual_frequency_observations()` は次を満たす行だけを残す。

- `system == "G"`
- `L1_value`, `L2_value`, `C1_value`, `C2_value` がすべて非欠損

さらに `station_id`, `sat_id`, `time` でソートする。

### Step 2: Geometry-free combinations

`compute_geometry_free_and_stec()` は以下を計算する。

```math
L_{\mathrm{GF}} = \lambda_1 L_1 - \lambda_2 L_2
```

```math
P_{\mathrm{GF}} = C_2 - C_1
```

コード上の列名は次。

- `phase_geometry_free_m`
- `code_geometry_free_m`

### Step 3: Convert to STEC

GPS L1/L2 の係数を固定値として持ち、次で TECU に変換している。

```math
\mathrm{STEC}_{\Phi}
=
\frac{f_1^2 f_2^2}{40.3 \times 10^{16}(f_1^2 - f_2^2)}
(\lambda_1 L_1 - \lambda_2 L_2)
```

```math
\mathrm{STEC}_{P}
=
\frac{f_1^2 f_2^2}{40.3 \times 10^{16}(f_1^2 - f_2^2)}
(C_2 - C_1)
```

列名:

- `phase_stec_tecu`
- `code_stec_tecu`

### Step 4: Slip detection and arc segmentation

`detect_cycle_slips_and_segment_arcs()` は station-satellite ごとに差分をとり、arc 分割を行う。

計算列:

- `gap_seconds`
- `phase_stec_diff_tecu`

現在の分割条件:

```math
\Delta t > 300 \ \mathrm{s}
```

または

```math
|\Delta \mathrm{STEC}_{\Phi}| > 2.0 \ \mathrm{TECU}
```

結果として次を付与する。

- `is_gap_break`
- `is_phase_jump_break`
- `is_arc_start`
- `arc_index`
- `arc_id`

### Step 5: Arc filtering and explicit bias leveling

`level_phase_stec_by_arc()` はまず短い arc を落とす。

現在の条件:

```math
N_{\mathrm{arc}} \ge 10
```

その後、`code_stec_tecu - phase_stec_tecu` を観測値として、次の加法モデルで bias を分解する。

```math
\Delta_k
=
b_{r(k)} + b_{s(k)} + b_{\mathrm{arc}(k)} + \epsilon_k
```

```math
\mathrm{STEC}_{\mathrm{leveled}}
=
\mathrm{STEC}_{\Phi}
+
b_r
+
b_s
+
b_{\mathrm{arc}}
```

付与される列:

- `arc_point_count`
- `receiver_bias_tecu`
- `satellite_bias_tecu`
- `arc_bias_tecu`
- `bias_model_residual_tecu`
- `stec_leveled_tecu`

### Output

```bash
docker compose exec -T backend python scripts/build_stec_arcs.py \
  /data/intermediate/observations/00011400.selected.parquet \
  --output-dir /data/intermediate/stec_arcs
```

生成物:

```text
data/intermediate/stec_arcs/00011400.stec_arcs.parquet
```

### Current sample result

サンプル `00011400` では次が生成されている。

- rows: `25956`
- arcs: `83`

## Stage 3: Station metadata

`build_station_metadata.py` は `ringo qc` の summary から `Approx XYZ` を抽出し、観測局の ECEF 座標と測地座標を Parquet に保存する。

出力例:

```text
data/intermediate/stations/0001.station.parquet
```

## Stage 4: IPP, VTEC, grid, anomaly

### IPP / VTEC

`build_ipp_points.py` は `stec_arcs.parquet` と station metadata を読み、次を計算する。

- station 緯度経度
- 方位角 `az`
- 仰角 `el`
- thin-shell model による `IPP`
- mapping function
- `vtec_tecu`

現在は衛星位置を自前で暦計算せず、`ringo rnxcsv obs nav` が出す `az/el` を使っている。

出力例:

```text
data/intermediate/ipp_points/00011400_nav.ipp_points.parquet
```

### Grid

`build_tec_grid.py` は `ipp_points.parquet` を時空間セルに集約する。

主な列:

- `time_bin`
- `grid_lat_deg`
- `grid_lon_deg`
- `sample_count`
- `mean_vtec_tecu`
- `median_vtec_tecu`
- `std_vtec_tecu`

### Anomaly

`build_anomaly_grid.py` は grid 単位で baseline と dispersion を求め、`delta_vtec_tecu` と `z_score` を付与する。

現在の anomaly は quiet-day ではなく、同一セル内の簡易統計ベースである。

出力例:

```text
data/intermediate/anomaly_grid/00011400_nav.anomaly_grid.parquet
```

## Stage 5: Multi-station national batch

単局の `IPP -> grid` では日本全域を覆えないため、`run_multi_station_pipeline.py` で複数観測局を並列処理して national grid を作る。

処理内容:

1. `raw_dir` から `*.26d.gz` と `*.26N.tar.gz` の station pair を収集
2. 各 station ごとに `qc -> rnxcsv -> ingest -> stec_arcs -> station metadata -> ipp_points`
3. 全 station の `ipp_points` を結合
4. national `tec_grid` を生成
5. national `anomaly_grid` を生成

局ごとの前処理は `ProcessPoolExecutor` で並列化している。既定の worker 数は `min(cpu_count, 8)`。

出力例:

```text
data/intermediate/national_make/national/national.ipp_points.parquet
data/intermediate/national_make/tec_grid/national.tec_grid.parquet
data/intermediate/national_make/anomaly_grid/national.anomaly_grid.parquet
```

確認済みの subset 実行:

```bash
make national-pipeline MAX_STATIONS=5 WORKERS=2
```

結果:

- stations: `5`
- `ipp_points`: `107847 rows`
- `tec_grid`: `10725 rows`
- `anomaly_grid`: `10725 rows`

## Output Schema Summary

### `selected.parquet`

主な列:

- `station_id`
- `system`
- `sat_id`
- `time`
- `L1_value`, `L1_code`
- `L2_value`, `L2_code`
- `C1_value`, `C1_code`
- `C2_value`, `C2_code`
- `S1_value`, `S1_code`
- `S2_value`, `S2_code`

### `stec_arcs.parquet`

追加列:

- `phase_geometry_free_m`
- `code_geometry_free_m`
- `phase_stec_tecu`
- `code_stec_tecu`
- `gap_seconds`
- `phase_stec_diff_tecu`
- `is_gap_break`
- `is_phase_jump_break`
- `is_arc_start`
- `arc_index`
- `arc_id`
- `arc_point_count`
- `receiver_bias_tecu`
- `satellite_bias_tecu`
- `arc_bias_tecu`
- `bias_model_residual_tecu`
- `stec_leveled_tecu`

### `ipp_points.parquet`

追加列:

- `lat_deg`
- `lon_deg`
- `az`
- `el`
- `mapping_function`
- `vtec_tecu`
- `ipp_lat_deg`
- `ipp_lon_deg`

### `tec_grid.parquet`

主な列:

- `time_bin`
- `grid_lat_deg`
- `grid_lon_deg`
- `sample_count`
- `mean_vtec_tecu`
- `median_vtec_tecu`
- `std_vtec_tecu`

### `anomaly_grid.parquet`

追加列:

- `baseline_vtec_tecu`
- `delta_vtec_tecu`
- `z_score`

## Not Implemented Yet

現在まだ入っていないもの:

- LLI を使った slip 判定
- Melbourne-Wubbena など追加の slip 指標
- elevation mask の厳密なチューニング
- satellite position の自前計算
- quiet-day baseline
- multi-GNSS の本格対応
- 全 1301 局での national batch 常用運転
- frontend 上の時系列統計パネル

## Operational Notes

- 現在のローカル開発実行は Docker 前提
- 実行コマンドは `docker compose exec -T backend ...`
- 主要な実行入口は `Makefile`
- `make national-pipeline` は毎回最初に `pytest` を実行する
- `data/` は Git 管理から外す前提
