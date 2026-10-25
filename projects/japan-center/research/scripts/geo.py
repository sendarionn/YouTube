"""日本の中心の計算に使う共通処理

- 国土の形：国土地理院「地球地図日本」第2.2版（1:100万、2016年。市区町村の面、JGD2000）
- 面積の計算：日本の中央付近を中心にしたランベルト正積方位図法（LAEA）に投影し、1km 四方の格子で数える
- 重心：地点を地球の中心からの3次元ベクトルにし、重みを付けて平均した向き（球面上の重心）
- 距離：GRS80 楕円体の測地線距離（pyproj.Geod）
"""
import math
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
import shapefile
import shapely
import shapely.ops
from pyproj import Geod, Transformer
from shapely.geometry import shape

REPO = Path(__file__).resolve().parents[4]
CACHE = Path(os.environ.get("INFOGRAPHIC_CACHE_DIR", REPO / "cache")) / "japan-center"
GM_DIR = CACHE / "gm" / "gm-jpn-all_u_2_2"
DATA = Path(__file__).resolve().parents[1] / "data"

GEOD = Geod(ellps="GRS80")
LAEA = "+proj=laea +lat_0=36 +lon_0=137 +ellps=GRS80 +units=m"
TO_XY = Transformer.from_crs("EPSG:4326", LAEA, always_xy=True)
TO_LL = Transformer.from_crs(LAEA, "EPSG:4326", always_xy=True)

# 北方領土（色丹村・泊村・留夜別村・留別村・紗那村・蘂取村）。地球地図日本の行政コード
NORTHERN_TERRITORIES = {"01695", "01696", "01697", "01698", "01699", "01700"}


@lru_cache
def land_polygons():
    """[(行政コード, shapely の Polygon（経度・緯度）)]。島ごとに1つ"""
    r = shapefile.Reader(str(GM_DIR / "polbnda_jpn.shp"), encoding="utf-8")
    out = []
    for sr in r.iterShapeRecords():
        geom = shape(sr.shape.__geo_interface__)
        for poly in getattr(geom, "geoms", [geom]):
            out.append((sr.record["adm_code"], poly))
    return out


def project(poly):
    return shapely.transform(poly, lambda c: np.column_stack(TO_XY.transform(c[:, 0], c[:, 1])))


def to_vec(lon, lat):
    lon, lat = np.radians(lon), np.radians(lat)
    return np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


def spherical_mean(lon, lat, w=None):
    """重み付きの球面上の重心（経度, 緯度）"""
    v = to_vec(np.asarray(lon, float), np.asarray(lat, float))
    w = np.ones(len(v)) if w is None else np.asarray(w, float)
    m = (v * w[:, None]).sum(axis=0)
    m /= np.linalg.norm(m)
    return math.degrees(math.atan2(m[1], m[0])), math.degrees(math.asin(m[2]))


def stat_bureau_mean(lon, lat, w):
    """統計局の人口重心の式（経度は cos(緯度) で重み付け、緯度は単純な加重平均）"""
    lon, lat, w = (np.asarray(a, float) for a in (lon, lat, w))
    c = np.cos(np.radians(lat))
    return float((w * lon * c).sum() / (w * c).sum()), float((w * lat).sum() / w.sum())


def distance_km(lon1, lat1, lon2, lat2):
    return GEOD.inv(lon1, lat1, lon2, lat2)[2] / 1000


def geometric_median(lon, lat, w, iters=500):
    """重み付きの測地線距離の合計が最小になる地点（Weiszfeld 法。LAEA 上で反復し、測地線距離で確認）"""
    x, y = TO_XY.transform(np.asarray(lon, float), np.asarray(lat, float))
    w = np.asarray(w, float)
    px, py = (w * x).sum() / w.sum(), (w * y).sum() / w.sum()
    for _ in range(iters):
        d = np.hypot(x - px, y - py)
        d = np.where(d < 1, 1, d)
        nx, ny = (w * x / d).sum() / (w / d).sum(), (w * y / d).sum() / (w / d).sum()
        if math.hypot(nx - px, ny - py) < 0.1:
            break
        px, py = nx, ny
    mlon, mlat = TO_LL.transform(px, py)
    return float(mlon), float(mlat)


def weighted_sum_distance(lon0, lat0, lon, lat, w):
    """地点から各点までの測地線距離（km）の重み付き平均"""
    n = len(lon)
    d = GEOD.inv(np.full(n, lon0), np.full(n, lat0), np.asarray(lon, float), np.asarray(lat, float))[2] / 1000
    return float((d * np.asarray(w, float)).sum() / np.sum(w))


def land_grid(step_m=1000, exclude=()):
    """国土を LAEA 上の step_m 四方の格子で覆い、陸地の格子の中心（経度, 緯度, 行政コード）を返す

    格子は正積図法上で同じ面積なので、格子の数が面積に比例する
    """
    lons, lats, codes = [], [], []
    for code, poly in land_polygons():
        if code in exclude:
            continue
        p = project(poly)
        minx, miny, maxx, maxy = p.bounds
        xs = np.arange(math.floor(minx / step_m) * step_m + step_m / 2, maxx, step_m)
        ys = np.arange(math.floor(miny / step_m) * step_m + step_m / 2, maxy, step_m)
        if len(xs) == 0 or len(ys) == 0:
            continue
        gx, gy = np.meshgrid(xs, ys)
        gx, gy = gx.ravel(), gy.ravel()
        inside = shapely.contains_xy(p, gx, gy)
        if not inside.any():
            continue
        lo, la = TO_LL.transform(gx[inside], gy[inside])
        lons.append(lo)
        lats.append(la)
        codes.append(np.full(inside.sum(), code))
    return np.concatenate(lons), np.concatenate(lats), np.concatenate(codes)


@lru_cache
def municipality_index():
    """地点がどの市区町村の陸地にあるかを調べるための索引（地球地図日本、2014年の境界）"""
    polys = land_polygons()
    tree = shapely.STRtree([p for _, p in polys])
    return polys, tree


def land_code(lon, lat):
    """地点を含む市区町村の行政コード。陸地でなければ None"""
    polys, tree = municipality_index()
    pt = shapely.Point(lon, lat)
    for i in tree.query(pt, predicate="within"):
        return polys[i][0]
    return None


def nearest_land_km(lon, lat):
    """地点から最も近い陸地までの距離（km、概算）"""
    polys, tree = municipality_index()
    pt = shapely.Point(lon, lat)
    i = tree.nearest(pt)
    q = shapely.ops.nearest_points(polys[i][1], pt)[0]
    return distance_km(lon, lat, q.x, q.y)


def dms(v):
    d = int(abs(v))
    m = int((abs(v) - d) * 60)
    s = (abs(v) - d - m / 60) * 3600
    return f"{d}度{m:02d}分{s:05.2f}秒"

