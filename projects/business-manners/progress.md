# 進捗と再開方法

更新：2026-10-18

## 状態

| 対象 | 状態 | 更新日 |
| --- | --- | --- |
| 研究 | 承認の記録なし（2026-10-21 の制作フロー導入前に制作。旧構成のため研究資料は直下） | 2026-10-21 |
| YouTube | 制作確認待ち（動画は完成、投稿していない） | 2026-10-18 |
| note | 未着手 | 2026-10-21 |

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
