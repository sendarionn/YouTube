"""分布の重心・最大集積地・アクセスの中心（直線距離）を計算する

代表点
- 市区町村別の値：統計局が公表した2020年の市区町村の人口重心（topics135_10.xlsx）に置く
- 都道府県別の値：同じく都道府県の人口重心に置く
  面積で決まる量（森林、耕地など）も人口重心に置くと偏るため、それらは市区町村別の値だけを使う
- 指定都市は、区の値があれば区を使い、市の合計は使わない。区の値がなければ市の合計を使う

重心は統計局の人口重心と同じ式（geo.stat_bureau_mean）で計算し、公表値と比べられるようにする
球面上の重み付き平均（geo.spherical_mean）も計算し、定義の違いによる差（alt_km）を記録する
出力：data/computed_weighted.csv
"""
import pandas as pd

import geo
from geo import DATA

SRC = geo.CACHE / "src"


def centroid_table():
    """地域コード → 2020年の人口重心（経度, 緯度）。都道府県・市区町村・指定都市の合計を含む"""
    t = pd.concat([d.iloc[2:, :4] for _, d in pd.read_excel(SRC / "topics135_10.xlsx", sheet_name=None,
                                                            header=None).items()])
    t.columns = ["code", "name", "lon", "lat"]
    t["code"] = t["code"].astype(str).str.zfill(5)
    return t.drop_duplicates("code").set_index("code")[["name", "lon", "lat"]].astype({"lon": float, "lat": float})


def leaf_units(codes):
    """指定都市の合計と区が両方ある場合は合計を除く"""
    codes = set(codes)
    drop = set()
    for c in codes:
        if c.endswith("000"):
            drop.add(c)
        elif c.endswith("00") or c in {"14130", "14150", "22130", "27140", "40130"}:
            # 指定都市の合計（例 01100 札幌市、14130 川崎市）。区のコードは合計+1〜
            wards = [w for w in codes if w != c and w[:2] == c[:2] and int(c) < int(w) < int(c) + 20]
            if wards:
                drop.add(c)
    return sorted(codes - drop)


# 国勢調査（市区町村別）の変数：(ID, 名称, 分野, 定義)
CENSUS = [
    ("pop2020_recalc", "pop", "人口重心（再計算）", "人口", "2020年の常住人口。統計局の市区町村別人口重心から全国を再計算（公表値との照合用）"),
    ("pop2025_est", "pop2025", "人口重心（2025年・推計）", "人口", "2025年国勢調査の市区町村別人口を、2020年の市区町村の人口重心に置いた推計"),
    ("daytime_pop", "daytime_pop", "昼間人口の重心", "人口", "昼間人口（常住人口－流出人口＋流入人口。従業地・通学地による）"),
    ("children", "age0_14", "子ども（15歳未満）の重心", "人口", "15歳未満人口"),
    ("elderly", "age65p", "高齢者（65歳以上）の重心", "人口", "65歳以上人口"),
    ("foreign_residents", "foreign", "外国人住民の重心", "人口", "国勢調査の外国人人口"),
    ("households", "households", "世帯の重心", "人口", "総世帯数"),
    ("w_agri", "w_agri_forest", "農業・林業で働く人の重心", "農林水産業", "農業・林業の就業者（常住地）"),
    ("w_fishery", "w_fishery", "漁業で働く人の重心", "農林水産業", "漁業の就業者（常住地）"),
    ("w_manufacturing", "w_manufacturing", "製造業で働く人の重心", "経済", "製造業の就業者（常住地）"),
    ("w_ict_res", "w_ict", "情報通信業で働く人の重心（常住地）", "通信・情報", "情報通信業の就業者（常住地）"),
]

# 統計ダッシュボードの指標：(キー, 名称, 分野)
DASH = [
    ("gdp", "県内総生産（GDP）の重心", "経済"),
    ("manufacturing", "製造品出荷額の重心", "経済"),
    ("establishments", "事業所の重心", "経済"),
    ("employees", "働く場所（従業者）の重心", "経済"),
    ("retail", "小売販売額の重心", "商業・金融"),
    ("deposits", "銀行預金の重心", "商業・金融"),
    ("emp_finance", "金融・保険業の従業者の重心", "商業・金融"),
    ("emp_ict", "情報通信業の従業者の重心", "通信・情報"),
    ("emp_research", "学術研究・専門サービスの従業者の重心", "教育・研究"),
    ("agri_output", "農業産出額の重心", "農林水産業"),
    ("farmland", "耕地の重心", "農林水産業"),
    ("forest", "森林の重心", "自然・環境"),
    ("fish_catch", "海面漁業漁獲量の重心", "農林水産業"),
    ("power_gen", "発電電力量の重心", "エネルギー"),
    ("power_demand", "電力需要の重心", "エネルギー"),
    ("guest_nights", "延べ宿泊者数の重心", "観光"),
    ("guest_nights_foreign", "外国人延べ宿泊者数の重心", "観光"),
    ("universities", "大学の重心", "教育・研究"),
    ("univ_students", "大学生の重心", "教育・研究"),
    ("museums", "博物館の重心", "文化・芸術"),
    ("theaters", "劇場・音楽堂の重心", "文化・芸術"),
    ("libraries", "図書館の重心", "文化・芸術"),
    ("important_cultural", "重要文化財の重心", "文化・芸術"),
    ("religious_bodies", "宗教団体の重心", "文化・芸術"),
    ("hospitals", "病院の重心", "医療・福祉"),
    ("hospital_beds", "病床の重心", "医療・福祉"),
    ("doctors", "医師の重心", "医療・福祉"),
    ("air_cargo", "航空貨物の重心", "物流"),
    ("sea_cargo", "海上貨物（港湾の出入貨物）の重心", "物流"),
    ("jr_freight", "JR貨物の発送量の重心", "物流"),
    ("expressway_km", "高速道路の延長の重心", "交通"),
]


def center(lon, lat, w):
    """(経度, 緯度, 球面上の重心との距離 km)"""
    lon, lat, w = (pd.Series(a).reset_index(drop=True).astype(float) for a in (lon, lat, w))
    ok = lon.notna() & lat.notna() & w.notna() & (w > 0)
    x, y = geo.stat_bureau_mean(lon[ok], lat[ok], w[ok])
    sx, sy = geo.spherical_mean(lon[ok], lat[ok], w[ok])
    return x, y, geo.distance_km(x, y, sx, sy)


def year_of(t):
    return f"{t[:4]}年度" if t.endswith("FY00") else f"{t[:4]}年"


def main():
    cen = centroid_table()
    muni = pd.read_csv(DATA / "municipalities.csv", dtype={"code": str}).set_index("code")
    out = []

    # 公表値との照合：都道府県の人口重心と人口から、統計局の式で全国を計算する
    pref = muni.groupby(muni.index.str[:2])["pop"].sum()
    pc = cen.loc[[p + "000" for p in pref.index]]
    sb = geo.stat_bureau_mean(pc["lon"], pc["lat"], pref.values)
    pub = cen.loc["00000"]
    diff_m = geo.distance_km(sb[0], sb[1], pub["lon"], pub["lat"]) * 1000
    print(f"人口重心の照合：統計局の式で再計算 {sb[0]:.6f}, {sb[1]:.6f}／公表 {pub['lon']:.6f}, {pub['lat']:.6f}（差 {diff_m:.1f} m）")
    sph = geo.spherical_mean(muni["lon"], muni["lat"], muni["pop"])
    print(f"球面上の重心（市区町村単位）との差：{geo.distance_km(sph[0], sph[1], pub['lon'], pub['lat']) * 1000:.0f} m")

    for cid, col, name, field, definition in CENSUS:
        w = muni[col].fillna(0)
        lon, lat, alt = center(muni["lon"], muni["lat"], w)
        top = muni.loc[w.idxmax()]
        out.append(dict(id=cid, name=name, field=field, category="分布の重心", definition=definition,
                        unit_level="市区町村（区）", year="2025年" if col == "pop2025" else "2020年", lon=lon, lat=lat,
                        method="独自計算", source="estat_census2020" + (",estat_census2025" if col == "pop2025" else "") + ",stat_topics135",
                        n_units=int((w > 0).sum()), top_unit=f"{top['pref']}{top['name']}", top_share=float(w.max() / w.sum()),
                        alt_km=alt))

    ind = pd.read_csv(DATA / "indicators.csv", dtype={"region": str, "indicator": str})
    for key, name, field in DASH:
        d = ind[ind["key"] == key]
        rank = int(d["rank"].iloc[0])
        d = d.groupby("region")["value"].sum()
        if rank == 4:
            # 2020年より後にできた区（浜松市 2024年の再編）は、2020年の人口重心がないため市の合計の点に置く
            if any("22138" <= c <= "22140" for c in d.index):
                d = d.drop("22130", errors="ignore")
                d = d.rename(index=lambda c: "22130" if "22138" <= c <= "22140" else c).groupby(level=0).sum()
        units = leaf_units(d.index) if rank == 4 else list(d.index)
        missing = [u for u in units if u not in cen.index or pd.isna(cen.loc[u, "lon"])]
        units = [u for u in units if u not in missing]
        v = d.loc[units]
        v = v[v > 0]
        lon, lat, alt = center(cen.loc[v.index, "lon"], cen.loc[v.index, "lat"], v.values)
        top = v.idxmax()
        r = ind[ind["key"] == key].iloc[0]
        out.append(dict(id=key, name=name, field=field, category="分布の重心", definition=f"{r['name']}（{r['unit_name']}）",
                        unit_level="市区町村（区）" if rank == 4 else "都道府県（代表点は人口重心）",
                        year=year_of(r["time"]), lon=lon, lat=lat, method="独自計算",
                        source=f"dashboard:{r['indicator']},stat_topics135", n_units=len(v),
                        top_unit=(cen.loc[top[:2] + "000", "name"] if not top.endswith("000") else "") + cen.loc[top, "name"],
                        top_share=float(v.max() / v.sum()), alt_km=alt,
                        note=(f"人口重心のない地域 {len(missing)} 件を除外（{','.join(missing[:5])}）" if missing else "")))

    # アクセスの中心（直線距離）：住民からの直線距離の合計が最小の地点
    lon, lat = geo.geometric_median(muni["lon"], muni["lat"], muni["pop"])
    avg = geo.weighted_sum_distance(lon, lat, muni["lon"], muni["lat"], muni["pop"])
    avg_c = geo.weighted_sum_distance(pub["lon"], pub["lat"], muni["lon"], muni["lat"], muni["pop"])
    out.append(dict(id="pop_median_point", name="全住民への直線距離が最も短い地点", field="人口", category="アクセスの中心",
                    definition="住民一人ひとりからの直線距離（測地線）の合計が最小になる地点（幾何中央値）",
                    unit_level="市区町村（区）", year="2020年", lon=lon, lat=lat, method="独自計算",
                    source="estat_census2020,stat_topics135", n_units=len(muni),
                    note=f"平均距離 {avg:.1f} km（人口重心からは {avg_c:.1f} km）"))
    # 人口の中央点：東西・南北それぞれで人口を半分に分ける線の交点
    def wmedian(x, w):
        o = x.argsort()
        cw = w.values[o].cumsum()
        return float(x.values[o][cw.searchsorted(cw[-1] / 2)])
    out.append(dict(id="pop_median_lonlat", name="人口を東西・南北に二等分する点", field="人口", category="分布の重心",
                    definition="人口を東西に半分ずつに分ける経線と、南北に半分ずつに分ける緯線の交点（中央値の点）",
                    unit_level="市区町村（区）", year="2020年", lon=wmedian(muni["lon"], muni["pop"]),
                    lat=wmedian(muni["lat"], muni["pop"]), method="独自計算", source="estat_census2020,stat_topics135",
                    n_units=len(muni)))
    # 市区町村を1つずつ同じ重みで数えた重心（人口重心の位置を代表点にする）
    lon, lat, alt = center(muni["lon"], muni["lat"], pd.Series(1.0, index=muni.index))
    out.append(dict(id="municipality_mean", alt_km=alt, name="市区町村の重心（1自治体1票）", field="政治・行政", category="分布の重心",
                    definition="全市区町村（指定都市は区）を同じ重みで数えた重心。代表点は各市区町村の人口重心",
                    unit_level="市区町村（区）", year="2020年", lon=lon, lat=lat, method="独自計算",
                    source="stat_topics135", n_units=len(muni)))
    pd.DataFrame(out).to_csv(DATA / "computed_weighted.csv", index=False)
    print(pd.DataFrame(out)[["id", "lon", "lat", "alt_km", "top_unit", "top_share", "note"]].to_string())


if __name__ == "__main__":
    main()
