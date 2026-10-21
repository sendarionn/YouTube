# tools/note

承認済みの研究資料から、note の記事（無料・有料）と販売資料を作る。YouTube の台本・動画は使わず、動画の書き出しも実行しない
note へのログイン、投稿、価格設定、販売開始はしない

## 使い方

リポジトリ直下で実行する

```sh
.venv/bin/python -m tools.note <slug> article   # 記事と図表（原稿を直した場合はこれだけ）
.venv/bin/python -m tools.note <slug> package   # 詳細レポート、データ、出典一覧、販売用 ZIP（再パッケージだけ）
.venv/bin/python -m tools.note <slug> check     # 品質確認、publication-checklist.md、manifest
.venv/bin/python -m tools.note <slug> all       # 上の3つを順に実行
```

| 場所 | 内容 | Git |
| --- | --- | --- |
| `projects/<slug>/note/config.json` | 設定（下記） | 管理する |
| `projects/<slug>/note/manifest.public.json` | 研究版、研究資料・出力のハッシュ、使った ID、確認結果。本文は含めない | 管理する |
| `private/<slug>/note/article.md` | 記事の原稿（有料部分を含む）。保存先は `NOTE_PRIVATE_DIR` で変更できる | 除外 |
| `private/<slug>/note/report.md` | 詳細レポートの原稿（必要な場合のみ） | 除外 |
| `output/<slug>/note/` | 出力一式 | 除外 |

## 出力

```text
output/<slug>/note/
  article-free.md / .html   無料部分（.html はブラウザで開いて note に貼り付ける）
  article-paid.md / .html   有料部分（原稿に境界がある場合のみ）
  article-full.md           確認用（無料＋境界＋有料）
  assets/chart-NNN.png      図表（研究資料のデータから描く）
  report.md / report.pdf    詳細レポート（config の report、pdf）
  data/*.csv、data/README.md  配布するデータとデータ辞書
  sources.md                出典一覧
  delivery/<name>.zip       販売用 ZIP（README.txt、レポート、データ、出典）
  publication-checklist.md  転載の手順、図表と添付の位置、有料ラインの位置、確認項目
  manifest.json             生成の記録（使った数値・出典・主張と、その区分）
```

## 原稿の記法

| 記法 | 意味 |
| --- | --- |
| `{{n:キー}}` | 数値。config の `numbers` で研究資料のファイル（JSON のパス、CSV の行と列、合計、件数、他の数値からの計算）を指定する |
| `{{t:25歳以下}}` | 定義や区分の境界として書く数値。集計値ではないことを示す |
| `{{s:S03}}`、`{{s:S03,S06}}` | 出典の短い表記。末尾の出典一覧に加える |
| `{{fig:chart-001}}` | 図表 |
| `{{link:YOUTUBE_URL}}` | 相互リンク。config の `links` が null の間は `{{YOUTUBE_URL}}` のまま出る |
| `{{attach:name.zip}}` | 添付ファイルの位置 |
| `<!--C:C01-->` | 直前の文の根拠（config の `claims`）。出力では消える |
| `<!-- paid -->` | ここから有料（1回だけ。なければ無料記事だけ） |

- 単位つきの数値（%、人、歳、冊、点、社、件、倍）を直接書くと、check で指摘する
- note の本文は表に対応しないため、記事の原稿で表を使うと指摘する（詳細レポートでは使ってよい）

## config.json

| キー | 内容 |
| --- | --- |
| `mode` | `trial`（試験生成。研究の承認とみなさない）か `production`（`progress.md` の「研究版」表に `research_version` がある場合だけ実行できる） |
| `research_root` | 研究資料のディレクトリ（新しい構成は `research`、旧構成は `.`）。`video/` は参照できない |
| `numbers`、`sources`、`claims`、`figures` | 数値、出典、主張と根拠、図表の定義 |
| `datasets` | 配布データ。`rights.status` が `ok` のものだけ配布し、それ以外（`unverified`、`personal` など）は出典のリンクだけ残す |
| `report`、`pdf` | 詳細レポートの原稿の名前（不要なら null）と PDF の要否 |
| `delivery` | 販売用 ZIP の名前（不要なら省く） |
| `max_attachment_mb` | 添付の上限（既定 50MB。note の上限の変更に合わせて直す） |

## 検証の範囲

- 自動：研究資料だけを参照していること、数値の直書き、無料・有料の分離、有料部分の文章が Git 管理のファイルにないこと、出力と原稿の保存先が Git 管理外であること、データ辞書と CSV の一致、ZIP の展開と中身、配布しないデータが ZIP にないこと、添付の容量
- 手動（`publication-checklist.md`）：note の編集画面での表示、有料ラインの位置、添付のアップロードとダウンロード、価格と区分、公開の許可
