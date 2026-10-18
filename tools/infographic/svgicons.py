"""既存のベクターアイコン集（library/icons/）を描画する

台帳（library/icons/catalog.json）にあるアイコン集を取得し、1つのアイコンを SVG に組み立てて PyMuPDF で描く
- 色・線幅・大きさは呼び出し側で指定する（DESIGN.md「素材と図表の使い分け」：パレットに合わせて調整する）
- 描画はスーパーサンプリング後の解像度で行うため、縮小後も輪郭が滑らか
- 使ったアイコン名は used に記録し、素材管理の記録に出力できるようにする
"""
import hashlib
import json
import subprocess
from functools import lru_cache

from .canvas import mix
from .config import REPO

LIBRARY = REPO / "library" / "icons"
used = set()


def catalog():
    return {s["id"]: s for s in json.loads((LIBRARY / "catalog.json").read_text(encoding="utf-8"))["sets"]}


def fetch(set_id):
    s = catalog()[set_id]
    path = LIBRARY / s["file"]
    if path.exists() and hashlib.sha1(path.read_bytes()).hexdigest() == s["sha1"]:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    subprocess.run(["curl", "-sfL", "--retry", "3", "-o", str(tmp), s["download_url"]], check=True)
    if hashlib.sha1(tmp.read_bytes()).hexdigest() != s["sha1"]:
        tmp.unlink()
        raise RuntimeError(f"{set_id}: sha1 が台帳と一致しません")
    tmp.rename(path)
    return path


@lru_cache(maxsize=None)
def _nodes(set_id):
    return json.loads(fetch(set_id).read_text(encoding="utf-8"))


def _attrs(a):
    return " ".join(f'{k}="{v}"' for k, v in a.items() if k != "key")


def svg(name, color="#000000", stroke=2.0, set_id="tabler-outline"):
    """アイコン1つの SVG 文字列（24×24 の座標系、線のアイコン）"""
    nodes = _nodes(set_id)
    if name not in nodes:
        raise KeyError(f"アイコン {name} が {set_id} にありません")
    body = "".join(f"<{tag} {_attrs(a)}/>" for tag, a in nodes[name])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


@lru_cache(maxsize=512)
def _raster(name, color, stroke, px, set_id):
    import pymupdf
    from PIL import Image

    doc = pymupdf.open(stream=svg(name, color, stroke, set_id).encode(), filetype="svg")
    page = doc[0]
    z = px / page.rect.width
    pm = page.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=True)
    return Image.frombytes("RGBA", (pm.width, pm.height), pm.samples)


def draw(cv, name, cx, cy, size, color=None, alpha=1.0, stroke=1.75, set_id="tabler-outline"):
    """中心 (cx, cy)、一辺 size（出力解像度のピクセル）でアイコンを描く。alpha はフェード用"""
    if alpha <= 0:
        return
    used.add((set_id, name))
    c = color or cv.th.text
    hexc = "#%02x%02x%02x" % tuple(c)
    px = max(4, int(round(size * cv.ss)))
    im = _raster(name, hexc, stroke, px, set_id)
    mask = im.getchannel("A")
    if alpha < 1:
        mask = mask.point(lambda v: int(v * alpha))
    x = int(round((cx - size / 2) * cv.ss))
    y = int(round((cy - size / 2) * cv.ss))
    cv.img.paste(im.convert("RGB"), (x, y), mask)


def used_report():
    """使ったアイコンの一覧（素材管理の記録用）"""
    cat = catalog()
    return [{"set": s, "name": n, "license": cat[s]["license"], "source": cat[s]["source_url"]} for s, n in sorted(used)]


__all__ = ["draw", "svg", "fetch", "catalog", "used_report", "mix"]
