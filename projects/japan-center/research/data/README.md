# data/

## centers.csv・centers.json（中心の一覧）

| 列 | 意味 |
| --- | --- |
| id | 一意の識別子 |
| name | 名称 |
| field | 分野（指示書3章の分野） |
| category | 分類（幾何学的中心、分布の重心、最大集積地、ネットワークの中心、アクセスの中心、制度的中心、制度的・歴史的中心、象徴的・通称的中心） |
| definition | 何をもって中心とするか。統計の指標名と単位を含む |
| place | 資料が示す場所（資料に場所の記述がなければ located と同じ） |
| located | 座標から求めた所在地（国土地理院の逆ジオコーダー）。海上は「海上（最寄りの陸地まで約○km）」 |
| land | 陸上／海上。逆ジオコーダーと地球地図日本の陸地で判定 |
| pref・municipality | 座標がある都道府県・市区町村。海上は空欄（自治体に割り当てない） |
| lon・lat | 経度・緯度（10進、度） |
| lon_dms・lat_dms | 同じ値の度分秒 |
| year | 対象年（統計の年・年度、地図の版、主張の時期） |
| method | 公表値／独自計算／自治体の主張／位置は住所の代表点 など |
| unit_level | 集計単位（市区町村、都道府県、1km 格子、駅、地点、住所の代表点） |
| source | 出典の ID（sources.md）。統計ダッシュボードは `dashboard:<指標コード>` |
| reliability | 信頼性と主な制約 |
| top_unit・top_share | 分布の重心に使った量が最も多い地域と、その全国に占める割合（0〜1） |
| alt_km | 統計局の式の重心と、球面上の重心との距離（km）。定義の違いによる幅 |
| n_units | 計算に使った地域・地点の数 |
| note | 補足 |

- 座標がない行：日本標準時子午線（経線）と、最大集積地（地域で示す）
- 不明な値は空欄。推測で埋めない

## そのほかのファイル

| ファイル | 内容 | 作るスクリプト |
| --- | --- | --- |
| curated_centers.csv | 公表値・制度・歴史・自治体の主張（手で記録。lon_dms・lat_dms は「度 分 秒」、座標がないものは address を住所検索する） | 手入力 |
| municipalities.csv | 市区町村（指定都市は区）ごとの2020年の人口重心（lon・lat）と国勢調査の値（人、世帯）。pop2025 は2025年の人口 | municipalities.py |
| indicators.csv | 統計ダッシュボードの指標（key、indicator＝指標コード、rank＝3 都道府県／4 市区町村、time＝年、region＝地域コード、value、unit_name） | fetch_dashboard.py |
| computed_geometry.csv・computed_weighted.csv・computed_network.csv・computed_other.csv | 独自計算の中間結果 | 各スクリプト |
| pop_centroid_history.csv | 人口重心の推移（統計局の公表値、1965〜2020年）。method は算出方法（2005年に変更）、move_km は前回からの移動距離（方法が同じ区間だけ） | other_centers.py |
| npb_stadiums.csv | プロ野球の本拠地球場の住所と座標（precision＝番地／市の代表点） | other_centers.py |
| analysis_distances.csv | 各点の人口重心（2020年）からの距離（km）と方位 | analyze.py |
| analysis_pairs.csv | 似た定義どうしの距離 | analyze.py |
| analysis_output.txt | analyze.py の出力 | analyze.py |

## 列の単位の補足

- municipalities.csv の w_* は国勢調査の産業別就業者（常住地、人）。daytime_pop は昼間人口（人）
- indicators.csv の value の単位は unit_name（百万円、ha、人泊、施設、トン、千kWh など）
