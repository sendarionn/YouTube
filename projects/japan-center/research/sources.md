# 出典

確認日はすべて 2026-10-25（URL を開いて記載内容を確認した日）
ID は `data/centers.csv` の source 列で使う

## 一次資料・公的統計

| ID | 資料 | 発行元 | URL | 対象 | 使った内容 |
| --- | --- | --- | --- | --- | --- |
| stat_topics135 | 統計トピックス No.135「我が国の人口重心 −令和2年国勢調査結果から−」（2023-01-17）、参考資料「各都道府県及び市区町村の人口重心（10進数）」（topics135_10.xlsx） | 総務省統計局 | https://www.stat.go.jp/data/kokusei/topics/topi135.html | 2020年10月1日 | 全国の人口重心（公表値）、1965〜2020年の推移、算出式、都道府県・市区町村の人口重心（代表点として使用） |
| stat_topics61 | 統計トピックス No.61「我が国の人口重心 −平成22年国勢調査結果から−」（topi6101.pdf） | 総務省統計局 | https://www.stat.go.jp/data/kokusei/topics/pdf/topi6101.pdf | 2010年 | 2005・2010年の人口重心の秒の値（No.135 の PDF の表は秒の値の配置が崩れて読めないため） |
| estat_census2020 | 令和2年国勢調査「都道府県・市区町村別の主な結果」（major_results_2020.xlsx） | 総務省統計局（e-Stat） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032143614&fileKind=0 | 2020年10月1日 | 市区町村別の人口、年齢別人口、外国人、世帯、産業別就業者（常住地）、昼間人口 |
| estat_census2025 | 令和7年国勢調査「都道府県・市区町村別の主な結果」（major_results_2025.xlsx） | 総務省統計局（e-Stat） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040507382&fileKind=0 | 2025年10月1日 | 市区町村別の人口（2025年の人口重心の推計に使用） |
| dashboard | 統計ダッシュボード API（getData） | 総務省統計局 | https://dashboard.e-stat.go.jp/api/1.0/Json/getData | 指標ごと（data/indicators.csv の time 列） | 31指標の都道府県・市区町村別の値。指標コードは `dashboard:<コード>` で記録。元の統計は社会・人口統計体系、県民経済計算、経済センサス、宿泊旅行統計調査、医療施設調査など |
| gsi_globalmap | 地球地図日本 第2.2版（gm-jpn-all_u_2_2.zip、1:100万、2016年） | 国土地理院 | https://www.gsi.go.jp/kankyochiri/gm_jpn.html | 2016年 | 陸地（市区町村の面）、海岸線、高速道路（rtt=16） |
| gsi_extremes | 日本の東西南北端点の経度緯度（2019-06-01 に最東端・最西端を更新） | 国土地理院 | https://www.gsi.go.jp/KOKUJYOHO/center.htm | 2019年 | 東西南北端の座標 |
| gsi_datum | 日本の測地基準点（日本経緯度原点・日本水準原点） | 国土地理院 | https://www.gsi.go.jp/sokuchikijun/datum-main.html | 現行値 | 経緯度原点の座標、水準原点の所在地と数値、測量法施行令第2条 |
| gsi_geocoder | 住所検索 API・逆ジオコーダー API | 国土地理院 | https://msearch.gsi.go.jp/address-search/AddressSearch 、https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress | 2026年 | 住所から代表点、座標から市区町村・町字（陸上・海上の判定） |
| ksj_n02 | 国土数値情報 鉄道データ N02-24 | 国土交通省 | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-2024.html | 2024年12月31日時点 | 線路の区間と駅（鉄道網の中心） |
| egov_shutoken | 首都圏整備法（昭和31年法律第83号）第1条・第2条 | e-Gov 法令検索（API v2） | https://laws.e-gov.go.jp/law/331AC0000000083 | 現行 | 第1条「わが国の政治、経済、文化等の中心としてふさわしい首都圏」、第2条 首都圏の定義 |
| egov_stdtime | 明治十九年勅令第五十一号（本初子午線経度計算方及標準時ノ件） | e-Gov 法令検索（API v2） | https://laws.e-gov.go.jp/law/119IO0000000051 | 現行 | 標準時の基準の経線（東経135度）。法令名と ID を API で確認 |
| mlit_nihonbashi | 観光社会資本の事例「日本の道路の起点『道路元標』が埋設されている重要文化財『日本橋』」 | 国土交通省（関東地方整備局 東京国道事務所） | https://www.mlit.go.jp/sogoseisaku/region/kankosyakaisihon/83/1304.pdf | — | 1972年に日本国道路元標を埋設、「日本の道路の原点」 |
| usgs_comcat | ANSS Comprehensive Earthquake Catalog（FDSN event API） | 米国地質調査所（USGS） | https://earthquake.usgs.gov/fdsnws/event/1/ | 1996-01-01〜2025-12-31、M5.0以上 | 震央の位置。クエリは scripts/other_centers.py の USGS |
| npb_stadium | 12球団本拠地球場、球場詳細（stadium/json/<ID>.json の address） | 日本野球機構（NPB） | https://npb.jp/stadium/franchise.html | 2026年 | 本拠地球場と住所 |

## 自治体の公表

| ID | 資料 | URL | 使った内容 |
| --- | --- | --- | --- |
| nishiwaki_heso | 西脇市観光物産協会「日本へそ公園」、西脇市「日本へそ公園概要」 | https://www.nishiwaki-kanko.jp/guide/sightseeing/nihonhesokoen.html 、https://www.city.nishiwaki.lg.jp/kakukanogoannai/kensetsusuidoubu/shisetukanrika/park_sightseeing/heso_park/1355360123022.html | 東経135度・北緯35度の交点、大正のへそ・平成のへそ |
| tatsuno_zero | 辰野町「日本の地理的中心 ゼロポイント」 | https://www.town.tatsuno.lg.jp/gyosei/soshiki/sangyoshinkoka/kankosite/4/7/1175.html | 北緯36度・東経138度、2011年1月の標柱 |
| tatsuno_chiko | 辰野町「日本の中心の中心 チコちゃんポイント」（2023-11-13 更新） | https://www.town.tatsuno.lg.jp/gyosei/soshiki/sangyoshinkoka/kankosite/4/7/1176.html | 28自治体の平均、北緯35度59分56秒・東経137度59分56秒、2018年秋 |
| shibukawa_mannaka | 渋川市「『へそのまち』日本のまんなか渋川市」（2025-11-30 更新） | https://www.city.shibukawa.lg.jp/shisei/000233/000234/p007509.html | 宗谷岬と佐多岬を円で結んだ中心、臍石の伝説、全国へそのまち協議会の設立 |
| heso_council | 渋川市「全国へそのまち協議会」（2026-09-02 更新） | https://www.city.shibukawa.lg.jp/shisei/000233/000239/p003337.html | 加盟9市町村とそれぞれの「へそ」の表現 |
| sano_heso | 佐野市「佐野市の歩み」（2025-02-14 更新） | https://www.city.sano.lg.jp/soshikiichiran/sougou/toshibrandsuishin/gyomuannai/koho/5/4738.html | 「平成10年 日本列島の中心点を作原に設置」（旧田沼町） |
| chuo_mannaka | 中央市「全国へそのまち協議会」 | https://www.city.chuo.yamanashi.jp/soshiki/kikaku/kikakusoumu/hesonomati/index.html | 2018年9月に「日本の真ん中 人が真ん中」として加盟。根拠の記述は検索結果の要約で確認（本文の地理的根拠の記述は見つからない） |
| saku_umikara | 佐久市「日本で海岸線から一番遠い地点」（2026-06-01 更新） | https://www.city.saku.nagano.jp/kanko/kanko/spot/nature/umikaratoi.html | 1996年に国土地理院が特定、約115km、雨川ダムの南東約2,200m |

## 歴史の年代（追加検証で確認）

| ID | 資料 | URL | 使った内容 |
| --- | --- | --- | --- |
| nara_heijo | 奈良県「天平文化のど真ん中『平城京』」、奈良文化財研究所の特別展案内 | https://www.pref.nara.jp/miryoku/aruku/kikimanyo/column/c03/ 、https://www.nabunken.go.jp/news/2026/06/20260626press.html | 710年（和銅3年）、元明天皇が平城の地に都を移した。784年に長岡京へ |
| kyoto_heian | 京都市「京都の歴史年表 都市のすがた」 | https://www2.city.kyoto.lg.jp/somu/rekishi/fm/nenpyou/toshi_nenpyo.html | 延暦13年（794年）10月に桓武天皇が新京へ移り、遷都の詔 |
| archives_tokyo | 国立公文書館「変貌 5.江戸城を皇居と定め東京城と改称」「8.明治天皇、東京へ再び行幸」 | https://www.archives.go.jp/exhibition/digital/henbou/contents/05.html 、https://www.archives.go.jp/exhibition/digital/henbou/contents/08.html | 明治元年（1868年）10月に江戸城を皇居と定め東京城と改称、明治2年（1869年）に再幸し太政官が移る |

- 確認は検索結果に示された公的機関のページの記載による（2026-10-25）。本文は要約で確認した

## 通説（一次資料を確認していない）

| ID | 内容 | 扱い |
| --- | --- | --- |
| tsusetsu | 歴代の宮・都・幕府の年代と所在地（飛鳥〜江戸）のうち、上の3つ以外 | 年代は日本史の通説（動画では示さない）。宮跡の位置は国土地理院の住所検索で町名の代表点を求めた。動画で使う場合は史跡の指定資料（文化庁「国指定文化財等データベース」など）で確認する |

## 利用条件

- 統計局・e-Stat・統計ダッシュボード：政府標準利用規約（第2.0版）に準拠。出典の記載で二次利用可
- 地球地図日本・国土地理院の API：国土地理院コンテンツ利用規約（出典の記載で利用可）。API の利用は国土地理院の「利用上の注意」に従う
- 国土数値情報 鉄道データ N02-24：2020年以降のデータはオープンデータ（CC BY 4.0）とデータのページに記載。出典の記載が必要
- USGS の地震カタログ：米国政府の著作物（パブリックドメイン）
- NPB の住所：事実の情報として使う。ページの内容は転載しない
- 自治体のページ：主張の内容と所在地を事実として引用する
