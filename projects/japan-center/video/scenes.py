"""動画「日本の中心はどこ？」の台本と画面（research-v1）

方針（AGENTS.md「ナレーションと映像の役割分担」、DESIGN.md、video/brief-video.md）
- 地図が主役。点の位置は研究の座標（research/data/centers.csv）を研究と同じ正積図法で置く（mapdraw.py）
- 種類ごとに色と形を変え、点・線（経線）・地域（最大集積地）を描き分ける
- ナレーションは要点と意味。読み上げる数値は結論の中心になるもの（97個、約29キロ、約115キロ、2人など）に限る
- 「重心」と「最も多い場所」を区別する。推計（2025年の人口重心）は推計と言う
- 数値はすべて research/data/ から読み、load_numbers の確認（assert）でナレーションと照合する
"""
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

VIDEO = Path(__file__).resolve().parent
PROJECT = VIDEO.parent
REPO = PROJECT.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(VIDEO))

import mapdraw as M  # noqa: E402
from tools.infographic import svgicons  # noqa: E402
from tools.infographic.canvas import ease, hexrgb, mix, ramp  # noqa: E402
from tools.infographic.video import Line, Scene  # noqa: E402

DATA = PROJECT / "research" / "data"
W, H = 1920, 1080
WHITE = (255, 255, 255)

# 読み上げ用の読み（VOICEVOX が読み誤りやすい語。字幕は元の表記）
YOMI = [("七宗町", "ひちそうちょう"), ("早川町", "ハヤカワチョウ"), ("関市", "せきし"), ("飯田市", "いいだし"),
        ("辰野町", "たつのまち"), ("西脇市", "にしわきし"), ("渋川市", "しぶかわし"), ("佐野市", "さのし"),
        ("佐久市", "さくし"), ("択捉島", "えとろふとう"), ("与那国島", "よなぐにじま"), ("沖ノ鳥島", "おきのとりしま"),
        ("南鳥島", "みなみとりしま"), ("経緯度原点", "けいいどげんてん"), ("水準原点", "すいじゅんげんてん"),
        ("子午線", "しごせん"), ("平城京", "へいじょうきょう"), ("平安京", "へいあんきょう"), ("日本橋", "にほんばし"),
        ("97個", "きゅうじゅうななこ"), ("48個", "よんじゅうはっこ"), ("28個", "にじゅうはっこ"), ("15個", "じゅうごこ"),
        ("国勢調査", "こくせいちょうさ"), ("重心", "じゅうしん"), ("日本のへそ", "にっぽんのへそ"),
        ("値です", "あたいです"), ("値では", "あたいでは"), ("東経", "とうけい"), ("北緯", "ほくい"), ("中央値", "ちゅうおうち"), ("従事", "じゅうじ")]


def yomi(text):
    for a, b in YOMI:
        text = text.replace(a, b)
    return text


def read(name):
    return list(csv.DictReader((DATA / name).open(encoding="utf-8")))


def load_numbers():
    N = {}
    C = {}
    for r in read("centers.csv"):
        if r["lat"]:
            r["x"], r["y"] = M.project(float(r["lon"]), float(r["lat"]))
        C[r["id"]] = r
    N["C"] = C
    N["n_all"] = len(C)
    assert N["n_all"] == 97
    cats = [r["category"] for r in C.values()]
    N["types"] = [(name, desc, sum(cats.count(k) for k in keys)) for name, desc, keys in M.TYPES]
    assert sum(n for *_, n in N["types"]) == 97
    N["n_points"] = sum(1 for r in C.values() if r["lat"] and r["id"] != "std_meridian")
    N["n_regions"] = sum(1 for r in C.values() if not r["lat"])  - 1  # 経線を除く
    assert (N["n_points"], N["n_regions"]) == (86, 10)

    pa = read("analysis_pairs.csv")
    pair = {(r["a"], r["b"]): float(r["km"]) for r in pa}
    N["nt_diff"] = pair[("area_all", "area_excl_nt")]
    assert round(N["nt_diff"]) == 15  # 「15キロほど」
    hist = read("pop_centroid_history.csv")
    N["hist"] = [(int(r["year"]), r["method"], *M.project(float(r["lon"]), float(r["lat"]))) for r in hist]
    a, b = hist[0], hist[-1]
    import geo
    N["hist_km"] = geo.distance_km(float(a["lon"]), float(a["lat"]), float(b["lon"]), float(b["lat"]))
    assert round(N["hist_km"]) == 29  # 「およそ29キロ」
    e = C["pop2025_est"]
    N["est_km"] = geo.distance_km(float(b["lon"]), float(b["lat"]), float(e["lon"]), float(e["lat"]))
    assert round(N["est_km"]) == 2 and "七宗町" in e["located"]
    fs = C["farthest_from_sea"]
    N["sea_km"] = float(fs["note"].split("まで ")[1].split(" km")[0])
    N["sea_coast"] = tuple(float(v) for v in fs["note"].split("最寄りの海岸 ")[1].rstrip("）").split(", "))
    assert round(N["sea_km"]) == 115

    # 追加検証①
    vi = read("verify_indicators.csv")
    dist = [r for r in vi]
    N["n_dist"] = len(dist)
    N["n_gifu"] = sum(r["gifu"] == "True" for r in dist)
    N["n_popshape"] = sum(1 for r in dist if r["r_pop"] and float(r["r_pop"]) >= 0.9 and r["id"] != "pop2020_recalc")
    vg = read("verify_groups.csv")
    N["n_groups"], N["n_groups_gifu"] = len(vg), sum(r["rep_gifu"] == "True" for r in vg)
    sys.path.insert(0, str(PROJECT / "research" / "scripts"))
    from verify_concentration import REPRESENTATIVE
    N["fields"] = [(f, rid, C[rid]["pref"] == "岐阜県") for f, rid in sorted(REPRESENTATIVE.items())]
    N["n_fields"], N["n_fields_gifu"] = len(N["fields"]), sum(g for *_, g in N["fields"])
    ring = {int(r["radius_km"]): float(r["gifu_land_share"]) for r in read("verify_points.csv")}
    N["ring50"] = ring[50]
    assert (N["n_dist"], N["n_gifu"]) == (48, 28) and N["n_popshape"] == 15
    assert (N["n_groups"], N["n_groups_gifu"]) == (27, 14) and (N["n_fields"], N["n_fields_gifu"]) == (15, 10)
    assert round(N["ring50"], 1) == 0.8  # 「およそ8割」
    N["r_pop"] = sorted([(r["name"], float(r["r_pop"]), r["gifu"] == "True") for r in dist if r["r_pop"]
                         and r["id"] != "pop2020_recalc"], key=lambda x: -x[1])

    # 追加検証②
    ict = json.loads((DATA / "verify_ict.json").read_text())
    N["ict"] = ict
    N["ict_metro_xy"] = M.project(*ict["metro_centroid"])
    N["ict_rest_xy"] = M.project(*ict["rest_centroid"])
    assert ict["hayakawa_employees"] == 2 and ict["tokyo_share"] > 0.5 and ict["metro_share"] > 0.6
    assert round(ict["hayakawa_pop2020"], -2) == 1100
    return N


# ---- 描画の部品 ----

def pill_text(cv, xy, s, size, alpha=1.0, bold=True, color=None, anchor="mm", pad=(22, 12), fill=WHITE):
    """背景つきの文字（地図の上の見出し・注記）"""
    if alpha <= 0:
        return
    w = cv.text_width(s, size, bold)
    x, y = xy
    left = x - w / 2 if anchor[0] == "m" else (x - w if anchor[0] == "r" else x)
    if 0 < alpha < 1 and getattr(cv, "sat_alpha", 0) > 0:
        box = (left - pad[0], y - size / 2 - pad[1], left + w + pad[0], y + size / 2 + pad[1])
        M.fade(cv, alpha, lambda a: pill_text(cv, xy, s, size, 1.0, bold, color, anchor, pad, fill), box)
        return
    cv.rect((left - pad[0], y - size / 2 - pad[1], left + w + pad[0], y + size / 2 + pad[1]), fill, alpha, radius=12)
    cv.text((left, y), s, size, bold=bold, color=color, alpha=alpha, anchor="lm")


def _later(cv, fn):
    """見出し・注記は、地図の線や点より後に描く（build の最後で場面の描画関数を包む）"""
    q = getattr(cv, "_later", None)
    if q is None:
        fn()
    else:
        q.append(fn)


def map_title(cv, s, alpha=1.0):
    _later(cv, lambda: pill_text(cv, (W / 2, 84), s, cv.th.size_title, alpha))


def sentence(s):
    """注記は文として「。」で終える（注記の書式を動画内でそろえる）"""
    return s if s.endswith("。") else s + "。"


def note(cv, s, alpha=1.0, y=900):
    cv.note(sentence(s), alpha, y=y)


def map_note(cv, s, alpha=1.0):
    s = sentence(s)
    if cv.text_width(s, cv.th.size_note) > W - 2 * cv.th.margin:
        raise ValueError(f"注記が1行に収まりません：{s}")
    _later(cv, lambda: pill_text(cv, (W / 2, 1000), s, cv.th.size_note, alpha, bold=False, color=cv.th.sub, pad=(18, 8)))


def deferred(draw):
    def wrapped(cv, st):
        cv._later = []
        draw(cv, st)
        q, cv._later = cv._later, None
        for fn in q:
            fn()
    return wrapped


def geo_line(lons, lats):
    """経度・緯度の列を正積図法の km 座標の配列にする（経線・緯線は曲がるため、点を細かく取る）"""
    import geo
    x, y = geo.TO_XY.transform(np.asarray(lons, float), np.asarray(lats, float))
    return np.column_stack([x / 1000, y / 1000])


def meridian(lon, lat0=24, lat1=46):
    lats = np.linspace(lat0, lat1, 80)
    return geo_line(np.full(80, lon), lats)


def parallel(lat, lon0=122, lon1=154):
    lons = np.linspace(lon0, lon1, 120)
    return geo_line(lons, np.full(120, lat))


def draw_geo_line(cv, cam, arr, color, width=2.5, alpha=1.0, dash=True, progress=1.0):
    if alpha <= 0:
        return
    n = max(2, int(len(arr) * progress))
    p = cam.pxa(arr[:n])
    if dash:
        M.dashed(cv, p, color, width, alpha=alpha)
    else:
        cv.line([tuple(q) for q in p], color, width, alpha)


def appear(t, t0, dur=0.5):
    return ramp(t, t0, dur)


def ring_of(t, t0, dur=1.1):
    if t is None or t < t0:
        return 0.0
    return min(1.0, (t - t0) / dur)


def build(N, voice_credit, music_credit=""):
    C = N["C"]
    import geo

    def P(cid):
        return C[cid]["x"], C[cid]["y"]

    def mk(cv, cam, cid, a, t=None, t0=None, r=11):
        x, y = cam.px(*P(cid))
        M.marker(cv, x, y, C[cid]["category"], a, r, ring_of(t, t0) if t0 is not None else 0.0)
        return x, y

    def lab(cv, cam, cid, text, sub=None, dx=26, dy=0, a=1.0, anchor="l", size=30):
        x, y = cam.px(*P(cid))
        return M.label(cv, x, y, text, sub, dx, dy, a, size, anchor)

    g = M.geometry()
    big = sorted(g["islands"], key=lambda i: -i["area"])[:4]
    allpts = np.vstack([i["coarse"] for i in big])
    MAIN4 = M.fit((allpts[:, 0].min() - 30, allpts[:, 1].min() - 30, allpts[:, 0].max() + 30, allpts[:, 1].max() + 30))
    ext = {k: M.project(lo, la) for k, (lo, la) in {"east": (153.986667, 24.283056), "west": (122.9325, 24.451389),
                                                   "south": (136.069722, 20.425278), "north": (148.752222, 45.557222)}.items()}
    ALL = M.fit((ext["west"][0] - 80, ext["south"][1] - 80, ext["east"][0] + 80, ext["north"][1] + 60))
    px0, py0 = P("pop2020_official")
    CENTER = M.fit((px0 - 330, py0 - 230, px0 + 330, py0 + 230))
    WIDE_C = M.fit((px0 - 620, py0 - 420, px0 + 620, py0 + 420))

    scenes = []

    # 1 導入
    order = sorted([k for k, r in C.items() if r["lat"] and k != "std_meridian"], key=lambda k: hash(k) % 997)

    guesses = [("地図の真ん中？", M.project(138.2, 36.6), 0.0), ("人が多く住むあたり？", M.project(136.2, 35.0), 0.33),
               ("首都の東京？", M.project(139.75, 35.68), 0.7)]

    def d_intro(cv, st):
        cam = MAIN4
        M.draw_base(cv, cam)
        map_title(cv, "日本の中心はどこ？", appear(st.t, 0.2, 0.6))
        # 文の中の言葉に合わせて、候補（仮の問い。データの点ではない）を灰色で示す
        dur1 = st.ends[1] - st.starts[1]
        out = 1 - appear(st.t, st.at(3) - 0.3, 0.4)
        for k, (text, (gx_, gy_), frac) in enumerate(guesses):
            a = appear(st.t, st.at(1) + frac * dur1, 0.4) * out
            if a <= 0:
                continue
            x, y = cam.px(gx_, gy_)
            r = 26 * (0.6 + 0.4 * ease(min(1, (st.t - st.at(1) - frac * dur1) / 0.5)))
            cv.d.ellipse((x - r, y - r, x + r, y + r), outline=mix(cv.th.sub, M.LAND, a), width=3)
            cv.text((x, y), "?", 30, bold=True, color=cv.th.sub, alpha=a, anchor="mm")
            M.label(cv, x, y, text, None, 40 if k != 1 else -40, -50 if k != 1 else 50, a, 30, "l" if k != 1 else "r")
        t0 = st.at(3)
        for k, cid in enumerate(order):
            ts = t0 + 0.035 * k
            mk(cv, cam, cid, appear(st.t, ts, 0.3), st.t, ts)
        a = appear(st.t, t0 + 0.035 * len(order) + 0.3, 0.5)
        pill_text(cv, (W / 2, 990), f"集めた中心 {N['n_all']}個", cv.th.size_body, a)

    scenes.append(Scene("導入", [
        Line("日本の中心はどこでしょうか。"),
        Line("地図の真ん中、人が多く住むあたり、それとも首都の東京。"),
        Line("実は、何を基準にするかで、答えはまったく違う場所になります。"),
        Line("今回は、公的な統計や地図のデータを使って、日本の「中心」を97個集めました。"),
    ], d_intro, lead=0.8, tail=1.8))

    # 2 種類
    def d_types(cv, st):
        th = cv.th
        cv.title(f"集めた{N['n_all']}個の中心の種類", appear(st.t, 0, 0.5))
        x0, x1 = 330, 1590
        y0 = 210
        rh = 80
        vmax = max(n for *_, n in N["types"])
        starts = [st.at(1), st.at(1) + 0.5, st.at(2), st.at(2) + 0.6, st.at(2) + 1.2, st.at(3), st.at(3) + 0.8]
        for k, ((name, desc, n), t0) in enumerate(zip(N["types"], starts)):
            a = appear(st.t, t0, 0.5)
            y = y0 + k * rh
            color, shape = M.STYLE[name]
            if shape == "square" and name == "最大集積地":
                cv.rect((x0 - 14, y + 14, x0 + 14, y + 42), mix(color, th.bg, 0.35 * a), radius=2)
                cv.line([(x0 - 14, y + 14), (x0 + 14, y + 14), (x0 + 14, y + 42), (x0 - 14, y + 42), (x0 - 14, y + 14)], color, 2.5, a)
            else:
                M.marker(cv, x0, y + 28, name, a, 13, bg=th.bg)
            cv.text((x0 + 36, y + 28), desc, th.size_note + 6, bold=True, alpha=a, anchor="lm")
            bx = x0 + 520
            w = (x1 - bx - 120) * n / vmax * ease((st.t - t0) / 0.7 if st.t > t0 else 0)
            cv.rect((bx, y + 10, bx + w, y + 46), color, a, radius=4)
            cv.text((bx + w + 16, y + 28), f"{n}個", th.size_note + 6, bold=True, alpha=a, anchor="lm")
        b = appear(st.t, st.at(4), 0.6)
        # 点・線・地域
        items = [("point", f"点 {N['n_points']}個"), ("line", "線 1本（経線）"), ("region", f"地域 {N['n_regions']}個")]
        for k, (kind, text) in enumerate(items):
            cx = W / 2 + (k - 1) * 420
            y = 860
            if kind == "point":
                M.marker(cv, cx - 120, y, "分布の重心", b, 13, bg=th.bg)
            elif kind == "line":
                M.dashed(cv, [(cx - 120, y - 30), (cx - 120, y + 30)], th.text, 3, alpha=b)
            else:
                col = M.STYLE["最大集積地"][0]
                cv.rect((cx - 145, y - 22, cx - 95, y + 22), mix(col, th.bg, 0.35 * b), radius=4)
            cv.text((cx - 80, y), text, th.size_note + 6, bold=True, alpha=b, anchor="lm")
        note(cv, "同じ考え方の言い換え（範囲や集計単位の違い）を含む。考え方としては30前後", appear(st.t, st.at(4) + 0.8, 0.6), y=940)

    scenes.append(Scene("集めた中心の種類", [
        Line("集めた中心は、大きく7つの種類に分けられます。"),
        Line("国土の形から求める中心、人口などの量の分布から求める重心、"),
        Line("量が最も多い地域、交通網の中心、移動の距離が最も短くなる地点、"),
        Line("法律や歴史で決まった中心、そして自治体が名乗る中心です。"),
        Line("地図の上では点で示すものが多いですが、線や地域で示すものもあります。"),
    ], d_types, tail=1.6))

    # 3 重心とは（つり合いの図解）
    weights = [(-560, 1.0), (-400, 1.6), (-250, 1.0), (-120, 1.3), (380, 6.0), (520, 1.2)]
    tot = sum(w for _, w in weights)
    bal = sum(x * w for x, w in weights) / tot

    def d_balance(cv, st):
        th = cv.th
        cv.title("重心とは", appear(st.t, 0, 0.5))
        cy = 560
        a = appear(st.t, st.at(0) + 0.3, 0.6)
        cv.line([(W / 2 - 700, cy), (W / 2 + 700, cy)], th.text, 6, a)
        for k, (x, w) in enumerate(weights):
            r = 16 * math.sqrt(w)
            b = appear(st.t, st.at(1) + 0.15 * k, 0.4)
            col = hexrgb("D9822B")
            cv.d.ellipse((W / 2 + x - r, cy - 2 * r - 4, W / 2 + x + r, cy - 4), fill=mix(col, th.bg, b))
        # 支点が重心へ動く
        p = ease((st.t - st.at(1) - 1.2) / 1.6) if st.t > st.at(1) + 1.2 else 0.0
        fx = W / 2 + (-700 + 60) * (1 - p) + bal * p
        f = appear(st.t, st.at(1) + 0.8, 0.5)
        cv.d.polygon([(fx, cy + 4), (fx - 34, cy + 64), (fx + 34, cy + 64)], fill=mix(hexrgb("2E6BD1"), th.bg, f))
        lab_a = appear(st.t, st.at(1) + 2.9, 0.5)
        cv.text((fx, cy + 90), "重心（つり合う点）", th.size_body, bold=True, color=hexrgb("2E6BD1"), alpha=lab_a, anchor="ma")
        c = appear(st.t, st.at(2), 0.6)
        bx = W / 2 + 380
        cv.text((bx, cy - 150), "最も多い場所", th.size_body, bold=True, color=th.sub, alpha=c, anchor="md")
        cv.line([(bx, cy - 140), (bx, cy - 90)], th.sub, 2, c)
        note(cv, "つり合う点の上に、量があるとは限らない", appear(st.t, st.at(2) + 0.8, 0.6), y=820)

    scenes.append(Scene("重心とは", [
        Line("まず、この動画で何度も出てくる、重心という考え方です。"),
        Line("重心は、一人ひとり、一つひとつに同じ重さがあると考えたとき、全体がちょうどつり合う点です。"),
        Line("量が最も多い場所とは違い、重心の位置そのものに、量があるとは限りません。"),
        Line("この違いが、あとで意外な場所に中心が現れる理由になります。"),
    ], d_balance, tail=1.4))

    # 4 国土の重心
    lo, la, _ = geo.land_grid(40000)
    gx, gy = geo.TO_XY.transform(lo, la)
    grid = np.column_stack([gx / 1000, gy / 1000])
    NOTO = M.fit((C["area_excl_nt"]["x"] - 180, C["area_excl_nt"]["y"] - 120,
                  C["area_excl_nt"]["x"] + 180, C["area_excl_nt"]["y"] + 120))

    def d_area(cv, st):
        th = cv.th
        keys = [(0, MAIN4), (st.at(2) + 1.2, MAIN4), (st.at(2) + 3.0, NOTO)]
        cam = M.cam_at(keys, st.t)
        M.draw_base(cv, cam, satellite=1.0)
        map_title(cv, "国土の重心", appear(st.t, 0, 0.5))
        # マス目（40km。説明用の粗い格子。計算は 1km）
        gp = 1 - appear(st.t, st.at(2) + 0.6, 0.8)
        if st.t > st.at(1) and gp > 0:
            col = mix(hexrgb("2E6BD1"), M.LAND, 0.28)
            n = len(grid)
            grow = ease((st.t - st.at(1)) / 2.0)
            for i, (x, y) in enumerate(grid):
                k = min(1.0, max(0.0, (grow - 0.7 * i / n) / 0.3))
                half = 17 / cam.kmpp * min(k, gp)
                if half <= 0.3:
                    continue
                sx, sy = cam.px(x, y)
                cv.d.rectangle((sx - half, sy - half, sx + half, sy + half), fill=col)
        t0 = st.at(2) + 0.3
        mk(cv, cam, "area_excl_nt", appear(st.t, t0, 0.4), st.t, t0)
        lab(cv, cam, "area_excl_nt", "国土の面積重心", "能登半島の沖・海の上", dx=-30, dy=-60, a=appear(st.t, st.at(2) + 3.2, 0.5), anchor="r")
        t1 = st.at(4) + 0.3
        mk(cv, cam, "area_all", appear(st.t, t1, 0.4), st.t, t1)
        lab(cv, cam, "area_all", "北方領土を含む", dx=30, dy=-40, a=appear(st.t, t1 + 0.3, 0.5), size=26)
        map_note(cv, "地球地図日本（国土地理院、1:100万）の陸地を1km 四方のマス目で数えた独自計算", appear(st.t, st.at(1), 0.6))

    scenes.append(Scene("国土の重心", [
        Line("最初は、国土の形から考えます。"),
        Line("陸地を同じ大きさのマス目に区切り、すべてのマス目がつり合う点を求めると、"),
        Line("国土の重心は、能登半島の沖、日本海の上になりました。"),
        Line("日本列島が弓のように曲がっているため、形の重心が陸の外に出るのです。"),
        Line("北方領土を含めるかどうかで15キロほど動きますが、どちらも海の上です。"),
    ], d_area, tail=1.6))

    # 5 東西南北の真ん中
    names = {"east": "南鳥島", "west": "与那国島", "south": "沖ノ鳥島", "north": "択捉島"}

    def d_bbox(cv, st):
        th = cv.th
        cam = M.cam_at([(0, MAIN4), (st.at(1) - 0.2, MAIN4), (st.at(1) + 1.6, ALL)], st.t)
        M.draw_base(cv, cam)
        map_title(cv, "東西南北の端の真ん中", appear(st.t, 0, 0.5))
        for k, key in enumerate(["east", "west", "north", "south"]):
            a = appear(st.t, st.at(1) + 1.6 + 0.4 * k, 0.4)
            x, y = cam.px(*ext[key])
            cv.d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=mix(th.text, M.SEA, a))
            dx = {"east": -20, "west": 20, "north": -20, "south": 20}[key]
            M.label(cv, x, y, names[key], None, dx, 0, a, 28, "r" if dx < 0 else "l", leader=False)
        b = appear(st.t, st.at(2), 0.6)
        mx = (ext["east"][0] + ext["west"][0]) / 2
        my = (ext["north"][1] + ext["south"][1]) / 2
        if b > 0:
            # 東西の中間・南北の中間（経度・緯度の中間。図では投影後の位置に線を引く）
            mid_lon = (153.986667 + 122.9325) / 2
            mid_lat = (45.557222 + 20.425278) / 2
            draw_geo_line(cv, cam, meridian(mid_lon, 19, 47), hexrgb("2E6BD1"), 2.5, b)
            draw_geo_line(cv, cam, parallel(mid_lat, 121, 156), hexrgb("2E6BD1"), 2.5, b)
        t0 = st.at(2) + 1.0
        mk(cv, cam, "bbox_mid", appear(st.t, t0, 0.4), st.t, t0)
        lab(cv, cam, "bbox_mid", "東西南北の端の中間", "伊豆諸島の西・太平洋の上", dx=30, dy=60, a=appear(st.t, t0 + 0.6, 0.5))
        map_note(cv, "端の座標：国土地理院「日本の東西南北端点の経度緯度」。経度と緯度それぞれの中間", appear(st.t, st.at(1), 0.6))

    scenes.append(Scene("東西南北の端の真ん中", [
        Line("では、東西南北の端の、ちょうど真ん中はどうでしょう。"),
        Line("東の南鳥島と西の与那国島、北の択捉島と南の沖ノ鳥島。"),
        Line("それぞれの中間をとると、伊豆諸島の西、太平洋の上になります。"),
    ], d_bbox, tail=1.8))

    # 6 海から最も遠い地点
    fx, fy = P("farthest_from_sea")
    coast = M.project(*N["sea_coast"])
    rad = math.hypot(coast[0] - fx, coast[1] - fy)
    SAKU = M.fit((fx - 210, fy - 170, fx + 210, fy + 170))

    def d_far(cv, st):
        th = cv.th
        cam = M.cam_at([(0, ALL), (0.6, ALL), (st.at(1), SAKU)], st.t)
        M.draw_base(cv, cam, satellite=1.0)
        map_title(cv, "海から最も遠い地点", appear(st.t, 0, 0.5))
        t0 = st.at(1) + 0.6
        a = appear(st.t, t0, 0.4)
        sx, sy = cam.px(fx, fy)
        p = ease((st.t - st.at(2)) / 1.4) if st.t > st.at(2) else 0.0
        if p > 0:
            r = rad / cam.kmpp * p
            # 衛星画像の上で見えるよう白い線にする
            cv.d.ellipse((sx - r, sy - r, sx + r, sy + r), outline=WHITE, width=3.5)
            cx, cy = cam.px(*coast)
            q = appear(st.t, st.at(2) + 1.4, 0.4)
            cv.line([(sx, sy), (sx + (cx - sx) * p, sy + (cy - sy) * p)], WHITE, 3.5, 1.0)
            cv.d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=WHITE)
            M.label(cv, (sx + cx) / 2, (sy + cy) / 2, f"約{round(N['sea_km'])}km", None, 20, 0, q, 34, leader=False)
        mk(cv, cam, "farthest_from_sea", a, st.t, t0)
        lab(cv, cam, "farthest_from_sea", "長野県佐久市", "海岸線から最も遠い", dx=30, dy=-70, a=appear(st.t, t0 + 0.5, 0.5))
        map_note(cv, "独自計算（1:100万の陸地）と佐久市の公表（1996年に国土地理院が特定、約115km）が一致", appear(st.t, st.at(3), 0.6))

    scenes.append(Scene("海から最も遠い地点", [
        Line("逆に、陸の一番奥はどこでしょうか。"),
        Line("海岸線から最も遠い地点を計算すると、長野県佐久市の山の中になりました。"),
        Line("最も近い海までは、およそ115キロあります。"),
        Line("佐久市も、国土地理院が特定した地点として、海岸線からおよそ115キロの地点を紹介しています。"),
    ], d_far, tail=1.6))

    # 7 人口重心
    muni = list(csv.DictReader((DATA / "municipalities.csv").open(encoding="utf-8")))
    mpts = np.array([M.project(float(r["lon"]), float(r["lat"])) for r in muni])
    mpop = np.array([float(r["pop"]) for r in muni])

    def d_pop(cv, st):
        th = cv.th
        cam = M.cam_at([(0, MAIN4), (st.at(2) + 0.2, MAIN4), (st.at(2) + 2.2, WIDE_C)], st.t)
        M.draw_base(cv, cam)
        map_title(cv, "人口重心", appear(st.t, 0, 0.5))
        a = appear(st.t, st.at(1), 0.8) * (1 - 0.5 * appear(st.t, st.at(2) + 2.2, 0.6))
        if a > 0:
            col = mix(hexrgb("5B6470"), M.LAND, 0.55 * a)
            sp = cam.pxa(mpts)
            rr = np.sqrt(mpop) / 140 * (MAIN4.kmpp / cam.kmpp) ** 0.5
            for (x, y), r in zip(sp, rr):
                if -20 < x < W + 20 and -20 < y < H + 20:
                    r = max(r, 1.0)
                    cv.d.ellipse((x - r, y - r, x + r, y + r), fill=col)
        t0 = st.at(2) + 0.2
        mk(cv, cam, "pop2020_official", appear(st.t, t0, 0.4), st.t, t0, r=13)
        lab(cv, cam, "pop2020_official", "人口重心（2020年）", "岐阜県関市", dx=34, dy=-60, a=appear(st.t, t0 + 2.2, 0.5))
        map_note(cv, "総務省統計局の公表値。灰色の円は市区町村の人口（2020年国勢調査）", appear(st.t, st.at(1), 0.6))

    scenes.append(Scene("人口重心", [
        Line("次は、人が住む場所から考えます。"),
        Line("国勢調査の人口を使い、日本に住む人全体がつり合う点を求めたものを、人口重心といいます。"),
        Line("2020年の人口重心は、岐阜県関市の山あいにあります。"),
        Line("これは総務省統計局が公表している値です。"),
    ], d_pop, tail=1.4))

    # 8 人口重心の移動
    hx = np.array([h[2] for h in N["hist"]])
    hy = np.array([h[3] for h in N["hist"]])
    TRACK = M.fit((hx.min() - 10, hy.min() - 9, hx.max() + 10, hy.max() + 7))

    def d_track(cv, st):
        th = cv.th
        cam = M.cam_at([(0, WIDE_C), (0.4, WIDE_C), (st.at(0) + 2.0, TRACK), (st.at(3), TRACK), (st.at(3) + 2.5, CENTER)], st.t)
        M.draw_base(cv, cam, satellite=1.0)
        M.scale_bar(cv, cam, appear(st.t, st.at(0) + 2.0, 0.5))
        x1_, y1_ = cam.px(*P("pop2020_official"))
        pill_text(cv, (x1_ - 150, y1_ + 140), "岐阜県", 30,
                  appear(st.t, st.at(0) + 2.0, 0.5) * (1 - appear(st.t, st.at(3), 0.4)), bold=False, color=cv.th.sub, pad=(14, 6))
        map_title(cv, "人口重心の移動", appear(st.t, 0, 0.5))
        p = ease((st.t - st.at(1)) / 3.0) if st.t > st.at(1) else 0.0
        pts = [(y, m, *cam.px(x, yy)) for y, m, x, yy in N["hist"]]
        col = hexrgb("D9822B")
        n_show = p * (len(pts) - 1)
        for i in range(len(pts) - 1):
            if i >= n_show:
                break
            (y0, m0, x0, yy0), (y1, m1, x1, yy1) = pts[i], pts[i + 1]
            if m0 != m1:  # 2005年に算出方法が変わった区間は線でつながない
                continue
            f = min(1.0, n_show - i)
            cv.line([(x0, yy0), (x0 + (x1 - x0) * f, yy0 + (yy1 - yy0) * f)], col, 4, 1.0)
        for i, (y, m, x, yy) in enumerate(pts):
            if i <= n_show + 1e-6:
                cv.d.ellipse((x - 7, yy - 7, x + 7, yy + 7), fill=col if m == "2005年からの方式" else mix(col, M.LAND, 0.6),
                             outline=WHITE, width=2)
        ya = appear(st.t, st.at(1) + 3.0, 0.5)
        x0, yy0 = pts[0][2:]
        x1, yy1 = pts[-1][2:]
        zo = 1 - appear(st.t, st.at(3), 0.4)
        M.label(cv, x0, yy0, "1965年", None, -24, -40, ya * zo, 30, "r")
        M.label(cv, x1, yy1, "2020年", None, 24, -50, ya * zo, 30, "l")
        # 2025年（推計）
        e = appear(st.t, st.at(2), 0.5)
        if e > 0:
            ex, ey = cam.px(*P("pop2025_est"))
            M.dashed(cv, [(x1, yy1), (ex, ey)], col, 3, alpha=e)
            cv.d.ellipse((ex - 8, ey - 8, ex + 8, ey + 8), fill=mix(WHITE, M.LAND, e), outline=mix(col, M.LAND, e), width=3)
            M.label(cv, ex, ey, "2025年（推計）", "七宗町", 24, 50, e * zo, 30, "l")
            M.label(cv, ex, ey, "人口重心の移動（1965〜2025年）", None, 40, 60, appear(st.t, st.at(3) + 2.0, 0.5), 28, "l")
        map_note(cv, "1965〜2020年は統計局の公表値（2005年に算出方法を変更）。2025年は国勢調査の人口からの独自の推計", appear(st.t, st.at(1), 0.6))

    scenes.append(Scene("人口重心の移動", [
        Line("人口重心は、国勢調査のたびに少しずつ動いてきました。"),
        Line("1965年からの55年間で、東南東へおよそ29キロ。首都圏への人の流入が続いたことなどによるものです。"),
        Line("2025年の国勢調査の人口で推計すると、さらに2キロほど南東の、七宗町に入ります。"),
        Line("ただし、これは今回の推計で、統計局が発表した値ではありません。"),
    ], d_track, tail=1.6))

    # 9 人の活動の重心
    act = [("gdp", "県内総生産"), ("employees", "働く場所"), ("retail", "小売販売額"), ("power_demand", "電力需要"),
           ("universities", "大学"), ("doctors", "医師"), ("guest_nights", "宿泊者"), ("manufacturing", "製造品出荷額"),
           ("museums", "博物館"), ("power_gen", "発電量")]
    dist_ids = [r for r, v in C.items() if v["category"] == "分布の重心"]

    def d_act(cv, st):
        th = cv.th
        cam = CENTER
        M.draw_base(cv, cam, highlight_pref="21", highlight_alpha=appear(st.t, st.at(2), 0.8))
        map_title(cv, "人の活動の重心", appear(st.t, 0, 0.5))
        mk(cv, cam, "pop2020_official", 1.0, r=13)
        for k, (cid, name) in enumerate(act):
            t0 = st.at(0) + 0.5 + 0.55 * k
            mk(cv, cam, cid, appear(st.t, t0, 0.3), st.t, t0)
        # 残りの分布の重心
        rest = [c for c in dist_ids if c not in dict(act) and c != "pop2020_official"]
        for k, cid in enumerate(rest):
            t0 = st.at(1) + 0.1 * k
            mk(cv, cam, cid, appear(st.t, t0, 0.3), st.t, t0)
        # 名前は一覧で示す（点が近いため、点ごとの札は付けない）
        b = appear(st.t, st.at(2), 0.6)
        pill_text(cv, (W / 2, 990), f"分布の重心 {N['n_dist']}個のうち {N['n_gifu']}個が岐阜県内", th.size_body, b)
        c = appear(st.t, st.at(0) + 0.5, 0.5) * (1 - appear(st.t, st.at(2), 0.5))
        if c > 0:
            names = "・".join(n for _, n in act)
            pill_text(cv, (W / 2, 990), names, th.size_note + 2, c, bold=False)

    scenes.append(Scene("人の活動の重心", [
        Line("人口だけでなく、経済、買い物、電気、大学、医療など、さまざまな量の分布から重心を計算しました。"),
        Line("すると、その多くが、人口重心の近くに集まります。"),
        Line("分布の重心48個のうち、28個が岐阜県の中です。"),
    ], d_act, tail=1.8))

    # 10 検証
    def d_verify(cv, st):
        th = cv.th
        cv.title("岐阜に集まるのはなぜか", appear(st.t, 0, 0.5))
        # 左：人口との相関（都道府県のシェア）のドット図
        x0, x1, y0 = 180, 900, 260
        a = appear(st.t, st.at(1), 0.6)
        cv.text(((x0 + x1) / 2, y0 - 40), "人口との相関（都道府県別の全国シェア）", th.size_note + 2, bold=True, alpha=a, anchor="ma")
        base = 640
        cv.line([(x0, base), (x1, base)], th.text, 2, a)
        for v in (0, 0.5, 0.9, 1.0):
            X = x0 + (x1 - x0) * v
            cv.line([(X, base), (X, base + 10)], th.text, 2, a)
            cv.text((X, base + 16), f"{v:.1f}", th.size_note - 2, color=th.sub, alpha=a, anchor="ma")
        Xh = x0 + (x1 - x0) * 0.9
        cv.rect((Xh, y0, x1 + 12, base), hexrgb("FBE3C8"), a * appear(st.t, st.at(1) + 1.0, 0.5))
        cv.text(((Xh + x1) / 2, y0 + 10), f"{N['n_popshape']}個", th.size_body, bold=True, alpha=a * appear(st.t, st.at(1) + 1.0, 0.5), anchor="ma")
        # 値の近い点は縦に積む
        bins = {}
        for name, r, gifu in N["r_pop"]:
            k = round(max(-0.05, r) * 40)
            bins.setdefault(k, []).append(gifu)
        for k, gs in bins.items():
            X = x0 + (x1 - x0) * k / 40
            for j, gifu in enumerate(sorted(gs, reverse=True)):
                Y = base - 22 - j * 24
                col = hexrgb("D9822B") if gifu else th.muted
                cv.d.ellipse((X - 10, Y - 10, X + 10, Y + 10), fill=mix(col, th.bg, a))
        leg = appear(st.t, st.at(1), 0.6)
        cv.d.ellipse((x0, 760 - 10, x0 + 20, 760 + 10), fill=mix(hexrgb("D9822B"), th.bg, leg))
        cv.text((x0 + 32, 760), "重心が岐阜県内", th.size_note, color=th.sub, alpha=leg, anchor="lm")
        cv.d.ellipse((x0 + 300, 760 - 10, x0 + 320, 760 + 10), fill=mix(th.muted, th.bg, leg))
        cv.text((x0 + 332, 760), "岐阜県外", th.size_note, color=th.sub, alpha=leg, anchor="lm")
        # 右：数え方を変えても
        rows = [(f"{N['n_dist']}個そのまま", N["n_gifu"], N["n_dist"], st.at(2)),
                (f"似た指標をまとめた{N['n_groups']}群", N["n_groups_gifu"], N["n_groups"], st.at(2) + 1.2),
                (f"分野ごとの代表{N['n_fields']}個", N["n_fields_gifu"], N["n_fields"], st.at(3))]
        rx0, rx1 = 1060, 1740
        for k, (name, g, n, t0) in enumerate(rows):
            b = appear(st.t, t0, 0.5)
            y = 300 + k * 150
            cv.text((rx0, y), name, th.size_note + 4, bold=True, alpha=b)
            bw = (rx1 - rx0 - 140)
            cv.rect((rx0, y + 46, rx0 + bw, y + 86), th.muted, b, radius=4)
            p = ease((st.t - t0 - 0.3) / 0.8) if st.t > t0 + 0.3 else 0
            cv.rect((rx0, y + 46, rx0 + bw * g / n * p, y + 86), hexrgb("D9822B"), b, radius=4)
            cv.text((rx0 + bw + 16, y + 66), f"{g}/{n}", th.size_body - 4, bold=True, alpha=b, anchor="lm")
        c = appear(st.t, st.at(4), 0.6)
        note(cv, f"人口重心から50km 以内の陸地の約{round(N['ring50'] * 10)}割が岐阜県。人口と似た分布の量は、重心も人口重心の近くに来る", c, y=860)

    scenes.append(Scene("岐阜に集まるのはなぜか", [
        Line("ただし、これは岐阜が日本の活動の中心だ、という意味ではありません。"),
        Line("人口や世帯、買い物の額のように、人口とほとんど同じ形で分布する量が15個あり、それらは重心も同じ場所に来ます。"),
        Line("そこで、似た量を一つにまとめたり、分野ごとに代表を一つ選んだりして、数え直しました。"),
        Line("それでも、15の分野のうち10の分野で、重心は岐阜県に入ります。"),
        Line("人口重心の周り50キロの陸地は、およそ8割が岐阜県です。"),
        Line("東京と、大阪や名古屋のあいだに重みがある量は、どれも重心が中部地方の内陸に来る、ということです。"),
    ], d_verify, tail=2.0))

    # 11 外れる重心
    out_ids = [("forest", "森林", 30, -50, "l"), ("fish_catch", "漁獲量", -30, -40, "r"), ("farmland", "耕地", 30, 30, "l"),
               ("agri_output", "農業産出額", -30, 50, "r"), ("emp_ict", "情報通信業", 30, 40, "l"),
               ("emp_finance", "金融・保険業", 30, -20, "l"), ("deposits", "銀行預金", -30, 60, "r")]
    OUTV = M.fit((px0 - 420, py0 - 260, px0 + 420, py0 + 380))

    def d_out(cv, st):
        th = cv.th
        cam = M.cam_at([(0, CENTER), (st.at(0) + 1.5, OUTV)], st.t)
        M.draw_base(cv, cam)
        map_title(cv, "外れる重心", appear(st.t, 0, 0.5))
        mk(cv, cam, "pop2020_official", 1.0, r=13)
        for k, (cid, name, dx, dy, an) in enumerate(out_ids):
            t0 = (st.at(1) if k < 4 else st.at(2)) + 0.6 * (k if k < 4 else k - 4)
            a = appear(st.t, t0, 0.4)
            x0_, y0_ = cam.px(*P("pop2020_official"))
            x1_, y1_ = cam.px(*P(cid))
            if a > 0:
                f = ease((st.t - t0) / 0.8)
                M.dashed(cv, [(x0_, y0_), (x0_ + (x1_ - x0_) * f, y0_ + (y1_ - y0_) * f)], th.sub, 2, alpha=a * 0.8)
            mk(cv, cam, cid, a, st.t, t0)
            lab(cv, cam, cid, name, None, dx, dy, appear(st.t, t0 + 0.4, 0.4), an, 28)
        map_note(cv, "点線は人口重心（2020年）からの向き", appear(st.t, st.at(1), 0.6))

    scenes.append(Scene("外れる重心", [
        Line("一方で、はっきり外れる重心もあります。"),
        Line("森林や耕地、漁業のように、北海道や東北に多いものは北へずれ、森林や漁獲量の重心は、日本海の上に出ます。"),
        Line("反対に、情報通信業や金融のように、東京に集中するものは、東へずれます。"),
    ], d_out, tail=1.6))

    # 12 早川町
    ict = N["ict"]
    hx_, hy_ = P("emp_ict")
    HAYA = M.fit((hx_ - 60, hy_ - 40, hx_ + 60, hy_ + 40))
    SEESAW = M.fit((N["ict_rest_xy"][0] - 140, min(N["ict_rest_xy"][1], N["ict_metro_xy"][1]) - 170,
                    N["ict_metro_xy"][0] + 140, max(N["ict_rest_xy"][1], N["ict_metro_xy"][1]) + 170))

    def d_haya(cv, st):
        th = cv.th
        cam = M.cam_at([(0, OUTV), (0.3, OUTV), (st.at(0) + 1.8, HAYA), (st.at(3) - 0.2, HAYA), (st.at(3) + 1.6, SEESAW)], st.t)
        M.draw_base(cv, cam, satellite=1 - appear(st.t, st.at(3), 0.8))
        M.pref_labels(cv, cam, 1 - appear(st.t, st.at(3), 0.4), avoid=[(*cam.px(hx_, hy_), 420)])
        M.scale_bar(cv, cam, appear(st.t, st.at(0) + 1.8, 0.5) * (1 - appear(st.t, st.at(3), 0.4)))
        map_title(cv, "情報通信業の重心", appear(st.t, 0, 0.5))
        x, y = cam.px(hx_, hy_)
        # つり合いの図解：首都圏とそれ以外の重心を、重みの大きさの円で示す
        s = appear(st.t, st.at(3) + 1.0, 0.6)
        if s > 0:
            mxy = cam.px(*N["ict_metro_xy"])
            rxy = cam.px(*N["ict_rest_xy"])
            cv.line([rxy, mxy], th.text, 4, s)
            # 首都圏の重みが先に、それ以外が後に現れる（文の順）
            for (cx_, cy_), share, name, an, t0 in [(mxy, ict["metro_share"], "首都圏", "l", st.at(3) + 1.0),
                                                    (rxy, 1 - ict["metro_share"], "それ以外", "r", st.at(4))]:
                g = appear(st.t, t0, 0.6)
                if g <= 0:
                    continue
                r = 120 * math.sqrt(share) * (0.3 + 0.7 * g)
                cv.d.ellipse((cx_ - r, cy_ - r, cx_ + r, cy_ + r), fill=mix(hexrgb("D9822B"), M.LAND, 0.45 * g),
                             outline=mix(hexrgb("D9822B"), M.LAND, g), width=3)
                M.label(cv, cx_, cy_, f"{name} {round(share * 100)}%", None, 0, -120 * math.sqrt(share) - 34, g, 32,
                        "l" if an == "l" else "r", leader=False)
            # 支点：2つの重みの中間から、つり合いの点（重心）へ動く
            q = ease((st.t - st.at(4) - 0.8) / 2.0) if st.t > st.at(4) + 0.8 else 0.0
            fx_ = (rxy[0] + mxy[0]) / 2 * (1 - q) + x * q
            fy_ = (rxy[1] + mxy[1]) / 2 * (1 - q) + y * q
            cv.d.polygon([(fx_, fy_ + 14), (fx_ - 22, fy_ + 52), (fx_ + 22, fy_ + 52)],
                         fill=mix(hexrgb("2E6BD1"), M.LAND, appear(st.t, st.at(4) + 0.4, 0.4)))
        mk(cv, cam, "emp_ict", 1.0 if st.t < st.at(3) + 1.0 else appear(st.t, st.at(4) + 2.6, 0.4), r=13)
        a = appear(st.t, st.at(0) + 1.8, 0.5) * (1 - appear(st.t, st.at(3), 0.4))
        M.label(cv, x, y, "山梨県早川町", "人口 1,098人（2020年）", 30, -60, a, 32)
        b = appear(st.t, st.at(1) + 0.5, 0.5) * (1 - appear(st.t, st.at(3), 0.4))
        M.label(cv, x, y, "情報通信業の従業者", f"{int(ict['hayakawa_employees'])}人（2021年）", 30, 70, b, 32)
        c = appear(st.t, st.at(5), 0.5)
        if c > 0:
            M.label(cv, x, y, "分布から計算した重心", None, 0, 120, c, 30, "l", leader=False)
        map_note(cv, "経済センサス（2021年）の情報通信業の従業者。代表点（市区町村の人口重心）の選び方で位置は数十km 動く",
                 appear(st.t, st.at(3), 0.6))

    scenes.append(Scene("情報通信業の重心", [
        Line("東へずれた情報通信業の重心は、山梨県早川町の山の中にあります。"),
        Line("人口およそ1100人の町で、ここで情報通信業の事業所に勤める人は、2人しかいません。"),
        Line("それなのに、なぜここなのでしょうか。"),
        Line("情報通信業で働く人の半分以上は東京都にいて、首都圏全体では6割を超えます。"),
        Line("首都圏の重みと、それ以外の地域の重みがつり合う点を求めると、ちょうど南アルプスの山の中に来るのです。"),
        Line("早川町に情報通信業が集まっているのではなく、分布から計算した重心が、たまたまそこに位置するということです。"),
    ], d_haya, tail=1.8))

    # 13 同じ人口から3つの中心
    med = C["pop_median_lonlat"]
    THREE = M.fit((px0 - 260, py0 - 240, px0 + 300, py0 + 150))

    def d_three(cv, st):
        th = cv.th
        cam = M.cam_at([(0, SEESAW), (st.at(0) + 1.4, THREE)], st.t)
        M.draw_base(cv, cam)
        map_title(cv, "同じ人口から3つの中心", appear(st.t, 0, 0.5))
        mk(cv, cam, "pop2020_official", 1.0, r=13)
        lab(cv, cam, "pop2020_official", "重心（平均）", "岐阜県関市", -30, -70, appear(st.t, st.at(0) + 1.4, 0.5), "r")
        b = appear(st.t, st.at(1), 0.6)
        draw_geo_line(cv, cam, meridian(float(med["lon"]), 30, 45), hexrgb("2E6BD1"), 2.5, b, progress=min(1, b * 1.2))
        draw_geo_line(cv, cam, parallel(float(med["lat"]), 128, 146), hexrgb("2E6BD1"), 2.5, b, progress=min(1, b * 1.2))
        t0 = st.at(1) + 1.6
        mk(cv, cam, "pop_median_lonlat", appear(st.t, t0, 0.4), st.t, t0)
        lab(cv, cam, "pop_median_lonlat", "中央値の点", "静岡市葵区（南アルプス）", 30, 60, appear(st.t, t0 + 0.4, 0.5))
        t1 = st.at(2) + 0.6
        mk(cv, cam, "pop_median_point", appear(st.t, t1, 0.4), st.t, t1)
        lab(cv, cam, "pop_median_point", "直線距離の合計が最小", "長野県飯田市", 30, -70, appear(st.t, t1 + 0.4, 0.5))
        map_note(cv, "青い線：人口を東西・南北それぞれ半分に分ける線（2020年、市区町村の人口重心で計算）", appear(st.t, st.at(1), 0.6))

    scenes.append(Scene("同じ人口から3つの中心", [
        Line("同じ人口のデータでも、中心の決め方を変えると、場所が変わります。"),
        Line("人口を東西で半分ずつ、南北で半分ずつに分ける線を引くと、交わる点は静岡市の南アルプスです。平均ではなく、中央値の考え方です。"),
        Line("住む人みんなからの、まっすぐな距離の合計が最も小さくなる点は、長野県飯田市になります。"),
        Line("重心は、遠くに住む人の影響を、距離に比例して大きく受けるため、こうした違いが生まれます。"),
    ], d_three, tail=1.6))

    # 14 鉄道
    NAGOYA = M.fit((C["rail_closeness"]["x"] - 260, C["rail_closeness"]["y"] - 180, C["rail_closeness"]["x"] + 260, C["rail_closeness"]["y"] + 180))

    def d_rail(cv, st):
        th = cv.th
        cam = M.cam_at([(0, MAIN4), (st.at(1) + 1.0, MAIN4), (st.at(1) + 3.0, NAGOYA), (st.at(2), NAGOYA),
                        (st.at(2) + 2.0, WIDE_C)], st.t)
        M.draw_base(cv, cam, rail=appear(st.t, st.at(0) + 0.5, 1.2))
        pa = appear(st.t, st.at(2) + 0.3, 0.8) * (1 - 0.6 * appear(st.t, st.at(3), 0.6))
        if pa > 0:
            col = mix(hexrgb("5B6470"), M.LAND, 0.45 * pa)
            sp = cam.pxa(mpts)
            rr = np.sqrt(mpop) / 140 * (MAIN4.kmpp / cam.kmpp) ** 0.5
            for (x, y), r in zip(sp, rr):
                if -20 < x < W + 20 and -20 < y < H + 20:
                    r = max(r, 1.0)
                    cv.d.ellipse((x - r, y - r, x + r, y + r), fill=col)
        map_title(cv, "鉄道網の中心", appear(st.t, 0, 0.5))
        t0 = st.at(1) + 1.0
        mk(cv, cam, "rail_closeness", appear(st.t, t0, 0.4), st.t, t0, r=13)
        lab(cv, cam, "rail_closeness", "名古屋駅", "線路の距離で全駅に最も近い", 30, -70,
            appear(st.t, st.at(1) + 3.0, 0.5) * (1 - appear(st.t, st.at(2), 0.3)))
        lab(cv, cam, "rail_closeness", "名古屋駅", "人口で重み付けしても同じ", 30, -70, appear(st.t, st.at(2) + 2.0, 0.5))
        map_note(cv, "国土数値情報「鉄道」（2024年）。本州・北海道・九州・四国がつながった路線網。所要時間ではなく距離", appear(st.t, st.at(1), 0.6))

    scenes.append(Scene("鉄道網の中心", [
        Line("交通網で考えるとどうでしょう。"),
        Line("全国の鉄道の線路をつなぎ、線路に沿った距離で、すべての駅に最も近い駅を探すと、名古屋駅になりました。"),
        Line("住む人の多さで重みをつけても、同じく名古屋駅です。"),
        Line("ただし、これは線路の長さで測った中心で、所要時間や、利用者の数で測った中心ではありません。"),
    ], d_rail, tail=1.6))

    # 15 制度と歴史
    tokyo_ids = [("origin_latlon", "経緯度原点", -60, 90, "r"), ("origin_height", "水準原点", -60, -40, "r"),
                 ("diet", "国会議事堂", -40, -130, "r"), ("road_origin", "日本橋（道路元標）", 60, -60, "l")]
    tx, ty = P("diet")
    TOKYO = M.fit((tx - 30, ty - 20, tx + 30, ty + 16))
    HIST = M.fit((P("capital_fukuhara")[0] - 120, P("capital_asuka")[1] - 110, tx + 80, ty + 160))
    caps = [("capital_heijo", "平城京 710年", -30, 40, "r"), ("capital_heian", "平安京 794年", -30, -50, "r"),
            ("shogunate_edo", "東京 1868〜69年", 30, 70, "l")]
    other_caps = [k for k, r in C.items() if r["category"] == "制度的・歴史的中心" and k not in dict((c[0], 1) for c in caps)]

    def d_inst(cv, st):
        th = cv.th
        cam = M.cam_at([(0, NAGOYA), (st.at(0) + 0.3, NAGOYA), (st.at(1) - 0.3, TOKYO), (st.at(3) - 0.5, TOKYO),
                        (st.at(3) + 1.5, MAIN4), (st.at(4), MAIN4), (st.at(4) + 1.6, HIST)], st.t)
        M.draw_base(cv, cam, satellite=1.0)
        M.scale_bar(cv, cam, appear(st.t, st.at(1), 0.5) * (1 - appear(st.t, st.at(3) - 0.5, 0.4)))
        map_title(cv, "法律と歴史の中心", appear(st.t, 0, 0.5))
        for k, (cid, name, dx, dy, an) in enumerate(tokyo_ids):
            t0 = st.at(1) + 0.6 * k
            a = appear(st.t, t0, 0.4)
            mk(cv, cam, cid, a, st.t, t0)
            lab(cv, cam, cid, name, None, dx, dy, a * (1 - appear(st.t, st.at(3) - 0.5, 0.4)), an, 28)
        q = appear(st.t, st.at(2), 0.5) * (1 - appear(st.t, st.at(3) - 0.5, 0.4))
        _later(cv, lambda: pill_text(cv, (W / 2, 920), "首都圏整備法 第1条「わが国の政治、経済、文化等の中心としてふさわしい首都圏」", th.size_note + 2, q, bold=False))
        m = appear(st.t, st.at(3) + 1.0, 0.6)
        if m > 0:
            draw_geo_line(cv, cam, meridian(135, 30, 46), th.text, 3, m)
            x, y = cam.px(*M.project(135, 31.2))
            M.label(cv, x, y, "東経135度（日本標準時子午線）", None, 20, 0, m * (1 - appear(st.t, st.at(4), 0.4)), 28, leader=False)
        for k, cid in enumerate(other_caps):
            mk(cv, cam, cid, appear(st.t, st.at(4) + 1.0 + 0.1 * k, 0.4))
        for k, (cid, name, dx, dy, an) in enumerate(caps):
            t0 = st.at(4) + 1.8 + 0.7 * k
            a = appear(st.t, t0, 0.4)
            mk(cv, cam, cid, a, st.t, t0)
            lab(cv, cam, cid, name, None, dx, dy, appear(st.t, t0 + 0.3, 0.4), an, 30)
        note = ("経緯度原点・水準原点は測量の基準点（国土地理院）。位置は住所の代表点を含む" if st.t < st.at(4)
                else "年代：奈良県（平城京）、京都市（平安京）、国立公文書館（東京）の資料。ほかの宮は年代を示さない")
        map_note(cv, note, appear(st.t, st.at(1), 0.6))

    scenes.append(Scene("法律と歴史の中心", [
        Line("法律や歴史で決まっている中心もあります。"),
        Line("日本の測量の基準になる経緯度原点と水準原点、道路の起点である日本橋、そして国会は、東京の都心に集まっています。"),
        Line("法律にも、首都圏を、わが国の政治、経済、文化等の中心、と書いたものがあります。"),
        Line("また、日本の時刻の基準になる東経135度の子午線は、点ではなく線で表される中心です。"),
        Line("歴史をさかのぼると、都は奈良や京都に置かれていました。平城京は710年、平安京は794年。明治のはじめに、東京へ移りました。"),
    ], d_inst, tail=1.8))

    # 16 中心を名乗る町
    claims = [("heso_nishiwaki", "兵庫県西脇市", "東経135度・北緯35度", -30, 60, "r"),
              ("zero_tatsuno", "長野県辰野町", "北緯36度・東経138度", 30, -70, "l"),
              ("chiko_tatsuno", "チコちゃんポイント", "28自治体の地点の平均", -30, 70, "r"),
              ("mannaka_shibukawa", "群馬県渋川市", None, 30, -30, "l"),
              ("heso_sano", "栃木県佐野市", None, 30, 30, "l"),
              ("mannaka_chuo", "山梨県中央市", None, 30, 40, "l")]
    TOWN = M.fit((P("heso_nishiwaki")[0] - 80, P("mannaka_chuo")[1] - 180, P("heso_sano")[0] + 160, P("mannaka_shibukawa")[1] + 120))
    TATSU = M.fit((P("zero_tatsuno")[0] - 25, P("zero_tatsuno")[1] - 17, P("zero_tatsuno")[0] + 25, P("zero_tatsuno")[1] + 17))

    def d_towns(cv, st):
        th = cv.th
        cam = M.cam_at([(0, HIST), (st.at(0) + 1.0, TOWN), (st.at(2) + 0.2, TOWN), (st.at(3), TATSU),
                        (st.at(4) - 0.2, TATSU), (st.at(4) + 1.2, TOWN)], st.t)
        M.draw_base(cv, cam, satellite=1.0)
        M.pref_labels(cv, cam, 0.8)
        M.scale_bar(cv, cam, appear(st.t, st.at(3), 0.5) * (1 - appear(st.t, st.at(4) - 0.2, 0.4)))
        map_title(cv, "日本の中心を名乗る町", appear(st.t, 0, 0.5))
        a = appear(st.t, st.at(1), 0.5)
        draw_geo_line(cv, cam, meridian(135, 33, 37), hexrgb("F2C94C"), 3, a)
        draw_geo_line(cv, cam, parallel(35, 133, 137), hexrgb("F2C94C"), 3, a)
        b = appear(st.t, st.at(2), 0.5)
        draw_geo_line(cv, cam, meridian(138, 34, 38), hexrgb("F2C94C"), 3, b)
        draw_geo_line(cv, cam, parallel(36, 136, 140), hexrgb("F2C94C"), 3, b)
        times = [st.at(1) + 0.6, st.at(2) + 0.6, st.at(3) + 1.0, st.at(4) + 1.4, st.at(4) + 1.9, st.at(4) + 2.4]
        for (cid, name, sub, dx, dy, an), t0 in zip(claims, times):
            al = appear(st.t, t0, 0.4)
            mk(cv, cam, cid, al, st.t, t0)
            if cid == "chiko_tatsuno" or cid == "zero_tatsuno":
                hide = appear(st.t, st.at(4), 0.4) if cid == "chiko_tatsuno" else 0
                lab(cv, cam, cid, name, sub, dx, dy, appear(st.t, t0 + 0.3, 0.4) * (1 - hide), an, 28)
            else:
                lab(cv, cam, cid, name, sub, dx, dy, appear(st.t, t0 + 0.3, 0.4), an, 28)
        map_note(cv, "各自治体の公式ページの説明による。チコちゃんポイントは辰野町の紹介（28自治体の一覧は未確認）", appear(st.t, st.at(1), 0.6))

    scenes.append(Scene("日本の中心を名乗る町", [
        Line("最後に、自分の町こそ日本の中心だ、と名乗る自治体です。"),
        Line("兵庫県西脇市は、東経135度と北緯35度が交わる点を、日本のへそとしています。"),
        Line("長野県辰野町には、北緯36度と東経138度が交わる、ゼロポイントがあります。"),
        Line("辰野町によると、テレビ番組が、日本の中心を名乗る28の自治体の地点を平均した点も、このすぐ近くだったそうです。"),
        Line("ほかにも、群馬県渋川市、栃木県佐野市、山梨県中央市などが、日本の真ん中を名乗っています。"),
    ], d_towns, tail=1.6))

    # 17 すべての中心
    REG = [("pref", "13", "東京都"), ("pref", "01", "北海道"), ("pref", "12", "千葉県"),
           ("muni", "13103", "港区"), ("muni", "21203", "高山市")]
    type_order = [t for t, *_ in M.TYPES]

    def d_all(cv, st):
        th = cv.th
        cam = M.cam_at([(0, TOWN), (st.at(0) + 1.2, MAIN4)], st.t)
        M.draw_base(cv, cam)
        map_title(cv, f"集めた{N['n_all']}個の中心", appear(st.t, 0, 0.5))
        # 地域（最大集積地）
        ra = appear(st.t, st.at(1) + 1.6, 0.6)
        for kind, code, name in REG:
            polys = g["prefs"][code] if kind == "pref" else g["munis"][code]
            M.region(cv, cam, polys, M.STYLE["最大集積地"][0], ra)
        # 線（経線）
        la = appear(st.t, st.at(1) + 0.9, 0.6)
        draw_geo_line(cv, cam, meridian(135, 30, 46), th.text, 2.5, la)
        # 点（種類ごとに順に）
        for k, typ in enumerate(type_order):
            keys = [kk for kk in M.TYPES if kk[0] == typ][0][2]
            ids = [c for c, r in C.items() if r["category"] in keys and r["lat"] and c != "std_meridian"]
            t0 = st.at(0) + 1.2 + 0.25 * k
            for cid in ids:
                mk(cv, cam, cid, appear(st.t, t0, 0.4), r=9)
        # 凡例
        lg = appear(st.t, st.at(1), 0.5)
        if lg > 0:
            x, y = 70, 300
            cv.rect((x - 20, y - 34, x + 410, y + 7 * 46 + 30), WHITE, lg, radius=12)
            for k, (name, desc, _) in enumerate(M.TYPES):
                yy = y + k * 46
                if name == "最大集積地":
                    col = M.STYLE[name][0]
                    cv.rect((x, yy - 12, x + 26, yy + 12), mix(col, WHITE, 0.35 * lg), radius=3)
                else:
                    M.marker(cv, x + 13, yy, name, lg, 10, bg=WHITE)
                cv.text((x + 44, yy), desc + ("（地域）" if name == "最大集積地" else ""), th.size_note - 2, alpha=lg, anchor="lm")
            yy = y + 7 * 46
            M.dashed(cv, [(x, yy), (x + 26, yy)], th.text, 2.5, alpha=lg)
            cv.text((x + 44, yy), "標準時子午線（線）", th.size_note - 2, alpha=lg, anchor="lm")
        map_note(cv, "地域で示す最大集積地：東京都・北海道・千葉県・港区・高山市（指標ごとに最も多い地域）", appear(st.t, st.at(1) + 1.6, 0.6))

    scenes.append(Scene("すべての中心", [
        Line("集めた97個の中心を、1枚の地図に重ねます。"),
        Line("点で表すもの、線で表すもの、そして、最も多い地域として、面で表すものがあります。"),
        Line("人の活動から計算した重心は中部地方の内陸に集まり、国土の形や自然から計算した中心は、日本海や太平洋の上に出ます。"),
        Line("法律と歴史の中心は東京と近畿に分かれ、自治体が名乗る中心は、そのどれとも重なりません。"),
    ], d_all, tail=2.0))

    # 18 まとめ
    def d_end(cv, st):
        th = cv.th
        cam = MAIN4
        M.draw_base(cv, cam)
        for cid, r in C.items():
            if r["lat"] and cid != "std_meridian":
                x, y = cam.px(*P(cid))
                M.marker(cv, x, y, r["category"], 0.35, 9)
        d1 = st.ends[1] - st.starts[1]
        # 「山の中にも、駅にも、海の上にも」の言葉に合わせる
        words = [(["pop2020_official", "farthest_from_sea", "emp_ict"], st.at(1) + 0.40 * d1),
                 (["rail_closeness"], st.at(1) + 0.55 * d1),
                 (["area_excl_nt", "bbox_mid", "forest", "fish_catch"], st.at(1) + 0.70 * d1)]
        for ids, t0 in words:
            a = appear(st.t, t0, 0.4) * (1 - appear(st.t, st.at(2), 0.4))
            for cid in ids:
                x, y = cam.px(*P(cid))
                M.marker(cv, x, y, C[cid]["category"], a, 13, ring_of(st.t, t0))
        groups = [("人の活動", [c for c in dist_ids if C[c]["pref"] == "岐阜県"], M.project(136.9, 35.6), (-150, 150)),
                  ("形・自然", ["area_excl_nt", "bbox_mid", "forest", "fish_catch", "earthquakes"], M.project(137.55, 37.4), (-130, -70)),
                  ("法律・歴史", ["diet", "capital_heijo", "capital_heian", "shogunate_edo"], M.project(139.75, 35.68), (90, 50))]
        for k, (name, ids, (gx_, gy_), (dx_, dy_)) in enumerate(groups):
            a = appear(st.t, st.at(2) + 0.9 * k, 0.5)
            for cid in ids:
                x, y = cam.px(*P(cid))
                M.marker(cv, x, y, C[cid]["category"], a, 11)
            x, y = cam.px(gx_, gy_)
            M.label(cv, x, y, name, None, dx_, dy_, a, 32, "l" if dx_ > 0 else "r", leader=True)
        pill_text(cv, (W / 2, 84), "日本の中心は、測り方で変わる", th.size_title, appear(st.t, st.at(0), 0.6))

    scenes.append(Scene("まとめ", [
        Line("日本の中心は、一つには決まりません。"),
        Line("何を数えるか、どう測るかで、山の中にも、駅にも、海の上にもなります。"),
        Line("中心がどこに現れるかを見ると、その量が日本のどこに偏っているかが見えてきます。"),
    ], d_end, tail=2.4))

    # 19 データとクレジット
    credits = [("統計", "総務省統計局（国勢調査・人口重心）、統計ダッシュボード、各府省の統計"),
               ("地図", "国土地理院 地球地図日本、国土数値情報 鉄道（CC BY 4.0）を加工して作成"),
               ("衛星画像", "地理院タイル（全国ランドサットモザイク画像）を加工して作成"),
               ("", "データソース：Landsat8画像（GSI,TSIC,GEO Grid/AIST）, Landsat8画像（courtesy of the U.S. Geological Survey）, 海底地形（GEBCO）"),
               ("音声", voice_credit),
               ("音楽", music_credit or "なし")]

    def d_close(cv, st):
        th = cv.th
        a = appear(st.t, st.at(0), 0.6)
        svgicons.draw(cv, "map-2", W / 2, 230, 96, th.text, a)
        cv.text((W / 2, 320), "計算の方法・出典・限界は概要欄にまとめています。", th.size_body, bold=True, alpha=a, anchor="ma")
        b = appear(st.t, st.at(1), 0.6)
        cv.text((W / 2, 400), "重心の位置は、式・代表点・地図の縮尺の選び方で数km〜数十km 動きます。", th.size_note + 4,
                color=th.sub, alpha=b, anchor="ma")
        c = appear(st.t, st.at(1) + 1.0, 0.6)
        cs = th.size_note
        bw = 150 + max(cv.text_width(body, cs) for _, body in credits)
        left = (W - bw) / 2
        for k, (h, body) in enumerate(credits):
            y = 500 + k * 56
            cv.text((left, y), h, cs, bold=True, alpha=c)
            cv.text((left + 150, y), body, cs, color=th.sub, alpha=c)

    scenes.append(Scene("データとクレジット", [
        Line("使ったデータと計算の方法は、概要欄にまとめています。"),
        Line("重心の位置は、計算の式や代表点、地図の縮尺によって、数キロから数十キロ動くことにも注意してください。"),
    ], d_close, tail=3.0))

    for sc in scenes:
        sc.draw = deferred(sc.draw)
        for ln in sc.lines:
            if ln.say is None and yomi(ln.text) != ln.text:
                ln.say = yomi(ln.text)
    return scenes
