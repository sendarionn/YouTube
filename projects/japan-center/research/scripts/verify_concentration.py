"""追加調査①②：分布の重心の岐阜県への集中と、意外な地点に重心が現れる理由（video/brief-video.md 3・4章）

① 岐阜県への集中
- 分布の重心48件の重み（指標）を都道府県別に集計し、指標どうしと人口との相関（都道府県の全国シェアの Pearson・Spearman）を求める
- 相関の高い指標をまとめた群（階層クラスタリング、完全連結、1−r で 0.1 を閾値）と、分野ごとの代表指標に絞っても、岐阜県・人口重心の周りに集まるかを調べる
- 代表点を変えた場合（人口重心 → 面積の重心）に、各重心がどれだけ動き、岐阜県内の件数がどう変わるかを調べる
- 人口重心の周りの陸地のうち、岐阜県が占める割合（「岐阜県に入る」ことの意味を確かめる）

② 意外な地点
- 情報通信業の従業者（経済センサス 2021、従業地）の重心を、首都圏（1都3県）とそれ以外の2つの重心のつり合いに分解する
- 早川町そのものの値、東京を除いた場合の重心

出力：data/verify_indicators.csv、verify_groups.csv、verify_points.csv、verify_ict.json
"""
import json

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from scipy.stats import spearmanr

import geo
from geo import DATA
from weighted_centers import CENSUS, DASH, centroid_table, leaf_units

GIFU = "21"
# 分野ごとの代表指標（その分野の量を最も直接に表すものを選ぶ。人口との相関で選ばない）
REPRESENTATIVE = {"人口": "pop2020_recalc", "経済": "gdp", "商業・金融": "retail", "農林水産業": "agri_output",
                  "自然・環境": "forest", "エネルギー": "power_gen", "観光": "guest_nights", "教育・研究": "univ_students",
                  "文化・芸術": "museums", "医療・福祉": "hospital_beds", "物流": "sea_cargo", "交通": "expressway_km",
                  "通信・情報": "emp_ict", "スポーツ": "npb", "政治・行政": "municipality_mean"}


def area_points():
    """地域コード → 面積の重心（地球地図日本の市区町村の面、2014年の境界。都道府県は市区町村の面を合わせる）"""
    lo, la, codes = geo.land_grid(2000)
    df = pd.DataFrame({"lon": lo, "lat": la, "code": codes})
    out = {}
    for code, g in df.groupby("code"):
        out[code] = geo.stat_bureau_mean(g["lon"], g["lat"], np.ones(len(g)))
    for p, g in df.groupby(df["code"].str[:2]):
        out[p + "000"] = geo.stat_bureau_mean(g["lon"], g["lat"], np.ones(len(g)))
    return out


def weights():
    """指標ごとの重み {id: Series(地域コード → 値)}、集計単位 {id: 3/4}"""
    muni = pd.read_csv(DATA / "municipalities.csv", dtype={"code": str}).set_index("code")
    ind = pd.read_csv(DATA / "indicators.csv", dtype={"region": str, "indicator": str})
    W, rank = {}, {}
    for cid, col, *_ in CENSUS:
        W[cid] = muni[col].fillna(0)
        rank[cid] = 4
    for key, *_ in DASH:
        d = ind[ind["key"] == key]
        r = int(d["rank"].iloc[0])
        d = d.groupby("region")["value"].sum()
        if r == 4:
            if any("22138" <= c <= "22140" for c in d.index):
                d = d.drop("22130", errors="ignore")
                d = d.rename(index=lambda c: "22130" if "22138" <= c <= "22140" else c).groupby(level=0).sum()
            d = d.loc[leaf_units(d.index)]
        W[key] = d
        rank[key] = r
    return W, rank


def to_pref(s):
    return s.groupby(s.index.str[:2]).sum().reindex([f"{i:02d}" for i in range(1, 48)]).fillna(0)


def centroid(s, points):
    s = s[s > 0]
    s = s[[c in points for c in s.index]]
    lon = np.array([points[c][0] for c in s.index])
    lat = np.array([points[c][1] for c in s.index])
    ok = ~np.isnan(lon)
    return geo.stat_bureau_mean(lon[ok], lat[ok], s.values[ok])


def main():
    c = pd.read_csv(DATA / "centers.csv").set_index("id")
    dist = c[c["category"] == "分布の重心"]
    W, rank = weights()
    other = [i for i in dist.index if i not in W]  # npb、earthquakes、prefecture_mean など地点・等重みのもの
    pop = to_pref(W["pop2020_recalc"])
    share = pd.DataFrame({k: to_pref(v) / to_pref(v).sum() for k, v in W.items()})
    popshare = pop / pop.sum()

    # 相関（都道府県の全国シェア）。東京都の大きさに左右されるため、Spearman（順位）と東京都を除いた Pearson も見る
    rows = []
    no_tokyo = share.index != "13"
    for k in share:
        rows.append(dict(id=k, name=c.loc[k, "name"], field=c.loc[k, "field"], unit="市区町村" if rank[k] == 4 else "都道府県",
                         source=c.loc[k, "source"].split(",")[0], year=c.loc[k, "year"],
                         r_pop=np.corrcoef(share[k], popshare)[0, 1],
                         rho_pop=spearmanr(share[k], popshare)[0],
                         r_pop_ex_tokyo=np.corrcoef(share[k][no_tokyo], popshare[no_tokyo])[0, 1],
                         tokyo_share=share.loc["13", k], gifu=c.loc[k, "pref"] == "岐阜県",
                         located=c.loc[k, "located"]))
    for k in other:
        rows.append(dict(id=k, name=c.loc[k, "name"], field=c.loc[k, "field"], unit=c.loc[k, "unit_level"],
                         source=c.loc[k, "source"].split(",")[0], year=c.loc[k, "year"], gifu=c.loc[k, "pref"] == "岐阜県",
                         located=c.loc[k, "located"]))
    ind = pd.DataFrame(rows)

    # 群：1−r の完全連結で、群の中のどの2指標も r ≥ 0.9
    R = share.corr()
    Z = linkage(squareform(1 - R.values, checks=False), "complete")
    lab = fcluster(Z, 0.1, "distance")
    ind["group"] = ind["id"].map(dict(zip(R.index, lab)))
    groups = []
    for g, ids in ind.dropna(subset=["group"]).groupby("group")["id"]:
        ids = list(ids)
        # 群の代表：群のほかの指標との相関の平均が最も高いもの
        rep = max(ids, key=lambda i: R.loc[i, ids].mean())
        groups.append(dict(group=int(g), n=len(ids), representative=rep, rep_name=c.loc[rep, "name"],
                           rep_located=c.loc[rep, "located"], rep_gifu=c.loc[rep, "pref"] == "岐阜県",
                           members="・".join(c.loc[i, "name"] for i in ids),
                           mean_r_pop=float(np.mean([R.loc[i, "pop2020_recalc"] for i in ids]))))
    for k in other:  # 地点・等重みの重心は相関を計算できないため、それぞれ1群
        groups.append(dict(group=f"点:{k}", n=1, representative=k, rep_name=c.loc[k, "name"], rep_located=c.loc[k, "located"],
                           rep_gifu=c.loc[k, "pref"] == "岐阜県", members=c.loc[k, "name"], mean_r_pop=np.nan))
    groups = pd.DataFrame(groups)
    ind.round(3).to_csv(DATA / "verify_indicators.csv", index=False)
    groups.round(3).to_csv(DATA / "verify_groups.csv", index=False)

    # 代表点を面積の重心にした場合
    pts_pop = {k: (v["lon"], v["lat"]) for k, v in centroid_table().iterrows()}
    pts_area = area_points()
    alt = []
    for k, s in W.items():
        lon, lat = centroid(s, pts_area)
        missing = [x for x in s[s > 0].index if x not in pts_area]
        code, _ = __import__("gsi_api").reverse(lon, lat)
        alt.append(dict(id=k, alt_lon=lon, alt_lat=lat, shift_km=geo.distance_km(c.loc[k, "lon"], c.loc[k, "lat"], lon, lat),
                        alt_pref_code=code[:2] if code else None, alt_gifu=bool(code and code[:2] == GIFU),
                        missing_area_points=len(missing)))
    alt = pd.DataFrame(alt)
    ind = ind.merge(alt, on="id", how="left")
    ind.round(4).to_csv(DATA / "verify_indicators.csv", index=False)

    # 人口重心の周りの陸地のうち岐阜県の割合
    p0 = c.loc["pop2020_official"]
    lo, la, codes = geo.land_grid(1000)
    d = geo.GEOD.inv(np.full(len(lo), p0["lon"]), np.full(len(lo), p0["lat"]), lo, la)[2] / 1000
    ring = {r: float((codes[d <= r].astype(str).astype("U2") == GIFU).mean()) for r in (25, 50, 75, 100)}
    pts = pd.DataFrame([dict(radius_km=r, gifu_land_share=v) for r, v in ring.items()])
    pts.to_csv(DATA / "verify_points.csv", index=False)

    # ② 情報通信業の分解
    s = W["emp_ict"]
    s = s[s > 0]
    metro = s[s.index.str[:2].isin(["11", "12", "13", "14"])]
    rest = s[~s.index.isin(metro.index)]
    m_c, r_c, all_c = centroid(metro, pts_pop), centroid(rest, pts_pop), centroid(s, pts_pop)
    ex_tokyo = centroid(s[s.index.str[:2] != "13"], pts_pop)
    top = s.sort_values(ascending=False)
    pref = to_pref(s)
    hayakawa = "19364"
    ict = dict(total=int(s.sum()), metro_share=float(metro.sum() / s.sum()), tokyo_share=float(pref["13"] / s.sum()),
               minato_share=float(s.get("13103", 0) / s.sum()),
               metro_centroid=m_c, rest_centroid=r_c, all_centroid=all_c, ex_tokyo_centroid=ex_tokyo,
               ex_tokyo_located=__import__("gsi_api").reverse(*ex_tokyo),
               metro_to_all_km=geo.distance_km(*m_c, *all_c), rest_to_all_km=geo.distance_km(*r_c, *all_c),
               metro_to_rest_km=geo.distance_km(*m_c, *r_c),
               hayakawa_employees=float(s.get(hayakawa, 0)), hayakawa_pop2020=None,
               top_units=[(centroid_table().loc[k, "name"], int(v), float(v / s.sum())) for k, v in top.head(8).items()],
               top_prefs=[(k, int(v), float(v / s.sum())) for k, v in pref.sort_values(ascending=False).head(8).items()])
    muni = pd.read_csv(DATA / "municipalities.csv", dtype={"code": str}).set_index("code")
    ict["hayakawa_pop2020"] = int(muni.loc[hayakawa, "pop"])
    ict["hayakawa_name"] = muni.loc[hayakawa, "name"]
    (DATA / "verify_ict.json").write_text(json.dumps(ict, ensure_ascii=False, indent=1, default=str))

    # 表示
    pd.set_option("display.width", 220)
    print(ind[["id", "field", "unit", "r_pop", "rho_pop", "r_pop_ex_tokyo", "tokyo_share", "group", "gifu", "alt_gifu", "shift_km"]]
          .round(2).to_string())
    print(groups[["group", "n", "rep_name", "rep_located", "rep_gifu", "mean_r_pop"]].round(2).to_string())
    print("岐阜県内：", int(ind["gifu"].sum()), "/", len(ind), "（面積の重心を代表点にすると",
          int(ind["alt_gifu"].fillna(ind["gifu"]).sum()), "）")
    print("群の代表で：", int(groups["rep_gifu"].sum()), "/", len(groups))
    reps = [REPRESENTATIVE[f] for f in sorted(REPRESENTATIVE)]
    print("分野の代表で：", int(sum(c.loc[r, "pref"] == "岐阜県" for r in reps)), "/", len(reps),
          [(f, c.loc[REPRESENTATIVE[f], "located"]) for f in sorted(REPRESENTATIVE)])
    print("人口重心の周りの陸地に占める岐阜県の割合：", ring)
    print(json.dumps(ict, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
