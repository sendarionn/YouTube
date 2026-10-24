# 出典一覧

確認日は記載のないものは 2026-10-23〜25（再調査で追加したものは 2026-10-25）

## データ

| ID | 資料 | 使い方 | 利用条件 |
| --- | --- | --- | --- |
| D1 | 国立国会図書館サーチ OpenSearch API https://ndlsearch.ndl.go.jp/api/opensearch （dpid=iss-ndl-opac、国立国会図書館蔵書） | 書誌（シリーズ名、刊行年、価格、ページ数、NDC、著者） | 国立国会図書館作成の書誌データは利用目的を問わず自由に利用可（https://ndlsearch.ndl.go.jp/help/sitepolicy）、CC BY 互換（https://ndlsearch.ndl.go.jp/help/api/provider）。API を利用したことを明記する |
| D2 | 国立国会図書館サーチ 外部提供インタフェース仕様書 第1.5版（2026-09-25） https://ndlsearch.ndl.go.jp/file/help/api/specifications/ndlsearch_api_20260925.pdf | 1回の検索は500件まで（501件目以降は取得不可） | — |
| D3 | Wikidata SPARQL https://query.wikidata.org/ | 著者の職業（P106）、所属（P108）、生年（P569） | CC0 |
| D4 | 政府統計の総合窓口（e-Stat）「消費者物価指数 2020年基準 長期時系列データ 品目別価格指数 全国 年平均」 https://www.e-stat.go.jp/stat-search/files?page=1&stat_infid=000032103938 | 実質価格の換算（総合） | 政府標準利用規約 第2.0版、CC BY 互換、商用利用可（https://www.e-stat.go.jp/terms-of-use）。出典：政府統計の総合窓口(e-Stat)。年と列を抽出して加工 |
| D5 | トーハン「年間ベストセラー」2016〜2025年（PDF） https://www.tohan.jp/bestsellers/archives/ | 新書ノンフィクション上位10点 | 「トーハン調べ」と明示。営利目的の第三者への二次利用は禁止 → 集計結果だけを使い、表は配布しない |
| D6 | 日販「年間ベストセラー」2024・2025年 https://www.nippan.co.jp/ranking/annual/ | トーハンの結果の確認（参考） | — |
| D7 | 国立国会図書館サーチ SRU https://ndlsearch.ndl.go.jp/api/sru （recordSchema=dcndl） | 書誌の大きさ（cm）の標本（判型の確認、data/sizes.csv） | D1 と同じ |
| D8 | 国立国会図書館サーチ OpenSearch（title=新書、2016〜2025年は毎年、1950〜2010年は10年ごと） | 候補のシリーズ名の発見（data/series_discovery.csv） | D1 と同じ |

## 候補の発見に使った資料

| ID | 資料 | 使い方 |
| --- | --- | --- |
| W1 | Wikipedia「新書レーベル一覧」（版 101785742、2024-09-09） https://ja.wikipedia.org/wiki/新書レーベル一覧 。MediaWiki API で本文を取得 | 候補シリーズの発見だけ。再調査で全249名を D1 で確認（data/wikipedia_labels.csv、wikipedia_survey.csv）。件数・年は D1 で確認 |

## 先行コンテンツ

| ID | 資料 | 確認結果 |
| --- | --- | --- |
| A1 | note「新書レーベルを図解してみた ver.1」2025-12-15 https://note.com/tnsmgg/n/n75fa28cfc5db | 印象による図。データなし |
| A2 | 不眠の子守唄「徹底解説！新書のレーベルごとの特徴まとめ」2021-10-17 https://moriishi.com/entry/shinsho-manual/ | 印象。8レーベル |
| A3 | 出版科学研究所「08年の新書刊行状況は」 https://shuppankagaku.com/column/20090501/ | メンテナンス中で未読 |
| A4 | YouTube 三宅書店 https://www.youtube.com/watch?v=9Wa52vTHVaY | 題名のみ確認、内容未確認 |

## ネット上のイメージ（data/image_claims.tsv）

| ID | 資料 | 日付 | 媒体 |
| --- | --- | --- | --- |
| Q1 | Yahoo!知恵袋「新書を読んで見識を広げようかと…」 https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q12134799642 | 2014-08-29 | Q&A |
| N1 | note「個人的新書レーベルイメージ」 https://note.com/right_sorrel5875/n/n9f7ad043aa62 | 2025-09-30 | note |
| E1 | note「新書レーベルを、リベラル→保守に並べてみる」 https://note.com/essere/n/n86f0c17ebef6 | 2025-07-01 | note |
| M1 | 不眠の子守唄「徹底解説！新書のレーベルごとの特徴まとめ」（A2） | 2021-10-17 | ブログ |
| M2 | 不眠の子守唄「新書デザイン考」 https://moriishi.com/entry/shinsho-design/ | 2020-03-23 | ブログ |
| B1 | Bibroom「教養を深める新書レーベル15選」 https://bibroom.com/shinsho-recommended/ | 2025-10-30 | ブログ |
| T1 | tesukoume「『新書』とは？」 https://tesukoume.com/what-is-shinsho/ | 2023-07-31 | ブログ |
| C1 | 自費出版比較ナビ「新書出版社の特徴や違いを比較してみた」 https://jihishuppan-hikaku-navi.com/ | 2024-03-29 | 比較サイト（自費出版の宣伝を含む） |
| K1 | 猫の手ゼミナール「大学生の読書〜新書のすすめ」 https://nekonotezemi.com/column/no1011d/ | 2019-01-27 | 企業のコラム |
| F1 | note「新書で人類の知の世界を観光する方法」 https://note.com/fujimuradaisuke/n/n4bc9e58a3fa0 | 2022-07-12 | note |
| S1 | note「sakurabarの新書100選（2024年度版）」 https://note.com/sakurabar/n/n7dc7dd625268 | 2024-08-02 | note |

読めなかったもの：Quora の質問（403）、note（kouunnohuehuki、404）、Seesaa ブログ（文字化け）

## 出版社・編集者の記述（data/publisher_claims.tsv）

| ID | 資料 | 日付 |
| --- | --- | --- |
| P1 | 新潮新書 編集長便り「『新書らしい』って何？」 https://www.shinchosha.co.jp/shinsho/henshucho/2008/200803.html | 2008-03 |
| P2 | 新潮新書 編集長便り「90冊と1748冊」 https://www.shinchosha.co.jp/shinsho/henshucho/2004/200410.html | 2004-10 |
| P3 | Real Sound「岩波新書 × 中公新書 × ブルーバックス 鼎談」 https://realsound.jp/book/2025/07/post-2089181.html | 2025-07-19 |
| P4 | ほぼ日「特集 編集とは何か。08 中公新書 前編集長 白戸直人さん」 https://www.1101.com/n/s/14editors/naohito_shirato/2021-09-29.html | 2021-09-29 |
| P5 | 講談社「レーベル一覧」 https://www.kodansha.co.jp/book/labels （講談社現代新書、ブルーバックス、講談社+α新書、星海社新書） | 確認 2026-10-25 |
| P6 | 講談社 現代ビジネス「現代新書」 https://gendai.media/gendai-shinsho | 確認 2026-10-25 |
| P7 | 講談社「ブルーバックス」 https://bluebacks.kodansha.co.jp/ | 確認 2026-10-25 |
| P8 | 筑摩書房「ちくま新書」 https://www.chikumashobo.co.jp/chikuma_shinsho/ | 確認 2026-10-25 |
| P9 | 筑摩書房「ちくまプリマー新書」 https://chikumashobo.co.jp/chikuma_primer_shinsho/ | 確認 2026-10-25 |
| P10 | 岩波書店「岩波ジュニア新書」 https://www.iwanami.co.jp/jr/ | 確認 2026-10-25 |
| P11 | 交通新聞社「交通新聞社新書」 https://www.kotsu.co.jp/products/shinsho/ | 確認 2026-10-25 |
| P12 | 文藝春秋BOOKS「おかげさまで1000点を超えました！ 文春新書、本日発売」 https://books.bunshun.jp/articles/-/167 | 確認 2026-10-25。記事中の創刊年「1988年」は国立国会図書館の書誌（1998年創刊）と食い違う |
| P13 | 岩波書店「岩波新書 新赤版2000点突破！」 https://www.iwanami.co.jp/news/n55235.html | 確認 2026-10-25 |

公式サイトで説明を確認できなかったもの（2026-10-25）：岩波新書（シリーズの紹介ページなし）、中公新書（新刊一覧のみ）、新潮新書・集英社新書・光文社新書・ポプラ新書（説明文なし）、PHP新書（一覧ページの説明は確認できず）、SBクリエイティブ（サイエンス・アイ新書のページは 503）、山と溪谷社（ヤマケイ新書の説明文なし）、イースト・プレス（イースト新書・Q の説明文なし）

## 再調査で行った検索（2026-10-25）

分野特化・実用・科学のシリーズについての読者のイメージを探した。読者の評価を述べた記述は見つからなかった（書店・通販の商品ページ、出版社の新刊情報が中心）

- 「ブルーバックス 新書 イメージ 難しい 理系 読者 感想 レーベル」：読書メーターの書誌ページが中心で、感想の本文は取得できなかった
- 「サイエンス・アイ新書 ブルーバックス 違い 比較」：結果なし
- 「岩波ジュニア新書 ちくまプリマー新書 大人が読む 違い」：学校図書館のお知らせ（PDF）が中心。どちらがどの特徴かを判別できる記述はなかった
- 「交通新聞社新書 鉄道 新書 おすすめ レーベル 特徴」：書店・通販の商品ページが中心
- 「イースト新書Q 創刊 イースト・プレス 新書 コンセプト」「SBビジュアル新書 SBクリエイティブ 創刊 フルカラー」「ヤマケイ新書 創刊 山と溪谷社 シリーズ 紹介」：レーベルの説明は見つからなかった
