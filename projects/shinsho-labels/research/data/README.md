# data/

文字コード UTF-8。集計の手順は `../methodology.md`、結果の解説は `../analysis.md`

| ファイル | 内容 | 作り方 |
| --- | --- | --- |
| label_candidates.csv | 採用したシリーズ137件（判型で除外した朝日文化手帖を含む138行。decision 列で区別）（出版社、区分、分野の焦点、検索語（「|」で複数）、シリーズ名・出版者の正規表現、追加した調査、以前の区分、前身・後継） | 手作業（第一調査・再調査） |
| label_decisions.csv | 候補のシリーズ名すべて（312行、304名）の採否と理由、情報源、書誌の件数の目安 | 手作業（再調査。規則は methodology.md「採否の基準」） |
| series_discovery.csv | 「新書」を含む書誌のシリーズ名ごとの件数（2016〜2025年は毎年、1950〜2010年は10年ごとの標本）と、既存の候補に一致するか | scripts/discover_labels.py |
| wikipedia_labels.csv | Wikipedia「新書レーベル一覧」（版 101785742）の見出し・出版社・シリーズ名 | API で取得した本文を分割 |
| wikipedia_survey.csv | 上の各シリーズ名の書誌の件数、最初の50件でシリーズ名が一致する件数、出版年の範囲 | scripts/survey_wikipedia.py |
| sizes.csv | シリーズごとの書誌の大きさ（cm）の標本（最大20件）、17〜18cm の割合。判型で除外したシリーズも decision 列つきで残す | scripts/sizes.py（SRU） |
| label_survey.csv | 予備調査：検索件数、先頭500件のうちシリーズ名が一致する件数、年の範囲 | scripts/survey_labels.py |
| collect_log.csv | 取得の記録：検索した期間ごとの件数、取りこぼしの可能性 | scripts/collect.py |
| titles.csv | 刊行点数の単位にまとめた書誌（1行1点、45,269点） | scripts/normalize.py |
| normalize_report.csv | まとめる規則ごとの件数（除外・統合） | scripts/normalize.py |
| coverage.csv | シリーズ・時期ごとの点数と最大の番号（網羅の目安） | scripts/analyze.py |
| yearly_counts.csv | シリーズ・年ごとの刊行点数 | scripts/analyze.py |
| summary_labels.csv | 横断比較（2016〜2025年）のシリーズごとの指標。区分で絞らず期間内に1点以上の全シリーズ。first_year・last_year（全期間）、status（2024年以降に刊行があれば current）、active_years（期間内に刊行した年の数）、titles_per_year、compared（100点以上。統計の安定性の目印で、比較への参加条件ではない） | scripts/analyze.py |
| ndc_specialization.csv | シリーズ × NDC 第1次区分：点数、構成比、全シリーズの構成比、特化係数（lq）、年平均点数 | scripts/analyze.py |
| ndc2_specialization.csv | 同じものを綱（NDC 上2桁）で | scripts/analyze.py |
| ndc_by_label.csv | 横断比較の NDC 第1次区分ごとの点数・構成比 | scripts/analyze.py |
| ndc_by_decade.csv | 10年ごとの NDC 構成比 | scripts/analyze.py |
| ndc_stats.csv | 範囲（scope：all／category:区分／between_categories）と分類の細かさ（level：class／division）ごとのクラメールの V、相互情報量、集中度・距離の中央値 | scripts/stats.py |
| ndc_distance.csv | シリーズの組み合わせごとの分野の構成の距離（期間内20点以上）。同じ区分か、同じ出版社か、両方100点以上か（stable） | scripts/stats.py |
| ndc_nearest.csv | シリーズごとに最も近いシリーズ、他との距離の中央値、同じ区分で最も近いシリーズ | scripts/stats.py |
| ndc_v_by_decade.csv | 10年ごとのクラメールの V（全シリーズ・一般向け、その10年に30点以上のシリーズ） | scripts/stats.py |
| price_trend.csv | 5年ごとの価格（本体・名目、実質）とページ数の中央値 | scripts/analyze.py |
| authors.csv | 横断比較の最初の著者と Wikidata の照合結果・区分 | scripts/authors.py |
| author_shares.csv | シリーズごとの著者区分の割合（照合率と上下限つき）。点数の少ないシリーズも出し、stable（100点以上）で区別 | scripts/author_shares.py |
| bestseller_counts.csv | トーハン年間ベストセラー（新書ノンフィクション）上位10点への登場数 | scripts/bestseller_labels.py |
| cpi_annual.csv | 消費者物価指数（全国、年平均、2020年=100）：総合、書籍・他の印刷物など | e-Stat から抽出 |
| image_claims.tsv | ネット上の記述（読者・ブログなど）：出典、日付、引用 | 手作業（ページを読んで記録） |
| publisher_claims.tsv | 出版社・編集者の記述（読者の評価とは別に扱う） | 手作業 |
| image_coded.tsv、image_summary.csv | 記述のカテゴリ分けと、シリーズ×カテゴリの情報源数 | scripts/code_images.py |

## titles.csv の列

| 列 | 意味 | 単位・定義 | 欠損値 |
| --- | --- | --- | --- |
| label | シリーズ名 | label_candidates.csv の名前 | なし |
| category | 区分 | general（一般向け）、science（科学）、junior（ジュニア）、business（ビジネス）、practical（実用）、specialized（分野特化）、selfpub（自費出版・企業出版）、translation（翻訳叢書）。定義は methodology.md | なし |
| era | 時期 | 岩波新書の赤版・青版・黄版・新赤版、角川新書・河出新書の旧シリーズと現行など。それ以外はシリーズ名と同じ | なし |
| series_prefix、series_no | シリーズの記号と番号 | 「岩波新書 新赤版 ; 1706」の 1706 | 番号のない書誌は空欄 |
| numbered | 番号の有無 | 1／0 | なし |
| title、subtitle | 書名、副書名 | 書誌の「 : 」の前と後 | 副書名がなければ空欄 |
| year、month | 刊行年月 | まとめた書誌のうち最も早いもの | 月が不明なら空欄 |
| price_yen | 価格 | 円。書誌の記載のまま | 記載がなければ空欄 |
| price_basis | 価格の区分 | 表示価格（税の記載なし、1989年以降は本体価格とみなす）／税込 | 価格がなければ空欄 |
| pages | 本文のページ数 | 書誌の「209,3p」の 209 | 記載がなければ空欄 |
| extra_pages、extra_pages_position | 別立てのページ数と位置 | 「209,3p」の 3（後）。前付けなら「前」 | なければ 0・空欄 |
| ndc_class、ndc、ndc_edition | NDC 第1次区分、分類記号、版 | NDC10 → NDC9 → NDC8 → 版不明の順に採用 | 分類がなければ空欄 |
| translated | 翻訳 | 責任表示に「訳」を含めば 1 | なし |
| first_creator、first_creator_birth | 最初の著者と生年 | 書誌の dc:creator | 不明なら空欄 |
| n_creators | 著者などの人数 | dc:creator の数 | なし |
| edition | 版の表示 | 書誌の記載 | なければ空欄 |
| isbn、ndl_bibid | ISBN、国立国会図書館書誌ID | 代表の書誌のもの | ISBN がない古い本は空欄 |
| records_merged | まとめた書誌の数 | 重版・複製など | なし |
| author_statement | 責任表示 | 「佐藤卓己 著」など | なし |

## 出典と利用条件

- 書誌：国立国会図書館サーチ（API を利用）。国立国会図書館作成の書誌データ（利用目的を問わず自由に利用可、CC BY 互換）
- 著者の職業：Wikidata（CC0）
- 消費者物価指数：政府統計の総合窓口（e-Stat）「2020年基準消費者物価指数 長期時系列データ 品目別価格指数 全国 年平均」（政府標準利用規約、CC BY 互換）。抽出して年と列を選んだ
- ベストセラー：トーハン調べ。ランキングの表は Git 管理外（cache/）に置き、ここには集計結果だけを置く
- ネット上の記述：引用の範囲で短く記録した
