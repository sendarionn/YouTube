"""中心の分布の分析（analysis.md の表の元）

- 人口重心（2020年、公表値）からの距離と方位
- 分類・分野ごとの広がり
- 都道府県ごとの点の数（多数決ではなく、どの定義が集まっているかを見るため）
- 似た定義どうしの距離
- 人口重心の推移と2025年の推計
出力：data/analysis_distances.csv、data/analysis_pairs.csv
"""
import math

import numpy as np
import pandas as pd

import geo
from geo import DATA

PAIRS = [
    ("pop2020_official", "area_excl_nt", "人が住む場所の中心 と 土地の中心"),
    ("pop2020_official", "pop_median_point", "重心 と 距離の合計が最小の点（同じ人口）"),
    ("pop2020_official", "pop_median_lonlat", "重心 と 東西・南北の中央値の点（同じ人口）"),
    ("pop2020_official", "daytime_pop", "夜の人口 と 昼の人口"),
    ("pop2020_official", "gdp", "人口 と 県内総生産"),
    ("children", "elderly", "子ども と 高齢者"),
    ("w_ict_res", "emp_ict", "情報通信業：住む場所 と 働く場所"),
    ("rail_closeness", "expressway_closeness", "鉄道網の中心 と 高速道路網の中心"),
    ("area_all", "area_excl_nt", "北方領土を含む面積重心 と 除く面積重心"),
    ("area_excl_nt", "coastline", "陸地の重心 と 海岸線の重心"),
    ("bbox_mid", "area_all", "東西南北端の中点 と 面積重心"),
    ("farthest_from_sea", "far_sea_saku", "海から最も遠い地点：独自計算 と 佐久市の公表"),
    ("soya_sata_mid", "mannaka_shibukawa", "宗谷岬と佐多岬の中点 と 渋川市"),
    ("chiko_tatsuno", "zero_tatsuno", "チコちゃんポイント と ゼロポイント"),
    ("agri_output", "w_agri", "農業産出額 と 農業・林業で働く人"),
    ("fish_catch", "w_fishery", "漁獲量 と 漁業で働く人"),
    ("pop2020_recalc", "pop2025_est", "人口重心 2020年 と 2025年（推計）"),
]


def bearing(lon1, lat1, lon2, lat2):
    az = geo.GEOD.inv(lon1, lat1, lon2, lat2)[0] % 360
    dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
    return dirs[int((az + 11.25) // 22.5) % 16]


def main():
    c = pd.read_csv(DATA / "centers.csv")
    pts = c.dropna(subset=["lon", "lat"]).copy()
    pts = pts[pts["id"] != "std_meridian"]
    p0 = pts[pts["id"] == "pop2020_official"].iloc[0]
    pts["dist_pop_km"] = [geo.distance_km(p0["lon"], p0["lat"], r["lon"], r["lat"]) for _, r in pts.iterrows()]
    pts["dir_from_pop"] = [bearing(p0["lon"], p0["lat"], r["lon"], r["lat"]) for _, r in pts.iterrows()]
    out = pts[["id", "name", "category", "field", "located", "land", "pref", "dist_pop_km", "dir_from_pop", "alt_km"]]
    out = out.sort_values("dist_pop_km")
    out.to_csv(DATA / "analysis_distances.csv", index=False)

    print(f"地図に置く点：{len(pts)}（標準時子午線は線のため除く）")
    print("\n## 人口重心からの距離の分布")
    for k in (25, 50, 100, 200, 400):
        print(f"{k:4d} km 以内：{(pts['dist_pop_km'] <= k).sum()}")
    print("\n## 分類ごと（人口重心からの距離の中央値、件数、海上の件数）")
    g = pts.groupby("category", observed=True).agg(n=("id", "size"), median_km=("dist_pop_km", "median"),
                                                   max_km=("dist_pop_km", "max"),
                                                   sea=("land", lambda s: (s == "海上").sum()))
    print(g.to_string())
    print("\n## 独自計算の分布の重心（computed）だけ：分野ごと")
    comp = pts[pts["category"] == "分布の重心"]
    print(comp.groupby("field").agg(n=("id", "size"), median_km=("dist_pop_km", "median")).sort_values("median_km").to_string())
    print("\n## 都道府県ごとの点の数（海上を除く）")
    print(pts["pref"].value_counts().to_string())
    print("\n## 分布の重心のうち岐阜県内：", (comp["pref"] == "岐阜県").sum(), "/", len(comp))
    print("\n## 海上の点")
    print(pts[pts["land"] == "海上"][["id", "located"]].to_string())
    print("\n## 定義の違い（統計局の式と球面上の平均）の差 alt_km")
    print(pts["alt_km"].describe().round(1).to_string())

    rows = []
    idx = pts.set_index("id")
    for a, b, label in PAIRS:
        ra, rb = idx.loc[a], idx.loc[b]
        rows.append(dict(a=a, b=b, label=label, km=geo.distance_km(ra["lon"], ra["lat"], rb["lon"], rb["lat"]),
                         dir=bearing(ra["lon"], ra["lat"], rb["lon"], rb["lat"]), a_at=ra["located"], b_at=rb["located"]))
    pairs = pd.DataFrame(rows)
    pairs.to_csv(DATA / "analysis_pairs.csv", index=False)
    print("\n## 似た定義どうしの距離")
    print(pairs[["label", "km", "dir", "a_at", "b_at"]].round(1).to_string())

    h = pd.read_csv(DATA / "pop_centroid_history.csv")
    print("\n## 人口重心の推移")
    a, b = h.iloc[0], h.iloc[-1]
    print(f"1965→2020：直線で {geo.distance_km(a['lon'], a['lat'], b['lon'], b['lat']):.1f} km、{bearing(a['lon'], a['lat'], b['lon'], b['lat'])}"
          f"／5年ごとの移動の合計 {h['move_km'].sum():.1f} km（2000年の方式変更をまたぐ区間を除く）")
    e = idx.loc["pop2025_est"]
    print(f"2020（公表）→2025（推計）：{geo.distance_km(b['lon'], b['lat'], e['lon'], e['lat']):.1f} km、{bearing(b['lon'], b['lat'], e['lon'], e['lat'])}")


if __name__ == "__main__":
    main()
