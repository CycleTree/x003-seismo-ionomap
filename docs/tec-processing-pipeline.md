# TEC Processing Pipeline

## Purpose

この文書は、RINEX 観測データから地図表示用の TEC 異常データを生成するまでの計算手順を定義する。

ここで扱うのは、実装ではなく「どの観測値から、どの物理量を、どの近似で導くか」である。

## Input Data

### Primary inputs

- RINEX observation files (`*.d.gz`, `*.crx.gz`, `*.rnx`)
- Navigation files (`*.N`, `*.N.tar.gz`) または将来的には SP3 precise ephemeris
- Station metadata

### RINGO output

`ringo rnxcsv` の出力を一次入力とする。

最初の MVP では、観測コードのうち GPS の以下を主対象にする。

- Carrier phase: `L1C`, `L1W`, `L1P`, `L2W`, `L2P`, `L2L`, `L2X`
- Pseudorange: `C1C`, `C1W`, `C1P`, `C2W`, `C2P`, `C2L`, `C2X`
- Signal strength: `S1C`, `S1W`, `S1P`, `S2W`, `S2P`, `S2L`, `S2X`

## Observation Model

GNSS の搬送波位相観測値とコード観測値は、簡略化すると次で表せる。

```math
\Phi_i =
\rho +
c(\delta t_r - \delta t_s) +
T -
I_i +
\lambda_i N_i +
\epsilon_{\Phi_i}
```

```math
P_i =
\rho +
c(\delta t_r - \delta t_s) +
T +
I_i +
\epsilon_{P_i}
```

記号:

- $\rho$: 幾何学的距離
- $c(\delta t_r - \delta t_s)$: 受信機時計差と衛星時計差
- $T$: 対流圏遅延
- $I_i$: 周波数 $f_i$ における電離圏遅延
- $\lambda_i$: 波長
- $N_i$: 搬送波整数アンビギュイティ
- $\epsilon$: 観測ノイズやマルチパス

電離圏一次項は周波数の二乗に反比例する。

```math
I_i \propto \frac{\mathrm{STEC}}{f_i^2}
```

## Step 1: Observation Selection

同一衛星・同一時刻に複数の観測コードがある場合、周波数ごとに優先順位を設けて 1 系列に落とす。

例:

- $L1 \leftarrow$ `L1C`, `L1W`, `L1P`
- $L2 \leftarrow$ `L2W`, `L2P`, `L2L`, `L2X`
- $C1 \leftarrow$ `C1C`, `C1W`, `C1P`
- $C2 \leftarrow$ `C2W`, `C2P`, `C2L`, `C2X`

この時点の解析単位は次。

- station
- satellite
- epoch

## Step 2: Geometry-Free Combination

電離圏成分を強調し、幾何距離・時計差・対流圏を落とすために、二周波の geometry-free combination を使う。

搬送波位相の geometry-free は次。

```math
L_{\mathrm{GF}} = \lambda_1 L_1 - \lambda_2 L_2
```

コード観測の geometry-free は次。

```math
P_{\mathrm{GF}} = P_2 - P_1
```

GPS L1/L2 では、

```math
f_1 = 1575.42 \ \mathrm{MHz}
```

```math
f_2 = 1227.60 \ \mathrm{MHz}
```

```math
\lambda_i = \frac{c}{f_i}
```

## Step 3: Convert Geometry-Free to STEC

一次電離圏項の関係から、STEC は geometry-free と比例関係にある。

位相ベースの STEC は次の係数で変換できる。

```math
\mathrm{STEC}_{\Phi}
=
\frac{f_1^2 f_2^2}{40.3 \times 10^{16}(f_1^2 - f_2^2)}
(\lambda_1 L_1 - \lambda_2 L_2)
```

コードベースの STEC は次。

```math
\mathrm{STEC}_{P}
=
\frac{f_1^2 f_2^2}{40.3 \times 10^{16}(f_1^2 - f_2^2)}
(P_2 - P_1)
```

実装上の注意:

- 位相ベース STEC は低ノイズだがアンビギュイティを含む
- コードベース STEC は絶対値に近いがノイズが大きい
- 実用上は code leveling を用いて位相系列を補正する

## Step 4: Cycle Slip Detection and Arc Segmentation

搬送波位相の不連続を含むまま TEC を計算すると破綻するため、cycle slip を検出して arc を分割する。

検出条件の基本形:

```math
\Delta t > t_{\mathrm{gap}}
```

```math
|\Delta L_{\mathrm{GF}}| > \tau_{\mathrm{GF}}
```

```math
\mathrm{LLI} \neq 0
```

ここで:

- $t_{\mathrm{gap}}$: 時刻ギャップ閾値
- $\tau_{\mathrm{GF}}$: geometry-free ジャンプ閾値

この条件で、station-satellite ごとに連続 arc を構成する。

短すぎる arc は除外する。

```math
T_{\mathrm{arc}} < T_{\min} \Rightarrow \text{discard}
```

## Step 5: Code Leveling

位相ベース STEC はアンビギュイティ分だけ定数オフセットを持つので、コードベース STEC に合わせて leveling する。

各 arc に対して、

```math
b_{\mathrm{arc}} = \mathrm{median}\left(\mathrm{STEC}_{P} - \mathrm{STEC}_{\Phi}\right)
```

```math
\mathrm{STEC}_{\mathrm{leveled}}
=
\mathrm{STEC}_{\Phi} + b_{\mathrm{arc}}
```

この結果を地図表示の元になる STEC とする。

## Step 6: Satellite Geometry and Elevation Mask

IPP を計算するために、各観測時刻の衛星位置と受信局位置が必要になる。

必要量:

- station ECEF position
- satellite ECEF position
- azimuth
- elevation

仰角マスクで低仰角データを除く。

```math
E < E_{\min} \Rightarrow \text{discard}
```

MVP では例えば $E_{\min} = 15^\circ$ とする。

## Step 7: Ionospheric Pierce Point

単層電離圏 thin-shell model を仮定し、高度 $H$ の球殻と LOS の交点を IPP とする。

```math
H = 350 \ \mathrm{km}
```

地球半径を $R_E$、受信局での仰角を $E$ とすると、地心角 $\psi$ は次で近似できる。

```math
\sin \psi = \frac{R_E}{R_E + H}\cos E
```

または同値な thin-shell の標準式として、

```math
\psi =
\frac{\pi}{2} - E -
\arcsin\left(\frac{R_E}{R_E + H}\cos E\right)
```

受信局緯度経度と方位角から IPP の緯度経度を計算する。

## Step 8: Mapping STEC to VTEC

STEC は LOS 方向の TEC なので、thin-shell mapping function を使って VTEC に変換する。

```math
M(E) =
\frac{1}{\sqrt{
1 -
\left(
\frac{R_E \cos E}{R_E + H}
\right)^2
}}
```

```math
\mathrm{VTEC} = \frac{\mathrm{STEC}_{\mathrm{leveled}}}{M(E)}
```

## Step 9: Spatial and Temporal Aggregation

表示用には IPP 点群のままでもよいが、安定した可視化と統計のためには格子化する。

MVP の格子例:

- latitude: $20^\circ$ to $50^\circ$
- longitude: $120^\circ$ to $155^\circ$
- grid spacing: $0.5^\circ$
- time step: 5 min, 15 min, or 1 hour

各セルでは例えば以下を保持する。

- mean VTEC
- median VTEC
- mean z-score
- max absolute z-score
- sample count

## Step 10: Baseline and Anomaly Metrics

異常抽出は絶対値表示より、基準差分や標準化の方が有効なことが多い。

### Difference from previous hour

```math
\Delta_{\mathrm{1h}}(t) = \mathrm{VTEC}(t) - \mathrm{VTEC}(t - 1\mathrm{h})
```

### Difference from previous day

```math
\Delta_{\mathrm{24h}}(t) = \mathrm{VTEC}(t) - \mathrm{VTEC}(t - 24\mathrm{h})
```

### Quiet-day baseline

同一 local time に対して、静穏日の中央値を基準とする。

```math
B(t_{\mathrm{LT}}) = \mathrm{median}\left(\mathrm{VTEC}_{\mathrm{quiet}}(t_{\mathrm{LT}})\right)
```

```math
\sigma(t_{\mathrm{LT}}) = \mathrm{std}\left(\mathrm{VTEC}_{\mathrm{quiet}}(t_{\mathrm{LT}})\right)
```

### Z-score

```math
z(t) = \frac{\mathrm{VTEC}(t) - B(t_{\mathrm{LT}})}{\sigma(t_{\mathrm{LT}})}
```

MVP では、この $z$ を地図の主表示量とする。

## Output Data Products

### Intermediate

- `ringo_csv/*.csv`
- `observations/*.wide.parquet`
- `observations/*.long.parquet`
- `observations/*.selected.parquet`

### Processing-stage outputs

今後追加する想定:

- `stec_arcs/*.parquet`
- `ipp_points/*.parquet`
- `tec_grid/*.parquet`

### API-ready outputs

FastAPI が返す軽量 JSON は次のような構造を想定する。

```json
{
  "time": "2026-05-20T00:00:00Z",
  "mode": "z_score",
  "cells": [
    {
      "lat": 37.5,
      "lon": 140.0,
      "value": 2.3,
      "count": 18
    }
  ]
}
```

## Assumptions and Limitations

- 初期実装は GPS 二周波を優先する
- thin-shell model を使うため、電離圏の高度構造は潰れる
- broadcast nav を使う段階では衛星位置精度に限界がある
- code leveling の品質はコード観測ノイズと低仰角データの影響を受ける
- 地震前兆の議論に使うには、space weather や geomagnetic activity との分離が必要

## Implementation Order

1. `ringo rnxcsv` の ingest
2. observation code selection
3. geometry-free combination
4. cycle slip detection
5. arc segmentation
6. code leveling
7. satellite geometry and IPP
8. VTEC conversion
9. gridding
10. baseline and z-score
