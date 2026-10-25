# 進捗と再開方法

更新：2026-10-26

## 状態

| 対象 | 状態 | 更新日 |
| --- | --- | --- |
| 研究 | 研究版 research-v1（追加検証を反映。下の「研究版」） | 2026-10-25 |
| YouTube | 制作確認待ち（動画 v1、8分29秒。research-v1 に基づく。output/japan-center/video/final.mp4・project.fcpxml。制作レポート video/production_log.md） | 2026-10-26 |
| note | 未着手 | |

状態の定義と変更の規則は AGENTS.md「制作状態」。承認を伴う状態はユーザーの指示があった場合だけ変更する

## 承認の記録

| 日付 | 対象 | 内容（ユーザーの指示の要旨） |
| --- | --- | --- |
| 2026-10-25 | 調査の開始 | 調査・制作指示書（brief.md）を受け取り「下記の指示書で進めつつ、音声はVoiceboxで一旦作って」と指示。指示書9〜11章により、今回は調査・分析・構成提案まで（動画のレンダリング・FCPXML・note・投稿はしない） |

## 制作方針（ユーザーの指示）

- ナレーションの声：この動画は VOICEVOX（春日部つむぎ、`voicevox`）で作る。2026-10-25 の指示「音声はVoiceboxで一旦作って」と、制作指示書 8章（voicevox を標準とする）による。動画 v1 は voicevox で制作した（video/build.py の VOICE）

## 研究版

| 版 | 承認日 | コミット | 範囲 |
| --- | --- | --- | --- |
| research-v1 | 2026-10-25 | f573f01 ＋ 追加検証（未コミット） | research/ の全体（97件の中心、analysis.md 10〜12章の追加検証、data/verify_*、video_selection.csv）。制作指示書が追加検証の後に動画制作へ進むよう指示したため、追加検証を反映した版を動画 v1 の研究版とする |

## 研究版の変更による影響

承認後に研究資料を変更した場合、影響する媒体・主張・図表・添付データを列挙する

## 公開

| 媒体 | 公開日 | URL |
| --- | --- | --- |

## 未完了・未確認

一覧は research/unresolved.md。主なもの
- 企業本社・消費支出・データセンター・通信網・出版／映画／音楽・伝統文化・河川網・活火山の中心：未計算（データ不足または定義が必要）
- 全国への平均移動時間が最短の地点：距離で代用（所要時間は未計算）
- 歴代の都の年代（通説）と位置（町名の代表点）：一次資料は未確認
- 2025年の人口重心：推計のみ（統計局の公表待ち）
- 航空貨物の指標の定義、延べ宿泊者数（2025年）が速報か確定か：未確認
- 地図（output/japan-center/research/centers_map.html）：ヘッドレスの Chrome で、全体表示と、点を選んだ状態（URL の # で指定）・拡大表示を画像で確認。マウスのドラッグ・ホイール操作は未確認
- 動画 v1：Final Cut Pro での読み込み（字幕クリップを含む）、通しの視聴・聴取、サムネイルは未確認・未作成（video/production_log.md）

## 再開方法

- 全工程の再実行：research/methodology.md「再実行」
- 元データは cache/japan-center/（Git 管理外）。統計ダッシュボードと国土地理院 API の応答も保存済みで、再実行は保存済みを使う
- 地図の再生成：`research/charts/map.py`
- 検証：`.venv/bin/python -m pytest -q projects/japan-center/research/tests`
- 動画の再生成：VOICEVOX ENGINE を起動し（`models/voicevox/engine_ditto/run --host 127.0.0.1 --port 50021`）、`video/build.py export`（音声は cache/tts を使う。`--only N` でシーンだけ描き直す）。品質確認は `video/qa.py`、読みの確認は `models/gpt-sovits/.venv/bin/python video/asr_lines.py`
- 地図の形のキャッシュ（cache/japan-center/video/geom.pkl）がない場合は `video/mapdraw.py` で作り直す
