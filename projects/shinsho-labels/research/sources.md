# 出典一覧

確認日は記載のないものは 2026-10-23〜24

## データ

| ID | 資料 | 使い方 | 利用条件 |
| --- | --- | --- | --- |
| D1 | 国立国会図書館サーチ OpenSearch API https://ndlsearch.ndl.go.jp/api/opensearch （dpid=iss-ndl-opac、国立国会図書館蔵書） | 書誌（シリーズ名、刊行年、価格、ページ数、NDC、著者） | 国立国会図書館作成の書誌データは利用目的を問わず自由に利用可（https://ndlsearch.ndl.go.jp/help/sitepolicy）、CC BY 互換（https://ndlsearch.ndl.go.jp/help/api/provider）。API を利用したことを明記する |
| D2 | 国立国会図書館サーチ 外部提供インタフェース仕様書 第1.5版（2026-09-25） https://ndlsearch.ndl.go.jp/file/help/api/specifications/ndlsearch_api_20260925.pdf | 1回の検索は500件まで（501件目以降は取得不可） | — |
| D3 | Wikidata SPARQL https://query.wikidata.org/ | 著者の職業（P106）、所属（P108）、生年（P569） | CC0 |
| D4 | 政府統計の総合窓口（e-Stat）「消費者物価指数 2020年基準 長期時系列データ 品目別価格指数 全国 年平均」 https://www.e-stat.go.jp/stat-search/files?page=1&stat_infid=000032103938 | 実質価格の換算（総合） | 政府標準利用規約 第2.0版、CC BY 互換、商用利用可（https://www.e-stat.go.jp/terms-of-use）。出典：政府統計の総合窓口(e-Stat)。年と列を抽出して加工 |
| D5 | トーハン「年間ベストセラー」2016〜2025年（PDF） https://www.tohan.jp/bestsellers/archives/ | 新書ノンフィクション上位10点 | 「トーハン調べ」と明示。営利目的の第三者への二次利用は禁止 → 集計結果だけを使い、表は配布しない |
| D6 | 日販「年間ベストセラー」2024・2025年 https://www.nippan.co.jp/ranking/annual/ | トーハンの結果の確認（参考） | — |

## 候補の発見に使った資料

| ID | 資料 | 使い方 |
| --- | --- | --- |
| W1 | Wikipedia「新書レーベル一覧」（2024-09-09 版） https://ja.wikipedia.org/wiki/新書レーベル一覧 | 候補シリーズの発見だけ。件数・年は D1 で確認 |

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
