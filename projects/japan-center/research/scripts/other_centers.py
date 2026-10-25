"""そのほかの独自計算と時系列

- プロ野球12球団の本拠地球場の重心（NPB の球場情報の住所 → 国土地理院の住所検索）
- 地震の震央の重心（USGS の地震カタログ。M5.0以上、1996〜2025年、陸地から200km 以内）
- 都道府県の重心（1都道府県1票。代表点は都道府県の人口重心）
- 渋川市の「宗谷岬と佐多岬を円で結んだ中心」の検証（2点の中点）
- 人口重心の推移（統計局の公表値 1965〜2020年）→ data/pop_centroid_history.csv
出力：data/computed_other.csv
"""
import io
import json

import numpy as np
import pandas as pd
import requests
import shapely

import geo
import gsi_api
from geo import CACHE, DATA
from geometry_centers import islands, unproject
from weighted_centers import centroid_table

NPB = CACHE / "npb"
# NPB「12球団本拠地球場」（https://npb.jp/stadium/franchise.html）の球場ID と球団
TEAMS = {"290": "北海道日本ハムファイターズ", "029": "東北楽天ゴールデンイーグルス", "068": "埼玉西武ライオンズ",
         "081": "読売ジャイアンツ", "082": "東京ヤクルトスワローズ", "073": "千葉ロッテマリーンズ",
         "093": "横浜DeNAベイスターズ", "151": "中日ドラゴンズ", "175": "オリックス・バファローズ",
         "181": "阪神タイガース", "208": "広島東洋カープ", "245": "福岡ソフトバンクホークス"}
USGS = ("https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv&starttime=1996-01-01&endtime=2026-01-01"
        "&minmagnitude=5&minlatitude=19&maxlatitude=48&minlongitude=120&maxlongitude=157&orderby=time-asc")

# 統計局 統計トピックス No.135・No.61 の表（1965〜2020年）。度・分・秒
POP_HISTORY = [
    (1965, "136 45 46", "35 39 46", "岐阜県山県郡美山町円原"),
    (1970, "136 51 11", "35 39 03", "岐阜県武儀郡洞戸村高賀"),
    (1975, "136 53 08", "35 38 17", "岐阜県美濃市今淵ヶ岳と瓢ヶ岳のほぼ中間"),
    (1980, "136 54 08", "35 38 19", "岐阜県郡上郡美並村片知山の北約1200m"),
    (1985, "136 55 07", "35 37 45", "岐阜県郡上郡美並村片知山の東約1400m"),
    (1990, "136 57 06", "35 37 19", "岐阜県郡上郡美並村長良川鉄道半在駅の東北東約650m"),
    (1995, "136 57 55", "35 37 12", "岐阜県郡上郡美並村長良川鉄道半在駅の東約1825m"),
    (2000, "136 58 45", "35 36 53", "岐阜県武儀郡武儀町北西部"),
    ("2000r", "136 59 16.83", "35 36 54.50", "岐阜県武儀郡武儀町富之保（2005年からの方式で遡及計算）"),
    (2005, "137 00 27.43", "35 36 20.65", "岐阜県関市富之保（関市立武儀東小学校から北約2260m）"),
    (2010, "137 01 45.46", "35 35 35.31", "岐阜県関市富之保（関市立武儀東小学校から東北東約1835m）"),
    (2015, "137 02 15.84", "35 34 51.44", "岐阜県関市中之保（関市立武儀東小学校から東南東約2452m）"),
    (2020, "137 03 20.44", "35 34 03.64", "岐阜県関市中之保（関市立武儀小学校から東南東約4489m）"),
]


def from_dms(s):
    p = [float(x) for x in str(s).split()]
    return p[0] + (p[1] if len(p) > 1 else 0) / 60 + (p[2] if len(p) > 2 else 0) / 3600


def npb():
    rows = []
    for sid, team in TEAMS.items():
        d = json.loads((NPB / f"{sid}.json").read_text())
        addr = d["address"]
        g, precision = gsi_api.geocode(addr), "番地"
        if g is None:
            # 新しい住所（北広島市Fビレッジ、2023年〜）は住所検索にないため、市の代表点を使う
            city = addr[:addr.index("市") + 1]
            g, precision = gsi_api.geocode(city), "市の代表点"
        rows.append(dict(team=team, stadium_id=sid, address=addr, lon=g[0], lat=g[1], matched=g[2], precision=precision))
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "npb_stadiums.csv", index=False)
    x, y = geo.stat_bureau_mean(df["lon"], df["lat"], np.ones(len(df)))
    return dict(id="npb", name="プロ野球12球団の本拠地の重心", field="スポーツ", category="分布の重心",
                definition="NPB 12球団の本拠地球場を同じ重みで数えた重心", unit_level="地点（住所の代表点）", year="2026年",
                lon=x, lat=y, method="独自計算", source="npb_stadium,gsi_geocoder", n_units=len(df),
                note="球場の位置は住所検索の代表点（エスコンフィールドは北広島市の代表点）")


def quakes():
    path = CACHE / "usgs_m5_1996_2025.csv"
    if not path.exists():
        r = requests.get(USGS, timeout=300)
        r.raise_for_status()
        path.write_bytes(r.content)
    q = pd.read_csv(path)
    land = shapely.union_all([p for p in islands()])
    x, y = geo.TO_XY.transform(q["longitude"].values, q["latitude"].values)
    d = shapely.distance(shapely.points(x, y), land) / 1000
    near = q[d <= 200]
    lon, lat = geo.stat_bureau_mean(near["longitude"], near["latitude"], np.ones(len(near)))
    return dict(id="earthquakes", name="地震（M5以上）の震央の重心", field="自然・環境", category="分布の重心",
                definition="1996〜2025年のマグニチュード5.0以上の地震のうち、震央が陸地から200km 以内のものを1回1票で数えた重心",
                unit_level="地点（震央）", year="1996〜2025年", lon=lon, lat=lat, method="独自計算", source="usgs_comcat,gsi_globalmap",
                n_units=len(near), note=f"カタログの範囲内 {len(q)} 回のうち {len(near)} 回。USGS のカタログで、気象庁の震源とは一致しない。"
                "2011年の東北地方太平洋沖地震の余震が多く含まれる")


def prefectures():
    cen = centroid_table()
    p = cen[cen.index.str.endswith("000") & (cen.index != "00000")]
    x, y = geo.stat_bureau_mean(p["lon"], p["lat"], np.ones(len(p)))
    return dict(id="prefecture_mean", name="都道府県の重心（1都道府県1票）", field="政治・行政", category="分布の重心",
                definition="47都道府県を同じ重みで数えた重心。代表点は各都道府県の人口重心", unit_level="都道府県",
                year="2020年", lon=x, lat=y, method="独自計算", source="stat_topics135", n_units=len(p))


def shibukawa_check():
    """宗谷岬（主要4島の最北端）と佐多岬（最南端）の中点。地球地図日本の陸地の端点を使う"""
    parts = [unproject(p) for p in islands()[:4]]
    pts = np.vstack([np.asarray(p.exterior.coords) for p in parts])
    n, s = pts[pts[:, 1].argmax()], pts[pts[:, 1].argmin()]
    lon, lat = geo.GEOD.npts(n[0], n[1], s[0], s[1], 1)[0]
    return dict(id="soya_sata_mid", name="宗谷岬と佐多岬の中点", field="地理・国土", category="幾何学的中心",
                definition="主要4島の最北端（宗谷岬）と最南端（佐多岬）を結ぶ測地線の中点（渋川市の説明の検証用の解釈）",
                unit_level="地点", year="2016年（地図の版）", lon=lon, lat=lat, method="独自計算", source="gsi_globalmap",
                note=f"最北端 {n[0]:.3f}, {n[1]:.3f}／最南端 {s[0]:.3f}, {s[1]:.3f}。2点を直径の両端とする円の中心でもある")


def history():
    rows = []
    # 2005年に算出方法が変わった。2000年は旧方式と、新方式での遡及計算（2000r）の両方がある
    for y, lo, la, place in POP_HISTORY:
        method = "2005年からの方式" if y == "2000r" or y >= 2005 else "2000年までの方式"
        rows.append(dict(year=2000 if y == "2000r" else y, method=method, lon=from_dms(lo), lat=from_dms(la),
                         lon_dms=lo, lat_dms=la, place=place))
    df = pd.DataFrame(rows)
    move = [np.nan]
    for i in range(1, len(df)):
        prev = df.iloc[i - 1] if df.iloc[i - 1]["method"] == df.iloc[i]["method"] else None
        move.append(np.nan if prev is None else geo.distance_km(prev["lon"], prev["lat"], df.iloc[i]["lon"], df.iloc[i]["lat"]))
    df["move_km"] = move
    df.to_csv(DATA / "pop_centroid_history.csv", index=False)
    print(df.to_string())


def main():
    history()
    rows = [npb(), quakes(), prefectures(), shibukawa_check()]
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "computed_other.csv", index=False)
    print(df[["id", "lon", "lat", "n_units", "note"]].to_string())


if __name__ == "__main__":
    main()
