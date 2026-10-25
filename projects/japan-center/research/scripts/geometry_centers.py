"""国土の形から決まる中心（幾何学的中心）を計算する

- 面積重心：国土を正積図法上の1km 四方の格子で覆い、陸地の格子を同じ重みで数えた重心（統計局の人口重心と同じ式）
- 外接範囲の中点：東西南北端の経度・緯度の中点（国土地理院の公表値）
- 海岸線の重心：海岸線（島の外周）を長さで重み付けした重心
- 海から最も遠い地点：陸地の点のうち、最も近い海岸線までの距離が最大の点
国土の形は地球地図日本（1:100万）なので、細かい海岸線や小さな島は省略されている（methodology.md）
出力：data/computed_geometry.csv
"""
import numpy as np
import pandas as pd
import shapely

import geo
from geo import DATA

# 国土地理院「日本の東西南北端点の経度緯度」（2019-06-01 更新）。度分秒
EXTREMES = {
    "east": ("南鳥島", 153 + 59 / 60 + 12 / 3600, 24 + 16 / 60 + 59 / 3600),
    "west": ("与那国島", 122 + 55 / 60 + 57 / 3600, 24 + 27 / 60 + 5 / 3600),
    "south": ("沖ノ鳥島", 136 + 4 / 60 + 11 / 3600, 20 + 25 / 60 + 31 / 3600),
    "north": ("択捉島", 148 + 45 / 60 + 8 / 3600, 45 + 33 / 60 + 26 / 3600),
}


def islands():
    """市区町村の面を合わせた島（正積図法の座標、面積の大きい順）。先頭の4つが本州・北海道・九州・四国"""
    union = shapely.union_all([geo.project(p) for _, p in geo.land_polygons()]).buffer(0)
    return sorted(getattr(union, "geoms", [union]), key=lambda g: -g.area)


def unproject(poly):
    return shapely.transform(poly, lambda c: np.column_stack(geo.TO_LL.transform(c[:, 0], c[:, 1])))


def coast_centroid(polys):
    lons, lats, ws = [], [], []
    for _, p in polys:
        c = np.asarray(p.exterior.coords)
        a, b = c[:-1], c[1:]
        seg = geo.GEOD.inv(a[:, 0], a[:, 1], b[:, 0], b[:, 1])[2]
        lons.append((a[:, 0] + b[:, 0]) / 2)
        lats.append((a[:, 1] + b[:, 1]) / 2)
        ws.append(seg)
    lon, lat, w = np.concatenate(lons), np.concatenate(lats), np.concatenate(ws)
    return geo.stat_bureau_mean(lon, lat, w), geo.spherical_mean(lon, lat, w), w.sum() / 1000


def farthest_from_sea(parts, step_m=500):
    """島ごとに格子点から海岸線（島の外周）までの距離を測り、最大の点を返す。湖は海として扱わない"""
    best = (0, None)
    for part in parts:
        if part.area < 1e9:  # 1,000 km2 未満の島は候補にならない
            continue
        coast = shapely.LinearRing(part.exterior.coords)
        minx, miny, maxx, maxy = part.bounds
        xs, ys = np.meshgrid(np.arange(minx, maxx, step_m * 4), np.arange(miny, maxy, step_m * 4))
        xs, ys = xs.ravel(), ys.ravel()
        inside = shapely.contains_xy(part, xs, ys)
        xs, ys = xs[inside], ys[inside]
        d = shapely.distance(shapely.points(xs, ys), coast)
        i = d.argmax()
        # 最大の点の周りを細かく探す
        gx, gy = np.meshgrid(np.arange(xs[i] - 4 * step_m, xs[i] + 4 * step_m, step_m / 5),
                             np.arange(ys[i] - 4 * step_m, ys[i] + 4 * step_m, step_m / 5))
        gx, gy = gx.ravel(), gy.ravel()
        d2 = shapely.distance(shapely.points(gx, gy), coast)
        j = d2.argmax()
        if d2[j] > best[0]:
            best = (d2[j], (gx[j], gy[j]), coast)
    dist, (x, y), coast = best
    lon, lat = geo.TO_LL.transform(x, y)
    # 測地線距離で確認する（正積図法上の距離はわずかにゆがむ）
    q = shapely.ops.nearest_points(coast, shapely.Point(x, y))[0]
    qlon, qlat = geo.TO_LL.transform(q.x, q.y)
    return float(lon), float(lat), dist / 1000, geo.distance_km(lon, lat, qlon, qlat), (float(qlon), float(qlat))


def main():
    rows = []
    lo, la, codes = geo.land_grid(1000)
    nt = np.isin(codes, list(geo.NORTHERN_TERRITORIES))
    print(f"国土の面積（格子の数）：{len(lo):,} km2（北方領土を除くと {(~nt).sum():,} km2）")
    variants = [
        ("area_all", "国土の面積重心", "北方領土・離島を含む全国土（地球地図日本の陸地）", np.ones(len(lo), bool)),
        ("area_excl_nt", "国土の面積重心（北方領土を除く）", "北方領土（色丹・国後・択捉・歯舞）を除く国土", ~nt),
    ]
    parts = islands()
    mains = parts[:4]
    for cid, name, definition, m in variants:
        x, y = geo.stat_bureau_mean(lo[m], la[m], np.ones(m.sum()))
        sx, sy = geo.spherical_mean(lo[m], la[m])
        rows.append(dict(id=cid, name=name, field="地理・国土", category="幾何学的中心", definition=definition,
                         unit_level="1km 格子", year="2016年（地図の版）", lon=x, lat=y, method="独自計算",
                         source="gsi_globalmap", n_units=int(m.sum()), alt_km=geo.distance_km(x, y, sx, sy)))
    # 主要4島だけの面積重心
    xy = np.column_stack(geo.TO_XY.transform(lo, la))
    m4 = np.zeros(len(lo), bool)
    for p in mains:
        m4 |= shapely.contains_xy(p, xy[:, 0], xy[:, 1])
    x, y = geo.stat_bureau_mean(lo[m4], la[m4], np.ones(m4.sum()))
    sx, sy = geo.spherical_mean(lo[m4], la[m4])
    rows.append(dict(id="area_main4", name="主要4島の面積重心", field="地理・国土", category="幾何学的中心",
                     definition="本州・北海道・九州・四国の4島だけの面積重心（ほかの島を除く）", unit_level="1km 格子",
                     year="2016年（地図の版）", lon=x, lat=y, method="独自計算", source="gsi_globalmap",
                     n_units=int(m4.sum()), alt_km=geo.distance_km(x, y, sx, sy)))

    e = EXTREMES
    rows.append(dict(id="bbox_mid", name="東西南北端の中点", field="地理・国土", category="幾何学的中心",
                     definition="最東端（南鳥島）と最西端（与那国島）の経度の中間、最北端（択捉島）と最南端（沖ノ鳥島）の緯度の中間",
                     unit_level="地点", year="2019年（端点の更新）", lon=(e["east"][1] + e["west"][1]) / 2,
                     lat=(e["north"][2] + e["south"][2]) / 2, method="独自計算（公表値から）", source="gsi_extremes"))
    # 主要4島の外接範囲
    b = np.array([unproject(p).bounds for p in mains])
    rows.append(dict(id="bbox_mid_main4", name="主要4島の東西南北端の中点", field="地理・国土", category="幾何学的中心",
                     definition="主要4島（本州・北海道・九州・四国）の東西南北端の経度・緯度の中間",
                     unit_level="地点", year="2016年（地図の版）", lon=(b[:, 0].min() + b[:, 2].max()) / 2,
                     lat=(b[:, 1].min() + b[:, 3].max()) / 2, method="独自計算", source="gsi_globalmap",
                     note=f"東端 {b[:, 2].max():.3f}、西端 {b[:, 0].min():.3f}、北端 {b[:, 3].max():.3f}、南端 {b[:, 1].min():.3f}（地球地図日本の陸地）"))

    # 海岸線：島ごとに市区町村の面を合わせ、外周を海岸線とする
    (cx, cy), (sx, sy), total = coast_centroid([(None, unproject(p)) for p in parts])
    rows.append(dict(id="coastline", name="海岸線の重心", field="地理・国土", category="幾何学的中心",
                     definition="すべての島の海岸線（外周）を長さで重み付けした重心", unit_level="海岸線の線分",
                     year="2016年（地図の版）", lon=cx, lat=cy, method="独自計算", source="gsi_globalmap",
                     n_units=len(parts), alt_km=geo.distance_km(cx, cy, sx, sy),
                     note=f"海岸線の総延長 {total:,.0f} km（1:100万の地図による。縮尺が大きいほど長くなる）"))

    lon, lat, d_proj, d_geod, q = farthest_from_sea(parts)
    rows.append(dict(id="farthest_from_sea", name="海から最も遠い地点", field="地理・国土", category="幾何学的中心",
                     definition="陸地のうち、最も近い海岸線までの距離が最大になる地点（到達不能極）", unit_level="200m 格子",
                     year="2016年（地図の版）", lon=lon, lat=lat, method="独自計算", source="gsi_globalmap",
                     note=f"最も近い海岸線まで {d_geod:.1f} km（最寄りの海岸 {q[0]:.3f}, {q[1]:.3f}）"))
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "computed_geometry.csv", index=False)
    print(df[["id", "lon", "lat", "alt_km", "note"]].to_string())


if __name__ == "__main__":
    main()
