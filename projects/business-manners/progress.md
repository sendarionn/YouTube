# 進捗と再開方法

更新：2026-10-18

## 状態

| 対象 | 状態 | 更新日 |
| --- | --- | --- |
| 研究 | 承認の記録なし（2026-10-21 の制作フロー導入前に制作。旧構成のため研究資料は直下） | 2026-10-21 |
| YouTube | 制作確認待ち（動画は完成、投稿していない） | 2026-10-18 |
| note | 試験生成のみ（研究版の承認がないため本制作ではない。公開・販売しない） | 2026-10-21 |

状態の定義は AGENTS.md「制作状態」。承認を伴う状態はユーザーの指示があった場合だけ変更する

動画の本制作まで完了（2026-10-18）。YouTube への投稿はしていない

- 完成動画：`output/business-manners/video/business_manners.mp4`（Git管理外、1920×1080、60fps、10分49秒）
- 台本：video/narration.md、絵コンテ：video/storyboard.md、字幕：video/captions.srt
- 出典対応表：video/claims.md、素材管理：video/assets.md、概要欄：video/description.md
- 制作・検証記録と再生成の手順：video/production_log.md

## 初回調査の成果物

| 成果物 | ファイル |
| --- | --- |
| 歴史調査レポート | history.md |
| 歴史年表 | timeline.md |
| 個別マナー検証表 | manners_table.md |
| 仮説検証結果 | hypotheses.md |
| 出典一覧 | sources.md |
| 動画構成案 | video_plan.md |
| 調査方法・再集計 | methodology.md |
| 指示書（原文） | brief.md |

## 未完了・未確認（調査）

- 『JALスチュワーデスのいきいきマナー講座』（1989）の本文：国会図書館のデジタル化資料（館内・図書館送信）
- 山口誠『客室乗務員の誕生』（2020）の本文
- 朝日新聞1986.6.7夕刊、1986.8.19夕刊、1989.4.8夕刊、1989.9.23茨城版の原紙面
- 文部省『礼法要項』（1941、『文部時報』720号）にお辞儀の角度の規定があるか
- 名刺交換の作法、お辞儀の15°・30°・45°、エレベーター・タクシーの席次の初出
- 日経連弘報部『職場のエチケット』（1952）の本文（1950年代の職場の作法の内容）
- 倉持益子（2013）は取得済みで未精読

## 再開方法

- 集計の再実行：methodology.md「再集計の手順」
- 取得済みのPDFとAPI応答：`cache/business-manners/`（Git管理外）

## Final Cut Pro 用の書き出し（2026-10-21 追加）

- `video/` で `python build.py export`：`output/business-manners/video/` に final.mp4、project.fcpxml、scenes/、audio/、subtitles.srt、manifest.json
- 一部のシーンだけ直した場合：`python build.py export --only 3,5`
- 撮影候補：`video/shot-list.md`（`scenes.py` の Shot から生成）
- 読み込みと別の Mac への移動：`tools/fcpxml/README.md`
- 従来の `render` の MP4（business_manners.mp4）はそのまま残る。export の final.mp4 とは音量の調整方法（固定の倍率）と色の変換（BT.709）が異なる

## note の試験生成（2026-10-21）

- 第3段階の機能確認のための試験生成。研究版の承認を意味しない
- 設定：`note/config.json`（`mode: trial`）、記録：`note/manifest.public.json`
- 原稿：`private/business-manners/note/`（Git 管理外）、出力：`output/business-manners/note/`
- 再出力：リポジトリ直下で `.venv/bin/python -m tools.note business-manners all`

## 訂正の記録

### 2026-10-21 航空会社・CA関連のマナー本の件数（18点 → 16点）

- 旧記載：hypotheses.md、history.md「18点（0.7%）」。video_plan.md、video/claims.md「0.7%」
- 正：16点（16 / 2,574 = 0.62%、表記は0.6%）。`data/ndl_airline_manner_titles.csv` の16行と一致
- 確認したこと
  - `scripts/airline_titles.py` を取得済みの NDL 応答（`cache/business-manners/ndl/`）で再実行すると16行になり、CSV と完全に一致する
  - 「マナー」の総数2,574点（題名の確認後、1950〜2025年）も `ndl_title_counts.csv` と一致する。ページ送り（500件ずつ）と書誌 URL による重複排除で件数は変わらない
  - 「CA」を単語の境界なしの部分一致で数え、かつ題名に「マナー」を含むかを確認しない条件では、ちょうど18点になる。増える2件は誤検出
    - 『LIFE CAREER：人生100年時代の私らしい働き方』（2019、CAREER の CA に一致。題名に「マナー」を含まない）
    - 映像資料『青春グラフィティ～ねぇお姉さん～』（2008、出版者 PONY CANYON の CA に一致。題名に「マナー」を含まない）
- 原因（推定）：18点は、現在のスクリプト（CA を単語として判定し、題名を確認する）に直す前の集計結果を文書に書いたものと考えられる。当時の実行記録は残っていないため、条件の再現による推定
- 取得時点による差ではない（同じ取得済み応答から両方の値を再現できる）
- 影響：動画は指示によりこの比率を使っていない。note の試験生成も使っていない。配布データ（CSV）は元から16行で、変更なし
- 再発防止：`tests/test_airline_titles.py`（CA の判定と、文書の件数・割合が CSV と一致することの確認）
