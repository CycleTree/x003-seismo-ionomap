# GSI SFTP Data Notes

## Purpose

このメモは、国土地理院 `terras.gsi.go.jp` の SFTP 配信データについて、このプロジェクトで必要な情報だけを抜き出したものです。

対象は主に次です。

- 電子基準点観測データ
- 電子基準点以外の観測データ
- IGS 精密暦
- 10分データの注意事項

## SFTP Access

- Host: `terras.gsi.go.jp`
- Port: `22`
- Protocol: `SFTP`

注意:

- SFTP のユーザ名・パスワードは、GSI の SFTP ユーザ登録で設定したものを使う
- 共通ログインサービスの認証情報とは別

Linux では `sftp` コマンドで接続できる。

## Observation Filename Rules

電子基準点観測データの基本ファイル名規則:

```text
ssssddd?.yyo   observation data
ssssddd?.yyn   GPS navigation
ssssddd?.yyq   QZSS navigation
ssssddd?.yyg   GLONASS navigation
ssssddd?.yyl   Galileo navigation
ssssddd?.yyd   compressed observation data
```

意味:

- `ssss`: 観測局番号または名称
- `ddd`: 年内通算日
- `yy`: 西暦下2桁
- `?`: セッション番号

補足:

- 電子基準点の `ssss` は、6桁局番号の下4桁
- ファイルは gzip 圧縮
- このプロジェクトでよく使う `*.26d.gz` は圧縮観測ファイル
- このプロジェクトでよく使う `*.26N.tar.gz` は GPS ナビ関連アーカイブ

## Main Directory Structure

電子基準点観測データは次の系統に保存される。

```text
/data/G_2.11
/data/GR_2.11
/data/GRJ_2.12
/data/GRJE_2.12
/data/GRJE_3.02
```

補足:

- さらに `YEAR/DOY` 単位の下位ディレクトリに格納
- `GRJE_3.02` は GPS, GLONASS, QZSS, Galileo を含む
- 今後 multi-station / multi-GNSS 対応を進めるなら、この階層を前提に収集するのが自然

## 10-Minute Data

試験配信の 10分観測データは次に保存される。

```text
/data/EXT_data/10min/(YEAR)/(DOY)/(sess)
```

セッションフォルダ例:

- `a00`: UTC 00:00 台
- `a10`: UTC 00:10 台
- ...
- `x50`: UTC 23:50 台

重要な注意:

- 速報性重視
- 欠測や通信断があってもリカバリーしない
- 3日より前のデータは順次削除
- 2023年12月26日に、配信間隔が 5分ごとから 10分ごとへ変更

このプロジェクトでは、全国を安定して再処理する用途にはまず通常の 1日または 1時間データを優先し、10分データはリアルタイム寄り用途として別扱いにするのが妥当。

## External Observation Data

電子基準点以外の GNSS 観測点は次に格納される。

```text
/data/EXT_data/GRJE_3.02
/data/EXT_data/GRJE_2.11
/data/EXT_data/GR_2.11
/data/EXT_data/G_2.11
```

補足:

- さらに `YEAR/DOY` 単位の下位ディレクトリに格納
- 観測点ごとの機器性能差で、観測衛星系が異なる
- 観測データが無い点や欠測がある場合がある

民間等電子基準点について:

- 観測ファイル名の先頭が `C` のものが該当

## IGS Precise Ephemeris

ファイル名規則:

```text
igswwwwd.sp3
```

意味:

- `wwww`: GPS week
- `d`: 曜日 (`0` = Sunday, ..., `6` = Saturday)

格納先:

```text
/data/IGS_products
```

補足:

- さらに GPS week ごとの下位ディレクトリに格納
- 将来的に broadcast nav ではなく precise orbit を使う場合は、この系統を参照する

## Daily Coordinates

電子基準点日々の座標値ファイル名規則:

```text
nnnnn[n].yy.pos
```

格納先:

```text
/data/coordinates_F5/GPS
/data/coordinates_R5/GPS
```

補足:

- `coordinates_F5/GPS` が現行の F5 解
- 年ごとの下位ディレクトリに格納

## Tropospheric Delay Products

ファイル名規則:

```text
F5**Gyyyydoynnnn.TRP.gz
```

格納先:

```text
/data/trp_F5/GPS
```

補足:

- 年・通算日ごとの下位ディレクトリに格納
- 必要になれば将来、TEC 異常と気象・対流圏との切り分け補助に利用できる

## Project Relevance

このプロジェクトでまず重要なのは次の 3 点。

1. 複数観測局の観測ファイル `*.yyd.gz`
2. 対応するナビファイル `*.yyn` 系
3. 将来的な高精度化のための `IGS_products/*.sp3`

現時点では、手元の `data/140` に多数の観測局データと対応 nav が存在するため、全国カバレッジ化のための素材としては十分ある。
