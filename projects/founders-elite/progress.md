# 進捗と再開方法

更新：2026-10-17

## 完了

| 段階 | 状態 |
| --- | --- |
| Phase 1 対象企業の確定 | 完了（903社を判定） |
| Phase 2 試験調査 | 完了（`data/pilot_sample.csv`） |
| Phase 3 全対象のデータ収集 | 職歴は完了、学歴は一部（下記） |
| Phase 4 集計・分析 | 完了（analysis.md） |
| Phase 5 比較・検証 | 公庫調査、大学進学率と照合済み |
| Phase 6 動画テーマ | 3案と推奨案、仮台本を作成（未承認） |

## 未完了

- 学歴：20年以内の創業者474人中387人が不明
  - 2016〜2021年上場の創業者で、無作為標本以外の約200人は未検索
- 創業者の氏名が分からない企業：62社
- 業種、IPO時の売上高・営業利益：未取得
- 大学別の卒業者数（出現倍率の計算用）：未取得
- 地方取引所の単独上場：対象外のまま

## 再集計の手順

作業ディレクトリ：`projects/founders-elite/scripts/`
Python：リポジトリ直下の `.venv/bin/python`

1. `fetch_jpx.py`：JPXの上場一覧を取得（`data/jpx_listings.csv`）
2. `fetch_part1.py 2016`：Iの部を取得（`cache/founders-elite/pdf/`）。取得済みは飛ばす
3. `extract_part1.py`：沿革と役員略歴を抽出（`cache/founders-elite/part1_extract.jsonl`）
4. `digest.py <年>`、`fetch_mirror.py <キー>`、`mirror_digest.py <キー>`：判定用の要約を作り、`data/screening.csv` に判定を記録（手作業）
5. `founder_candidates.py`：役員略歴から創業者の取りこぼしを確認
6. `build_founders.py` → `classify_careers.py`：創業者と職歴の表
7. `analyze.py`：`companies.csv`、`founders.csv`、`evidence.csv`、`summary.json`、グラフ
8. `breakdowns.py`：analysis.md 用の追加集計

## 学歴調査の再開方法

1. `data/founders.csv` で `target_20y == "Y"` かつ `education_level == "不明"` の人を抽出する
2. 1人1〜2回検索し、`batch_quote.py` に「founder_id|URL|キーワード」を渡して原文を確認する
3. 原文で確認できたものだけを `data/evidence_manual.tsv` に追記する（形式は既存の行を参照）
4. `analyze.py` と `breakdowns.py` を再実行する

- 無作為標本（`data/edu_sample.csv`）は固定する。標本を作り直すと前後の比較ができなくなる

## 動画「上場した創業者は、何歳で起業したのか」（2026-10-17）

- 完成動画：`output/founders-elite/video/founders_age_career.mp4`（Git管理外、1920×1080、30fps、7分59秒。後半に創業者3人の事例の章）
- 事例の調査：`cases.md`（3人の経歴・起業理由・出典）
- 台本・構成・概要欄：`video/narration.md`、`video/scene_plan.md`、`video/description.md`、字幕 `video/captions.srt`
- 共通ツール：リポジトリ直下の `tools/infographic/`（描画、音声合成、書き出し）

再生成

1. VOICEVOX ENGINE を起動する
   - `models/voicevox/` に公式リリース（voicevox_engine-macos-arm64-0.25.2.vvpp、SHA-256 1ba77670…）を `ditto -x -k` で展開済み
   - `models/voicevox/engine_ditto/run --host 127.0.0.1 --port 50021`
   - リポジトリ直下の `.venv` に `imageio-ffmpeg` と `requests` を入れる
2. `projects/founders-elite/video/` で `python build.py frames`：確認用の静止画（`output/founders-elite/video/frames/`）
3. `python build.py render`：MP4、台本、字幕、読みの確認表（`output/founders-elite/video/yomi_check.md`）
4. テスト：リポジトリ直下で `python -m pytest tools/infographic/tests projects/founders-elite/tests`

- 数値を変えた場合は `scripts/` で再集計してから書き出す。`scenes.py` は集計ファイル間の整合を確認し、合わなければ止まる
- 音声は `build.py` の `BACKEND`（VOICEVOX、春日部つむぎ）。別の音声にする場合は `tools/infographic/tts.py` に `key()` と `synthesize()` を持つクラスを追加して差し替える（Open JTalk 用のクラスも残してある）
