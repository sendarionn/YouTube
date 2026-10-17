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
