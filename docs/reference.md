# Reference

## Summary

日本全域の TEC / VTEC を出すとき、既存研究や運用は **IPP をそのまま格子平均する** 方針を取っていない。  
基本方針は、**全 LOS 観測を使って全国格子の VTEC 場を同時推定する** ことである。

このプロジェクトでは、`v0.2` 以降の設計判断のために、以下のソースを参照する。

## References

| Source | URL | Type | What it says | What we take for this project |
| --- | --- | --- | --- | --- |
| Otsuka et al. (2002) | https://link.springer.com/article/10.1186/BF03352422 | Paper | GEONET の 1000 局超を使い、受信機・衛星バイアスを最小二乗で除去した上で、日本上空の絶対 VTEC 2D マップを作成。解像度は 30 秒、0.15° × 0.15°。 | 日本全国の VTEC は、観測点セル平均ではなく、bias を含む推定問題として解くべき。 |
| Ping et al. (2002) | https://link.springer.com/article/10.1186/BF03352450 | Paper | 日本列島上の TEC を 0.5° × 0.5°、10 分格子で表現し、全球 GIM を球面調和関数で高次展開した regional ionosphere map (RIM) を用いる。 | `0.5° / 10 min` の全国格子と、球面調和関数ベースの regional VTEC 推定は現実的な実装候補。 |
| NICT realtime GEONET TEC maps | https://www2.nict.go.jp/spe/gps/REALTIME_GEONET/index_e.html | Official operation | GEONET から 2D TEC, detrended TEC, ROTI, LOL などの realtime マップを運用している。 | Web 表示の最終用途は 2D TEC / detrended TEC / anomaly で十分。まず tomography より 2D 全国面を優先する。 |
| Jin & Miyake (2009) | https://www.nict.go.jp/publication/shuppan/kihou-journal/journal-vol56no1_2_3_4/journal-vol56no1-4_030303.pdf | Paper / NICT report | `TEC = (STEC - B_r - B_s)\cos\chi` の形で receiver / satellite bias を補正して VTEC 化し、数分〜10分オーダーで near-real-time 導出を行う。 | bias 補正を明示的に入れる。`receiver bias`, `satellite bias`, `arc bias` を前処理から独立モジュール化する。 |
| Li et al. (2020) | https://link.springer.com/article/10.1186/s40623-020-1137-0 | Paper | GEONET 向けに PSGM を提案。phase-only で arc bias を推定し、0.1° × 0.1° 格子の VTEC を構築。細かい格子では Kobe 付近でも可用率約 60%、海上では約 15% と報告。 | raw IPP を細格子へ直接置くだけでは全国面は埋まらない。phase-only + arc bias 推定と、補間・正則化が必要。 |
| recent tomography study | https://link.springer.com/article/10.1186/s40623-024-02051-2 | Paper | GEONET 1300 局超に multi-GNSS / 追加網を組み合わせ、3D 電子密度摂動を再構成。 | 3D が必要なら tomography に進めるが、本プロジェクトの MVP は 2D VTEC / anomaly に留める。 |
| recent tomography study | https://link.springer.com/article/10.1186/s40623-018-0815-7 | Paper | 30 秒間隔・高密度 GNSS 網を使った 3D 電離圏トモグラフィーを実施。 | 3D 化は後段テーマ。まず 2D 全国場推定を安定化させる。 |
| GEONET official info | https://web1.gsi.go.jp/ENGLISH/geonet_english.html | Official | GEONET は日本全国 1300 局超、平均約 20 km 間隔、RINEX 30 秒観測で構成される。 | データ密度自体は全国場推定に十分。今の疎さは観測網不足ではなく、推定法不足が主因。 |

## Design conclusion

| Topic | Decision |
| --- | --- |
| Final target | `IPP -> cell aggregate` を最終成果物にしない。 |
| Core method | 全国格子 VTEC を unknown にして、全 LOS 観測から最小二乗で同時推定する。 |
| Grid candidate | `0.5° × 0.5°`, `10 min` を第一候補とする。 |
| Required preprocessing | multi-GNSS, quality control, bias / DCB / arc bias estimation を追加する。 |
| Spatial completion | 海上や欠測部は球面調和関数, B-spline, 背景 GIM/IRI + 残差補正で補う。 |
| Time handling | 時間方向の正則化を入れる。 |
| Anomaly product | quiet-day baseline と detrended TEC / z-score を併用する。 |
| 3D tomography | `v0.2` の主対象ではない。必要になったら別段で進める。 |

## Recommended v0.2 direction

| Step | Recommendation |
| --- | --- |
| 1 | multi-GNSS 対応 |
| 2 | STEC 生成の品質管理強化 |
| 3 | receiver / satellite / arc bias 推定 |
| 4 | 全国格子を unknown にした正則化付き最小二乗推定 |
| 5 | quiet-day baseline と detrended TEC の生成 |

## Practical recommendation

このプロジェクトでは、**Otsuka 2002 + Ping 2002 + Li 2020 の折衷**を採るのが現実的である。

具体的には次を推奨する。

- `0.5° × 0.5°`
- `10 min`
- multi-GNSS
- bias / arc bias 推定
- 全国格子 VTEC を unknown にした regularized least squares
- quiet-day baseline による anomaly 生成
