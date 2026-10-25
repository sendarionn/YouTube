"""動画の地図を描く部品

- 投影は研究と同じランベルト正積方位図法（北緯36度・東経137度中心、research/scripts/geo.py）。座標は km（北が上）
- 陸地・都道府県界・鉄道は研究と同じデータ（地球地図日本、国土数値情報 N02-24）から作り、cache/japan-center/video/ に保存する
- カメラ（中心の x・y と 1px あたりの km）をキーフレームで補間し、ズームは対数で補間する（拡大の速さを一定に見せる）
- 点の記号は分類ごとに色と形を変える（研究の地図 centers_map.html と同じ対応）
"""
import math
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
REPO = PROJECT.parents[1]
sys.path.insert(0, str(PROJECT / "research" / "scripts"))
sys.path.insert(0, str(REPO))

from tools.infographic.canvas import ease, hexrgb, mix  # noqa: E402

GEOM = REPO / "cache" / "japan-center" / "video" / "geom.pkl"

SEA = hexrgb("E4EBF0")
LAND = hexrgb("F6F5F2")
COAST = hexrgb("A9B3BC")
PREF = hexrgb("CDD3D9")
RAIL = hexrgb("7C8A96")

# 分類：(色, 形)。動画の中で意味を変えない
STYLE = {
    "幾何学的中心": (hexrgb("2E6BD1"), "diamond"),
    "分布の重心": (hexrgb("D9822B"), "circle"),
    "最大集積地": (hexrgb("8C6BB8"), "square"),
    "ネットワークの中心": (hexrgb("2A9D8F"), "square"),
    "アクセスの中心": (hexrgb("6E8B2E"), "triangle"),
    "制度的中心": (hexrgb("B5472F"), "triangle"),
    "制度的・歴史的中心": (hexrgb("B5472F"), "triangle"),
    "象徴的・通称的中心": (hexrgb("B8901E"), "star"),
}
# 動画で示す7つの種類（制度的中心と制度的・歴史的中心は1つにまとめる）
TYPES = [("幾何学的中心", "国土の形から求める中心", ["幾何学的中心"]),
         ("分布の重心", "量の分布から求める重心", ["分布の重心"]),
         ("最大集積地", "量が最も多い地域", ["最大集積地"]),
         ("ネットワークの中心", "交通網の中心", ["ネットワークの中心"]),
         ("アクセスの中心", "距離の合計が最小の地点", ["アクセスの中心"]),
         ("制度的・歴史的中心", "法律・歴史で決まる中心", ["制度的中心", "制度的・歴史的中心"]),
         ("象徴的・通称的中心", "自治体などが名乗る中心", ["象徴的・通称的中心"])]


def build_geometry():
    """陸地（島）・都道府県・鉄道を正積図法の km 座標にして保存する"""
    import shapefile
    import shapely
    import shapely.geometry

    import geo
    from geometry_centers import islands

    out = {"islands": [], "prefs": {}, "rail": []}
    for p in islands():
        if p.area < 0.5e6:
            continue
        fine = np.asarray(p.simplify(120).exterior.coords) / 1000
        coarse = np.asarray(p.simplify(800).exterior.coords) / 1000
        out["islands"].append({"area": p.area / 1e6, "fine": fine.astype(np.float32), "coarse": coarse.astype(np.float32)})
    # 都道府県の境界：市区町村の面を都道府県ごとに合わせる
    by_pref = {}
    for code, poly in geo.land_polygons():
        by_pref.setdefault(code[:2], []).append(geo.project(poly))
    for pc, polys in by_pref.items():
        u = shapely.union_all(polys).buffer(0)
        parts = [g for g in getattr(u, "geoms", [u]) if g.area > 2e6]
        out["prefs"][pc] = [(np.asarray(g.simplify(150).exterior.coords) / 1000).astype(np.float32) for g in parts]
    # 湖（地球地図日本の内水面のうち 20 km² 以上。陸地の上に海の色で塗る）
    out["lakes"] = []
    lk = shapefile.Reader(str(geo.GM_DIR / "inwatera_jpn.shp"), encoding="utf-8")
    for sh in lk.iterShapes():
        g = geo.project(shapely.geometry.shape(sh.__geo_interface__))
        for part in getattr(g, "geoms", [g]):
            if part.area > 20e6:
                out["lakes"].append((np.asarray(part.simplify(120).exterior.coords) / 1000).astype(np.float32))
    # 市区町村の面（最大集積地の地域を塗るため。港区・高山市）
    out["munis"] = {}
    for code, poly in geo.land_polygons():
        if code in ("13103", "21203"):
            g = geo.project(poly)
            out["munis"].setdefault(code, []).append((np.asarray(g.simplify(50).exterior.coords) / 1000).astype(np.float32))
    # 鉄道（研究のネットワークと同じ N02-24）
    r = shapefile.Reader(str(geo.CACHE / "ksj" / "N02-24" / "UTF-8" / "N02-24_RailroadSection.shp"), encoding="utf-8")
    for s in r.iterShapes():
        for part in np.split(np.asarray(s.points), s.parts[1:]):
            x, y = geo.TO_XY.transform(part[:, 0], part[:, 1])
            line = shapely.LineString(np.column_stack([x, y])).simplify(200)
            out["rail"].append((np.asarray(line.coords) / 1000).astype(np.float32))
    GEOM.parent.mkdir(parents=True, exist_ok=True)
    GEOM.write_bytes(pickle.dumps(out))
    return out


_G = None


def geometry():
    global _G
    if _G is None:
        _G = pickle.loads(GEOM.read_bytes()) if GEOM.exists() else build_geometry()
    return _G


def project(lon, lat):
    import geo

    x, y = geo.TO_XY.transform(lon, lat)
    return x / 1000, y / 1000


class Camera:
    """画面の中心（km）と縮尺（1px あたり km）。画面の (cx, cy) に地図の (x, y) を置く"""

    def __init__(self, x, y, kmpp, W=1920, H=1080, cx=None, cy=None):
        self.x, self.y, self.kmpp = x, y, kmpp
        self.cx, self.cy = cx if cx is not None else W / 2, cy if cy is not None else H / 2

    def px(self, x, y):
        return float(self.cx + (x - self.x) / self.kmpp), float(self.cy - (y - self.y) / self.kmpp)

    def pxa(self, a):
        return np.column_stack([self.cx + (a[:, 0] - self.x) / self.kmpp, self.cy - (a[:, 1] - self.y) / self.kmpp])


def fit(box, W=1920, H=1080, top=150, bottom=110, side=120, cx=None):
    """地図上の範囲 (x0, y0, x1, y1)（km）が画面の余白の内側に収まるカメラ"""
    x0, y0, x1, y1 = box
    aw, ah = W - 2 * side, H - top - bottom
    kmpp = max((x1 - x0) / aw, (y1 - y0) / ah)
    return Camera((x0 + x1) / 2, (y0 + y1) / 2, kmpp, W, H, cx if cx is not None else W / 2, top + ah / 2)


def lerp_cam(a, b, p):
    """カメラの補間（中心は線形、縮尺は対数）。p は 0〜1（ease は呼び出し側で掛けない）"""
    q = ease(p)
    k = math.exp(math.log(a.kmpp) + (math.log(b.kmpp) - math.log(a.kmpp)) * q)
    # 拡大中に目標が画面の外へ流れないよう、中心は縮尺の変化に合わせて補間する
    if abs(math.log(b.kmpp / a.kmpp)) > 1e-6:
        w = (1 / k - 1 / a.kmpp) / (1 / b.kmpp - 1 / a.kmpp)
    else:
        w = q
    return Camera(a.x + (b.x - a.x) * w, a.y + (b.y - a.y) * w, k, cx=a.cx + (b.cx - a.cx) * q, cy=a.cy + (b.cy - a.cy) * q)


def cam_at(keys, t):
    """keys：[(時刻, Camera)] の昇順。時刻 t のカメラ。各区間は (t0, cam0)→(t1, cam1) を ease で補間"""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, c0), (t1, c1) in zip(keys, keys[1:]):
        if t < t1:
            return lerp_cam(c0, c1, (t - t0) / (t1 - t0)) if t1 > t0 else c1
        if t1 == t0:
            continue
    return keys[-1][1]


def _poly(cv, p, fill=None, outline=None, width=1.0):
    """画面座標の配列（N×2）を、スーパーサンプリングの倍率を掛けて直接描く（大量の頂点を速く描くため）"""
    k = cv.d.k
    cv.d._d.polygon((np.asarray(p, np.float64) * k).ravel().tolist(), fill=fill, outline=outline,
                    width=max(1, int(round(width * k))) if outline else 0)


def _line(cv, p, fill, width=1.0, closed=False):
    k = cv.d.k
    a = np.asarray(p, np.float64) * k
    if closed:
        a = np.vstack([a, a[:1]])
    cv.d._d.line(a.ravel().tolist(), fill=fill, width=max(1, int(round(width * k))), joint="curve")


def draw_base(cv, cam, prefs=True, rail=0.0, highlight_pref=None, highlight_alpha=0.0, fine=None):
    """海・陸地・都道府県界（・鉄道）"""
    W, H = cv.th.width, cv.th.height
    cv.rect((0, 0, W, H), SEA)
    g = geometry()
    fine = cam.kmpp < 1.2 if fine is None else fine
    vx0, vx1 = cam.x - (cam.cx + 50) * cam.kmpp, cam.x + (W - cam.cx + 50) * cam.kmpp
    vy0, vy1 = cam.y - (H - cam.cy + 50) * cam.kmpp, cam.y + (cam.cy + 50) * cam.kmpp
    for isl in g["islands"]:
        a = isl["fine" if fine else "coarse"]
        if a[:, 0].max() < vx0 or a[:, 0].min() > vx1 or a[:, 1].max() < vy0 or a[:, 1].min() > vy1:
            continue
        if isl["area"] / cam.kmpp ** 2 < 2:  # 画面上で 2px² 未満の島は描かない
            continue
        _poly(cv, cam.pxa(a), fill=LAND)
    if cam.kmpp < 3:
        for a in g.get("lakes", []):
            if a[:, 0].max() < vx0 or a[:, 0].min() > vx1 or a[:, 1].max() < vy0 or a[:, 1].min() > vy1:
                continue
            _poly(cv, cam.pxa(a), fill=SEA)
            _line(cv, cam.pxa(a), COAST, 1.0, closed=True)
    if highlight_pref and highlight_alpha > 0:
        for a in g["prefs"][highlight_pref]:
            _poly(cv, cam.pxa(a), fill=mix(hexrgb("FBE3C8"), LAND, highlight_alpha))
    coast_after = prefs and cam.kmpp < 2.5
    if not coast_after:
        for isl in g["islands"]:
            a = isl["fine" if fine else "coarse"]
            if a[:, 0].max() < vx0 or a[:, 0].min() > vx1 or a[:, 1].max() < vy0 or a[:, 1].min() > vy1:
                continue
            if isl["area"] / cam.kmpp ** 2 < 2:
                continue
            _line(cv, cam.pxa(a), COAST, 1.2, closed=True)
    if coast_after:
        al = min(1.0, (2.5 - cam.kmpp) / 1.0)
        col = mix(PREF, LAND, al)
        for pc, parts in g["prefs"].items():
            for a in parts:
                if a[:, 0].max() < vx0 or a[:, 0].min() > vx1 or a[:, 1].max() < vy0 or a[:, 1].min() > vy1:
                    continue
                _line(cv, cam.pxa(a), col, 1.2, closed=True)
        # 海岸線を上から描き直す（都道府県界の線が海岸に重ならないように）
        for isl in g["islands"]:
            a = isl["fine" if fine else "coarse"]
            if a[:, 0].max() < vx0 or a[:, 0].min() > vx1 or a[:, 1].max() < vy0 or a[:, 1].min() > vy1:
                continue
            if isl["area"] / cam.kmpp ** 2 < 2:
                continue
            _line(cv, cam.pxa(a), COAST, 1.2, closed=True)
    if rail > 0:
        col = mix(RAIL, LAND, rail)
        for a in g["rail"]:
            if a[:, 0].max() < vx0 or a[:, 0].min() > vx1 or a[:, 1].max() < vy0 or a[:, 1].min() > vy1:
                continue
            _line(cv, cam.pxa(a), col, 1.6)


_PREF_LABELS = None


def pref_labels(cv, cam, alpha=1.0, size=28, avoid=()):
    """都道府県名（拡大した地図の手がかり）。位置は統計局の都道府県の人口重心（陸上にある）"""
    global _PREF_LABELS
    if alpha <= 0 or cam.kmpp > 1.2:
        return
    if _PREF_LABELS is None:
        import csv
        data = PROJECT / "research" / "data"
        names = {}
        for r in csv.DictReader((data / "municipalities.csv").open(encoding="utf-8")):
            names[r["code"][:2]] = r["pref"]
        from weighted_centers import centroid_table
        t = centroid_table()
        _PREF_LABELS = [(names[c[:2]], *project(t.loc[c, "lon"], t.loc[c, "lat"])) for c in t.index
                        if c.endswith("000") and c != "00000"]
    a = alpha * min(1.0, (1.2 - cam.kmpp) / 0.4)
    for name, x, y in _PREF_LABELS:
        sx, sy = cam.px(x, y)
        if any(math.hypot(sx - ax, sy - ay) < ar for ax, ay, ar in avoid):
            continue
        if 150 < sx < cv.th.width - 150 and 160 < sy < cv.th.height - 140:
            cv.text((sx, sy), name, size, color=hexrgb("8A949E"), alpha=a, anchor="mm")


def scale_bar(cv, cam, alpha=1.0, x=120, y=930):
    """縮尺（km）。画面上で 120〜300px になるきりのよい長さ"""
    if alpha <= 0:
        return
    for km in (1, 2, 5, 10, 20, 50, 100, 200, 500):
        if km / cam.kmpp >= 120:
            break
    w = km / cam.kmpp
    col = cv.th.text
    cv.rect((x - 12, y - 40, x + w + 12, y + 18), (255, 255, 255), alpha, radius=8)
    cv.line([(x, y), (x + w, y)], col, 3, alpha)
    cv.line([(x, y - 10), (x, y + 6)], col, 3, alpha)
    cv.line([(x + w, y - 10), (x + w, y + 6)], col, 3, alpha)
    cv.text((x + w / 2, y - 14), f"{km}km", 24, color=col, alpha=alpha, anchor="md")


def region(cv, cam, polys, color, alpha):
    """地域（都道府県・市区町村）を塗る。点の記号と区別するため、塗りと輪郭で示す"""
    if alpha <= 0:
        return
    for a in polys:
        p = cam.pxa(a)
        _poly(cv, p, fill=mix(color, LAND, 0.35 * alpha))
        _line(cv, p, mix(color, LAND, alpha), 2.5, closed=True)


def marker(cv, x, y, category, alpha=1.0, r=11, ring=0.0, bg=LAND):
    """中心点の記号（画面座標）。ring は出現時の輪（0〜1 で広がって消える）"""
    if alpha <= 0:
        return
    color, shape = STYLE[category]
    c = mix(color, bg, alpha)
    edge = mix((255, 255, 255), bg, alpha)
    d = cv.d
    if 0 < ring < 1:
        rr = r * (1.4 + 2.6 * ease(ring))
        d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=mix(color, bg, (1 - ring) * 0.8), width=2.5)
    if shape == "circle":
        d.ellipse((x - r, y - r, x + r, y + r), fill=c, outline=edge, width=2.5)
    elif shape == "square":
        s = r * 0.9
        d.rectangle((x - s, y - s, x + s, y + s), fill=c, outline=edge, width=2.5)
    elif shape == "diamond":
        s = r * 1.25
        d.polygon([(x, y - s), (x + s, y), (x, y + s), (x - s, y)], fill=c, outline=edge, width=2.5)
    elif shape == "triangle":
        s = r * 1.25
        d.polygon([(x, y - s), (x + s * 1.05, y + s * 0.75), (x - s * 1.05, y + s * 0.75)], fill=c, outline=edge, width=2.5)
    elif shape == "star":
        pts = []
        for i in range(10):
            a = math.pi / 5 * i - math.pi / 2
            rr = r * (1.45 if i % 2 == 0 else 0.62)
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        d.polygon(pts, fill=c, outline=edge, width=2.0)


def label(cv, x, y, text, sub=None, dx=24, dy=0, alpha=1.0, size=30, anchor="l", color=None, leader=True):
    """点のラベル（白い札と引き出し線）。anchor は札を点の右（l）・左（r）に置く"""
    if alpha <= 0:
        return
    th = cv.th
    s2 = size - 8
    w = max(cv.text_width(text, size, True), cv.text_width(sub, s2) if sub else 0) + 28
    h = size + 20 + (s2 + 8 if sub else 0)
    bx = x + dx if anchor == "l" else x + dx - w
    by = y + dy - h / 2
    if leader and (abs(dx) > 30 or abs(dy) > 10):
        ex = bx if anchor == "l" else bx + w
        cv.line([(x, y), (ex, y + dy)], th.sub, 2, alpha)
    cv.rect((bx, by, bx + w, by + h), (255, 255, 255), alpha, radius=8)
    cv.text((bx + 14, by + 10), text, size, bold=True, color=color, alpha=alpha)
    if sub:
        cv.text((bx + 14, by + 10 + size + 8), sub, s2, color=th.sub, alpha=alpha)
    return (bx, by, bx + w, by + h)


def dashed(cv, pts, color, width=2.5, dash=12, gap=9, alpha=1.0):
    """破線（経線・推計の線）。折れ線の頂点をまたいで、破線の周期を続ける"""
    if alpha <= 0:
        return
    pts = np.asarray(pts, float).tolist()
    period = dash + gap
    pos = 0.0  # 折れ線の始点からの長さ
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        if L == 0:
            continue
        s = 0.0
        while s < L:
            phase = (pos + s) % period
            if phase < dash:
                e = min(L, s + dash - phase)
                cv.line([(x0 + (x1 - x0) * s / L, y0 + (y1 - y0) * s / L), (x0 + (x1 - x0) * e / L, y0 + (y1 - y0) * e / L)],
                        color, width, alpha)
                s = e
            else:
                s = min(L, s + period - phase)
        pos += L


if __name__ == "__main__":
    g = build_geometry()
    print(len(g["islands"]), "島", len(g["prefs"]), "都道府県", len(g["rail"]), "鉄道", sum(len(i["fine"]) for i in g["islands"]), "頂点")
