"""拡大した地図の背景に使う衛星画像（国土地理院の地理院タイル「全国最新写真（シームレス）」）

- タイル：https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg（ウェブメルカトル）
  ズーム 9〜13 は「全国ランドサットモザイク画像」（Landsat8 の衛星画像）、14〜18 は航空写真
- 取得したタイルは library/maptiles/files/gsi-seamlessphoto/{z}/{x}/{y}.jpg に保存し（Git 管理外）、
  台帳 library/maptiles/catalog.json と一覧 library/maptiles/gsi-seamlessphoto-tiles.json（ハッシュ）に記録する
  写真は更新されるため、再生成では保存済みのタイルを使い、取り直さない
- 動画の地図は正積図法（mapdraw.py）のため、場面ごとの範囲を正積図法の格子に描き直した画像（ラスター）を作り、
  cache/japan-center/video/sat/ に保存する。フレームごとには、その画像を切り抜いて拡大・縮小するだけにする
- 出典（地理院タイル一覧ページの指定）：地理院タイル（全国ランドサットモザイク画像）、
  データソース：Landsat8画像（GSI,TSIC,GEO Grid/AIST）, Landsat8画像（courtesy of the U.S. Geological Survey）, 海底地形（GEBCO）
"""
import hashlib
import json
import math
import sys
import time
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "research" / "scripts"))

TILESET = "gsi-seamlessphoto"
URL = "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg"
LIB = REPO / "library" / "maptiles"
FILES = LIB / "files" / TILESET
SAT = REPO / "cache" / "japan-center" / "video" / "sat"
CREDIT = ("衛星画像：地理院タイル（全国ランドサットモザイク画像）を加工して作成。データソース：Landsat8画像（GSI,TSIC,GEO Grid/AIST）, "
          "Landsat8画像（courtesy of the U.S. Geological Survey）, 海底地形（GEBCO）")
SHORT_CREDIT = "衛星画像：地理院タイル（Landsat8）"

# 場面ごとの範囲：(名前, 中心の経度・緯度, 東西・南北の半幅 km, 1px の m, タイルのズーム)
# ズーム 9〜13 はすべて Landsat8 のモザイク（同じ見た目にそろう）
RASTERS = [
    ("mid", (137.8, 36.8), (1000, 820), 300, 9),
    ("noto", (137.59, 37.34), (260, 180), 110, 10),
    ("saku", (138.58, 36.18), (270, 220), 110, 10),
    ("track", (137.02, 35.60), (45, 32), 15, 13),
    ("haya", (138.27, 35.56), (95, 65), 30, 12),
    ("tokyo", (139.745, 35.68), (40, 28), 15, 13),
    ("tatsu", (138.0, 36.0), (35, 25), 15, 13),
]


def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def fetch_tile(z, x, y):
    p = FILES / str(z) / str(x) / f"{y}.jpg"
    if p.exists():
        return p
    import requests
    p.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(URL.format(z=z, x=x, y=y), timeout=60)
    time.sleep(0.12)  # サーバーに負荷をかけない間隔
    if r.status_code == 404:  # 範囲外（海の遠方など）
        p.with_suffix(".none").write_text("")
        return None
    r.raise_for_status()
    p.write_bytes(r.content)
    return p


def _tile_image(z, x, y):
    p = FILES / str(z) / str(x) / f"{y}.jpg"
    if not p.exists() and (FILES / str(z) / str(x) / f"{y}.none").exists():
        return None
    p = fetch_tile(z, x, y)
    return Image.open(p).convert("RGB") if p else None


def raster_grid(center, half, mpp):
    """正積図法の格子（km）。戻り値は (x0, y0, x1, y1)、幅、高さ"""
    import mapdraw as M
    cx, cy = M.project(*center)
    x0, x1, y0, y1 = cx - half[0], cx + half[0], cy - half[1], cy + half[1]
    w, h = int(round((x1 - x0) * 1000 / mpp)), int(round((y1 - y0) * 1000 / mpp))
    return (x0, y0, x1, y1), w, h


def build_raster(name, center, half, mpp, z):
    """タイルを貼り合わせ、正積図法の格子に描き直した画像を作る"""
    import geo
    (x0, y0, x1, y1), w, h = raster_grid(center, half, mpp)
    xs = np.linspace(x0, x1, w, endpoint=False) + (x1 - x0) / w / 2
    ys = np.linspace(y1, y0, h, endpoint=False) - (y1 - y0) / h / 2
    gx, gy = np.meshgrid(xs * 1000, ys * 1000)
    lon, lat = geo.TO_LL.transform(gx, gy)
    n = 2 ** z
    tx = (lon + 180) / 360 * n
    ty = (1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * n
    tx0, tx1 = int(np.floor(tx.min())), int(np.floor(tx.max()))
    ty0, ty1 = int(np.floor(ty.min())), int(np.floor(ty.max()))
    mosaic = np.zeros(((ty1 - ty0 + 1) * 256, (tx1 - tx0 + 1) * 256, 3), np.uint8)
    have = np.zeros((ty1 - ty0 + 1, tx1 - tx0 + 1), bool)
    for X in range(tx0, tx1 + 1):
        for Y in range(ty0, ty1 + 1):
            im = _tile_image(z, X, Y)
            if im is not None:
                mosaic[(Y - ty0) * 256:(Y - ty0 + 1) * 256, (X - tx0) * 256:(X - tx0 + 1) * 256] = np.asarray(im)
                have[Y - ty0, X - tx0] = True
    # 双一次補間で標本化する
    from scipy.ndimage import map_coordinates
    py = (ty - ty0) * 256 - 0.5
    px = (tx - tx0) * 256 - 0.5
    out = np.stack([map_coordinates(mosaic[..., c].astype(np.float32), [py, px], order=1, mode="nearest")
                    for c in range(3)], axis=-1)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    SAT.mkdir(parents=True, exist_ok=True)
    img.save(SAT / f"{name}.jpg", quality=92)
    meta = {"name": name, "bbox_km": [x0, y0, x1, y1], "width": w, "height": h, "mpp": mpp, "zoom": z,
            "tiles": int(have.sum()), "missing_tiles": int((~have).sum())}
    (SAT / f"{name}.json").write_text(json.dumps(meta))
    return meta


def build_all():
    metas = [build_raster(*r) for r in RASTERS]
    write_catalog()
    return metas


def write_catalog():
    """台帳と、取得したタイルの一覧（ハッシュ）を書く"""
    tiles = {}
    for p in sorted(FILES.rglob("*.jpg")):
        tiles[p.relative_to(FILES).as_posix()] = hashlib.sha1(p.read_bytes()).hexdigest()
    LIB.mkdir(parents=True, exist_ok=True)
    (LIB / f"{TILESET}-tiles.json").write_text(json.dumps(tiles, indent=0, sort_keys=True) + "\n")
    cat_path = LIB / "catalog.json"
    cat = json.loads(cat_path.read_text()) if cat_path.exists() else {
        "note": "地図タイル（衛星画像など）の台帳（AGENTS.md「取得済み素材の管理」）。原本は files/（Git管理外）", "sets": []}
    entry = {
        "id": TILESET, "name": "地理院タイル 全国最新写真（シームレス）", "creator": "国土地理院",
        "library": "地理院タイル", "url_template": URL, "source_url": "https://maps.gsi.go.jp/development/ichiran.html",
        "files": f"files/{TILESET}/{{z}}/{{x}}/{{y}}.jpg", "tile_list": f"{TILESET}-tiles.json",
        "zoom_levels_used": sorted({int(k.split('/')[0]) for k in tiles}), "tiles": len(tiles),
        "content": "ズーム 9〜13 は全国ランドサットモザイク画像（Landsat8）、14〜18 は航空写真。今回はズーム 9〜13 だけを使った",
        "acquired": date.today().isoformat(),
        "license": "国土地理院コンテンツ利用規約（公共データ利用規約 第1.0版 PDL1.0 に準拠、CC BY 4.0 と互換）",
        "license_url": "https://www.gsi.go.jp/kikakuchousei/kikakuchousei40182.html",
        "terms": "出典の記載で利用可（地理院タイル一覧の「出典の記載のみで利用可能なもの」）。商用利用可（PDL1.0）。加工した場合は加工したことと主体を記載し、国土地理院が作成したかのように示さない。"
                 "ランドサットモザイク画像は追加のデータソースの表記が必要",
        "license_checked": "2026-10-26", "commercial_use": True, "youtube_use": True, "credit_required": True,
        "credit": CREDIT, "style": "衛星画像（トゥルーカラー）", "used_in": ["japan-center/video（2026-10-26）"],
    }
    cat["sets"] = [s for s in cat["sets"] if s["id"] != TILESET] + [entry]
    cat_path.write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n")


@lru_cache(maxsize=3)
def load(name):
    meta = json.loads((SAT / f"{name}.json").read_text())
    return meta, Image.open(SAT / f"{name}.jpg").convert("RGB")


def available():
    return [r[0] for r in RASTERS if (SAT / f"{r[0]}.json").exists()]


def render(cam, width, height, ss):
    """カメラの見る範囲の衛星画像（出力解像度 × ss の大きさ）と、画像がある範囲のマスク（L、0〜255）

    画面を覆う画像があれば、必要な細かさに足りる中で最も粗いものを使う（足りなければ最も細かいもの）。
    覆う画像がない場合は、重なりの最も大きい画像を使い、画像のない部分はマスクで外す（写真が一度に消えないように）
    """
    W, H = width * ss, height * ss
    vx0 = cam.x - cam.cx * cam.kmpp
    vx1 = cam.x + (width - cam.cx) * cam.kmpp
    vy1 = cam.y + cam.cy * cam.kmpp
    vy0 = cam.y - (height - cam.cy) * cam.kmpp
    need = cam.kmpp * 1000 / ss  # 1px あたりに必要な m
    best, partial = None, None
    for name in available():
        meta = json.loads((SAT / f"{name}.json").read_text())
        x0, y0, x1, y1 = meta["bbox_km"]
        if x0 <= vx0 and vx1 <= x1 and y0 <= vy0 and vy1 <= y1:
            key = (0, -meta["mpp"]) if meta["mpp"] <= need * 1.6 else (1, meta["mpp"])
            if best is None or key < best[0]:
                best = (key, name)
        else:
            ov = max(0, min(x1, vx1) - max(x0, vx0)) * max(0, min(y1, vy1) - max(y0, vy0))
            if ov > 0 and (partial is None or ov > partial[0]):
                partial = (ov, name)
    if best is None and partial is None:
        return None, None
    name = best[1] if best else partial[1]
    meta, img = load(name)
    x0, y0, x1, y1 = meta["bbox_km"]
    sx = meta["width"] / (x1 - x0)
    sy = meta["height"] / (y1 - y0)
    box = ((vx0 - x0) * sx, (y1 - vy1) * sy, (vx1 - x0) * sx, (y1 - vy0) * sy)
    out = img.transform((W, H), Image.Transform.EXTENT, box, Image.Resampling.BILINEAR)
    if best:
        return out, None
    mask = Image.new("L", (meta["width"], meta["height"]), 255).transform((W, H), Image.Transform.EXTENT, box,
                                                                          Image.Resampling.BILINEAR, fill=0)
    return out, mask


def alpha_for(kmpp, start=0.65, full=0.45):
    """縮尺に応じた衛星画像の濃さ（拡大するほど濃く）"""
    return min(1.0, max(0.0, (start - kmpp) / (start - full)))


if __name__ == "__main__":
    for m in build_all():
        print(m)
