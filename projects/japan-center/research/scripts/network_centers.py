"""交通網の中心（ネットワークの中心・アクセスの中心）を計算する

鉄道：国土数値情報「鉄道」N02-24（2024年）
- 線路の区間の端点を節点、区間を辺（長さは測地線距離）にしたグラフを作る。座標を約1m で丸めて接続を判定する
- 同じ駅グループ（N02_005g）の駅は乗り換えできるものとして、駅どうしを長さ0の辺で結ぶ
- 本州・九州・四国・北海道がつながった最大の連結成分だけを使う（沖縄・離島の路線は含まれない）
- 指標1（ネットワークの中心）：全駅への線路上の距離の平均が最小の駅（距離の近接中心性）
- 指標2（アクセスの中心）：市区町村の人口を最寄り駅に割り当て、住民への線路上の距離の人口加重平均が最小の駅
  所要時間ではなく距離。列車の速さ・本数・乗り換え時間は考えない

高速道路：地球地図日本 第2.2版の道路のうち「national motorway」（rtt=16）
- 同じ方法で、全節点への道路上の距離の平均が最小の点と、人口加重の平均が最小の点を求める
出力：data/computed_network.csv
"""
import numpy as np
import pandas as pd
import shapefile
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

import geo
from geo import CACHE, DATA

RAIL = CACHE / "ksj" / "N02-24" / "UTF-8"
ROUND = 5  # 約1m


class Graph:
    def __init__(self):
        self.ids, self.xy, self.edges = {}, [], []

    def node(self, lon, lat):
        k = (round(lon, ROUND), round(lat, ROUND))
        if k not in self.ids:
            self.ids[k] = len(self.xy)
            self.xy.append(k)
        return self.ids[k]

    def add_line(self, coords):
        c = np.asarray(coords)
        seg = geo.GEOD.inv(c[:-1, 0], c[:-1, 1], c[1:, 0], c[1:, 1])[2] / 1000
        a, b = self.node(*c[0]), self.node(*c[-1])
        if a != b:
            self.edges.append((a, b, float(seg.sum())))
        return a, b

    def matrix(self):
        n = len(self.xy)
        e = np.array(self.edges)
        i, j, w = e[:, 0].astype(int), e[:, 1].astype(int), np.maximum(e[:, 2], 1e-6)
        m = coo_matrix((np.r_[w, w], (np.r_[i, j], np.r_[j, i])), shape=(n, n)).tocsr()
        return m, np.array(self.xy)


def giant(m):
    _, lab = connected_components(m, directed=False)
    big = np.bincount(lab).argmax()
    return lab == big


def nearest(xy_nodes, lon, lat):
    """各点に最も近い節点（正積図法上の距離）"""
    from scipy.spatial import cKDTree
    nx, ny = geo.TO_XY.transform(xy_nodes[:, 0], xy_nodes[:, 1])
    px, py = geo.TO_XY.transform(np.asarray(lon), np.asarray(lat))
    d, i = cKDTree(np.column_stack([nx, ny])).query(np.column_stack([px, py]))
    return i, d / 1000


def centers(m, xy, cand, targets, weights):
    """候補 cand のうち、targets への距離の（重み付き）平均が最小の節点"""
    dist = dijkstra(m, directed=False, indices=cand)[:, targets]
    w = np.asarray(weights, float)
    mean = (dist * w).sum(axis=1) / w.sum()
    k = mean.argmin()
    order = mean.argsort()
    return cand[k], mean[k], [(cand[o], mean[o]) for o in order[:10]]


def rail():
    g = Graph()
    r = shapefile.Reader(str(RAIL / "N02-24_RailroadSection.shp"), encoding="utf-8")
    for s in r.iterShapes():
        for part in np.split(np.asarray(s.points), s.parts[1:]):
            g.add_line(part)
    st = shapefile.Reader(str(RAIL / "N02-24_Station.shp"), encoding="utf-8")
    stations = []
    for sr in st.iterShapeRecords():
        pts = np.asarray(sr.shape.points)
        a, b = g.add_line(pts)  # 駅の区間も線路の一部として加える
        rec = sr.record
        stations.append(dict(node=a, node2=b, name=rec["N02_005"], line=rec["N02_003"], company=rec["N02_004"],
                             group=rec["N02_005g"], lon=pts[:, 0].mean(), lat=pts[:, 1].mean()))
    st = pd.DataFrame(stations)
    for _, grp in st.groupby("group"):
        nodes = grp["node"].tolist()
        for n in nodes[1:]:
            g.edges.append((nodes[0], n, 0.0))
    m, xy = g.matrix()
    ok = giant(m)
    st = st[ok[st["node"].values]]
    # 駅グループごとに1点（乗り換え駅を1駅として数える）
    sg = st.groupby("group").agg(node=("node", "first"), name=("name", "first"), lon=("lon", "mean"),
                                 lat=("lat", "mean"), lines=("line", lambda s: "・".join(sorted(set(s)))[:80]))
    cand = sg["node"].values
    print(f"鉄道：節点 {len(xy):,}、辺 {len(g.edges):,}、最大の連結成分の駅グループ {len(sg):,}")
    out = []
    k, mean, top = centers(m, xy, cand, cand, np.ones(len(cand)))
    s = sg[sg["node"] == k].iloc[0]
    out.append(dict(id="rail_closeness", name="鉄道網の中心（全駅への距離が最短の駅）", field="交通", category="ネットワークの中心",
                    definition="本州・北海道・九州・四国の鉄道網で、全駅（乗り換え駅は1駅）への線路上の距離の平均が最小の駅",
                    unit_level="駅", year="2024年", lon=s["lon"], lat=s["lat"], method="独自計算", source="ksj_n02",
                    n_units=len(sg), place_name=f"{s['name']}駅（{s['lines']}）",
                    note=f"平均 {mean:.0f} km。上位：" + "、".join(f"{sg[sg['node'] == n].iloc[0]['name']} {d:.0f}km" for n, d in top[:5])))
    muni = pd.read_csv(DATA / "municipalities.csv", dtype={"code": str})
    ni, dkm = nearest(sg[["lon", "lat"]].values, muni["lon"], muni["lat"])
    targets = cand[ni]
    k, mean, top = centers(m, xy, cand, targets, muni["pop"])
    s = sg[sg["node"] == k].iloc[0]
    out.append(dict(id="rail_pop_access", name="鉄道で全住民に最も近い駅", field="交通", category="アクセスの中心",
                    definition="市区町村の人口を人口重心の最寄り駅に割り当て、住民への線路上の距離の人口加重平均が最小の駅",
                    unit_level="駅", year="2024年（人口は2020年）", lon=s["lon"], lat=s["lat"], method="独自計算",
                    source="ksj_n02,estat_census2020,stat_topics135", n_units=len(muni), place_name=f"{s['name']}駅（{s['lines']}）",
                    note=f"人口加重平均 {mean:.0f} km（沖縄県など鉄道網につながらない地域も最寄り駅に割り当てた）。上位："
                    + "、".join(f"{sg[sg['node'] == n].iloc[0]['name']} {d:.0f}km" for n, d in top[:5])))
    return out


def expressway():
    g = Graph()
    r = shapefile.Reader(str(geo.GM_DIR / "roadl_jpn.shp"), encoding="utf-8")
    for sr in r.iterShapeRecords():
        if sr.record["rtt"] != 16:
            continue
        for part in np.split(np.asarray(sr.shape.points), sr.shape.parts[1:]):
            g.add_line(part)
    m, xy = g.matrix()
    ok = np.where(giant(m))[0]
    print(f"高速道路：節点 {len(xy):,}、辺 {len(g.edges):,}、最大の連結成分 {len(ok):,}")
    out = []
    # 節点の分布は道路の形に左右されるため、道路の長さの重みで平均する（各節点に接する辺の長さの半分）
    e = np.array(g.edges)
    seglen = np.zeros(len(xy))
    np.add.at(seglen, e[:, 0].astype(int), e[:, 2] / 2)
    np.add.at(seglen, e[:, 1].astype(int), e[:, 2] / 2)
    k, mean, _ = centers(m, xy, ok, ok, seglen[ok])
    out.append(dict(id="expressway_closeness", name="高速道路網の中心", field="交通", category="ネットワークの中心",
                    definition="高速道路網の上で、網全体（道路の長さで重み付け）への道路上の距離の平均が最小の地点",
                    unit_level="道路の節点", year="2016年（地図の版）", lon=xy[k, 0], lat=xy[k, 1], method="独自計算",
                    source="gsi_globalmap", n_units=len(ok), note=f"平均 {mean:.0f} km"))
    muni = pd.read_csv(DATA / "municipalities.csv", dtype={"code": str})
    ni, dkm = nearest(xy[ok], muni["lon"], muni["lat"])
    k, mean, _ = centers(m, xy, ok, ok[ni], muni["pop"])
    out.append(dict(id="expressway_pop_access", name="高速道路で全住民に最も近い地点", field="交通", category="アクセスの中心",
                    definition="市区町村の人口を最寄りの高速道路の節点に割り当て、住民への道路上の距離の人口加重平均が最小の地点",
                    unit_level="道路の節点", year="2016年（人口は2020年）", lon=xy[k, 0], lat=xy[k, 1], method="独自計算",
                    source="gsi_globalmap,estat_census2020,stat_topics135", n_units=len(muni),
                    note=f"人口加重平均 {mean:.0f} km（高速道路までの距離は含めない）"))
    return out


def main():
    out = rail() + expressway()
    df = pd.DataFrame(out)
    df.to_csv(DATA / "computed_network.csv", index=False)
    print(df[["id", "lon", "lat", "place_name", "note"]].to_string())


if __name__ == "__main__":
    main()
