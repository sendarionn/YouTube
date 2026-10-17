"""図解用のアイコンと、人やモノの数で割合を示す図

アイコンは外部素材を使わず、図形の組み合わせで描く（ライセンスの確認が不要で、色と大きさを自由に変えられる）
座標は中心 (cx, cy) と大きさ s（高さの目安、ピクセル）で指定する
"""
import math

from .canvas import ease, mix


def _c(cv, color, alpha):
    return mix(color or cv.th.text, cv.th.bg, alpha)


def person(cv, cx, cy, s, color=None, alpha=1.0, cap=False):
    """人。cap=True で学生帽をのせる"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    d = cv.d
    hr = s * 0.17
    hy = cy - s * 0.28
    d.ellipse((cx - hr, hy - hr, cx + hr, hy + hr), fill=c)
    bw, top, bot = s * 0.30, cy - s * 0.06, cy + s * 0.48
    d.rounded_rectangle((cx - bw, top, cx + bw, bot), radius=int(bw * 0.8), fill=c)
    if cap:
        cw = s * 0.30
        d.polygon([(cx - cw, hy - hr * 0.9), (cx, hy - hr * 1.7), (cx + cw, hy - hr * 0.9), (cx, hy - hr * 0.2)], fill=c)
        d.line([(cx + cw * 0.8, hy - hr * 1.0), (cx + cw * 0.8, hy + hr * 0.3)], fill=c, width=max(2, int(s * 0.03)))


def briefcase(cv, cx, cy, s, color=None, alpha=1.0):
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    w, h = s * 0.9, s * 0.62
    cv.d.rounded_rectangle((cx - w / 2, cy - h / 2 + s * 0.08, cx + w / 2, cy + h / 2 + s * 0.08), radius=int(s * 0.08), fill=c)
    hw = s * 0.32
    cv.d.rounded_rectangle((cx - hw / 2, cy - h / 2 - s * 0.08, cx + hw / 2, cy - h / 2 + s * 0.12), radius=int(s * 0.05),
                           outline=c, width=max(3, int(s * 0.06)))
    cv.d.line([(cx - w / 2, cy + s * 0.05), (cx + w / 2, cy + s * 0.05)], fill=cv.th.bg, width=max(2, int(s * 0.03)))


def building(cv, cx, cy, s, color=None, alpha=1.0, floors=5):
    """ビル（大きな組織・上場企業）"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    w, h = s * 0.55, s
    x0, y0 = cx - w / 2, cy - h / 2
    cv.d.rectangle((x0, y0, x0 + w, y0 + h), fill=c)
    ww = w * 0.18
    for r in range(floors):
        for k in range(3):
            wx = x0 + w * (0.14 + 0.29 * k)
            wy = y0 + h * (0.08 + 0.17 * r)
            cv.d.rectangle((wx, wy, wx + ww, wy + h * 0.09), fill=cv.th.bg)


def shop(cv, cx, cy, s, color=None, alpha=1.0):
    """小さな店（小規模な開業）"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    w = s * 0.8
    x0 = cx - w / 2
    cv.d.polygon([(x0 - s * 0.05, cy - s * 0.1), (cx, cy - s * 0.45), (x0 + w + s * 0.05, cy - s * 0.1)], fill=c)
    cv.d.rectangle((x0, cy - s * 0.1, x0 + w, cy + s * 0.4), fill=c)
    cv.d.rectangle((cx - s * 0.12, cy + s * 0.08, cx + s * 0.12, cy + s * 0.4), fill=cv.th.bg)


def bulb(cv, cx, cy, s, color=None, alpha=1.0):
    """電球（アイデア）"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    r = s * 0.3
    cv.d.ellipse((cx - r, cy - s * 0.42, cx + r, cy - s * 0.42 + 2 * r), fill=c)
    cv.d.polygon([(cx - r * 0.6, cy + s * 0.05), (cx + r * 0.6, cy + s * 0.05), (cx + r * 0.45, cy + s * 0.25),
                  (cx - r * 0.45, cy + s * 0.25)], fill=c)
    for k in range(2):
        y = cy + s * (0.3 + 0.09 * k)
        cv.d.rounded_rectangle((cx - r * 0.45, y, cx + r * 0.45, y + s * 0.06), radius=int(s * 0.03), fill=c)
    for ang in (-60, -30, 0, 30, 60):
        a = math.radians(ang - 90)
        x1, y1 = cx + math.cos(a) * s * 0.42, cy - s * 0.12 + math.sin(a) * s * 0.42
        x2, y2 = cx + math.cos(a) * s * 0.52, cy - s * 0.12 + math.sin(a) * s * 0.52
        cv.d.line([(x1, y1), (x2, y2)], fill=c, width=max(2, int(s * 0.04)))


def cards(cv, cx, cy, s, color=None, alpha=1.0, n=5):
    """名刺の山"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    w, h = s * 0.8, s * 0.48
    for k in range(n):
        dx, dy = (k - n / 2) * s * 0.05, (n / 2 - k) * s * 0.07
        x0, y0 = cx - w / 2 + dx, cy - h / 2 + dy
        cv.d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=int(s * 0.03), fill=cv.th.bg, outline=c,
                               width=max(2, int(s * 0.03)))
        cv.d.line([(x0 + w * 0.12, y0 + h * 0.35), (x0 + w * 0.6, y0 + h * 0.35)], fill=c, width=max(2, int(s * 0.04)))
        cv.d.line([(x0 + w * 0.12, y0 + h * 0.62), (x0 + w * 0.45, y0 + h * 0.62)], fill=c, width=max(2, int(s * 0.03)))


def sheet(cv, cx, cy, s, color=None, alpha=1.0, rows=6):
    """帳簿・入力作業（罫線の入った書類と鉛筆）"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    w, h = s * 0.62, s * 0.85
    x0, y0 = cx - w / 2 - s * 0.08, cy - h / 2
    cv.d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=int(s * 0.04), outline=c, width=max(3, int(s * 0.04)))
    for k in range(rows):
        y = y0 + h * (0.18 + 0.13 * k)
        cv.d.line([(x0 + w * 0.15, y), (x0 + w * 0.85, y)], fill=c, width=max(2, int(s * 0.025)))
    px, py = x0 + w + s * 0.05, y0 + h * 0.25
    cv.d.polygon([(px, py), (px + s * 0.1, py - s * 0.06), (px - s * 0.18, py + s * 0.55), (px - s * 0.25, py + s * 0.6)], fill=c)


def magnifier(cv, cx, cy, s, color=None, alpha=1.0):
    """虫めがね（探す・転職活動）"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    r = s * 0.28
    ox, oy = cx - s * 0.08, cy - s * 0.08
    cv.d.ellipse((ox - r, oy - r, ox + r, oy + r), outline=c, width=max(4, int(s * 0.08)))
    cv.d.line([(ox + r * 0.7, oy + r * 0.7), (cx + s * 0.42, cy + s * 0.42)], fill=c, width=max(5, int(s * 0.11)))


def chart_up(cv, cx, cy, s, color=None, alpha=1.0):
    """右肩上がりの線と矢印（上場・成長）"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    w = max(4, int(s * 0.08))
    x0, y0 = cx - s * 0.45, cy + s * 0.4
    cv.d.line([(x0, cy - s * 0.45), (x0, y0), (cx + s * 0.45, y0)], fill=c, width=w)
    pts = [(x0 + s * 0.1, cy + s * 0.2), (cx - s * 0.1, cy), (cx + s * 0.05, cy + s * 0.1), (cx + s * 0.35, cy - s * 0.25)]
    cv.d.line(pts, fill=c, width=w, joint="curve")
    tx, ty = cx + s * 0.38, cy - s * 0.3
    cv.d.polygon([(tx + s * 0.05, ty - s * 0.08), (tx - s * 0.14, ty - s * 0.04), (tx - s * 0.02, ty + s * 0.12)], fill=c)


def flag(cv, cx, cy, s, color=None, alpha=1.0):
    """旗（決意）"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    x = cx - s * 0.25
    cv.d.line([(x, cy - s * 0.45), (x, cy + s * 0.45)], fill=c, width=max(4, int(s * 0.07)))
    cv.d.polygon([(x, cy - s * 0.45), (x + s * 0.55, cy - s * 0.28), (x, cy - s * 0.08)], fill=c)


def bank(cv, cx, cy, s, color=None, alpha=1.0):
    """柱のある建物（金融）"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    w = s * 0.9
    cv.d.polygon([(cx - w / 2, cy - s * 0.18), (cx, cy - s * 0.45), (cx + w / 2, cy - s * 0.18)], fill=c)
    for k in range(4):
        x = cx - w * 0.38 + k * w * 0.253
        cv.d.rectangle((x - s * 0.05, cy - s * 0.12, x + s * 0.05, cy + s * 0.3), fill=c)
    cv.d.rectangle((cx - w / 2, cy + s * 0.32, cx + w / 2, cy + s * 0.42), fill=c)


def factory(cv, cx, cy, s, color=None, alpha=1.0):
    """工場（メーカー・インフラ）"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    x0, y1 = cx - s * 0.45, cy + s * 0.4
    pts = [(x0, y1), (x0, cy - s * 0.05), (x0 + s * 0.3, cy - s * 0.25), (x0 + s * 0.3, cy - s * 0.05),
           (x0 + s * 0.6, cy - s * 0.25), (x0 + s * 0.6, cy - s * 0.05), (cx + s * 0.45, cy - s * 0.25), (cx + s * 0.45, y1)]
    cv.d.polygon(pts, fill=c)
    cv.d.rectangle((cx + s * 0.25, cy - s * 0.5, cx + s * 0.38, cy - s * 0.2), fill=c)


def presentation(cv, cx, cy, s, color=None, alpha=1.0):
    """ボードと棒グラフ（コンサルティング）"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    w, h = s * 0.85, s * 0.6
    x0, y0 = cx - w / 2, cy - s * 0.42
    cv.d.rectangle((x0, y0, x0 + w, y0 + h), outline=c, width=max(3, int(s * 0.05)))
    for k, bh in enumerate((0.25, 0.4, 0.55)):
        bx = x0 + w * (0.2 + 0.22 * k)
        cv.d.rectangle((bx, y0 + h * (0.85 - bh), bx + w * 0.14, y0 + h * 0.85), fill=c)
    cv.d.line([(cx, y0 + h), (cx - s * 0.2, cy + s * 0.45)], fill=c, width=max(3, int(s * 0.05)))
    cv.d.line([(cx, y0 + h), (cx + s * 0.2, cy + s * 0.45)], fill=c, width=max(3, int(s * 0.05)))


def browser(cv, cx, cy, s, color=None, alpha=1.0):
    """ブラウザの窓（ネット企業）"""
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    w, h = s * 0.9, s * 0.7
    x0, y0 = cx - w / 2, cy - h / 2
    cv.d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=int(s * 0.06), outline=c, width=max(3, int(s * 0.05)))
    cv.d.rectangle((x0, y0, x0 + w, y0 + h * 0.2), fill=c)
    cv.d.ellipse((cx - s * 0.13, cy - s * 0.02, cx + s * 0.13, cy + s * 0.24), outline=c, width=max(3, int(s * 0.04)))


def cross(cv, cx, cy, s, color=None, alpha=1.0):
    if alpha <= 0:
        return
    c = _c(cv, color, alpha)
    w = max(4, int(s * 0.12))
    cv.d.line([(cx - s * 0.3, cy - s * 0.3), (cx + s * 0.3, cy + s * 0.3)], fill=c, width=w)
    cv.d.line([(cx - s * 0.3, cy + s * 0.3), (cx + s * 0.3, cy - s * 0.3)], fill=c, width=w)


ICONS = {"person": person, "briefcase": briefcase, "building": building, "shop": shop, "bulb": bulb, "cards": cards,
         "sheet": sheet, "magnifier": magnifier, "chart_up": chart_up, "flag": flag, "bank": bank, "factory": factory,
         "presentation": presentation, "browser": browser, "cross": cross}


def icon(cv, name, cx, cy, s, color=None, alpha=1.0, **kw):
    ICONS[name](cv, cx, cy, s, color, alpha, **kw)


def people_grid(cv, box, total, n_on, cols, progress=1.0, on=None, off=None, alpha=1.0, cap_on=False):
    """total 人のうち n_on 人を強調するピクトグラム（progress に応じて強調が増える）"""
    x0, y0, x1, y1 = box
    rows = (total + cols - 1) // cols
    cw = (x1 - x0) / cols
    ch = (y1 - y0) / rows
    s = min(cw * 0.95, ch * 0.78)
    lit = int(round(n_on * progress))
    for k in range(total):
        r, c = divmod(k, cols)
        is_on = k < lit
        person(cv, x0 + cw * (c + 0.5), y0 + ch * (r + 0.5), s, (on or cv.th.accent) if is_on else (off or cv.th.muted),
               alpha, cap=cap_on and is_on)


def dot_hist(cv, box, values, vmin, vmax, progress=1.0, color_of=None, r=None, gap=2, alpha=1.0):
    """値ごとに点を積み上げる図（1人＝1点）。返り値は値→x座標の関数と、1点の直径

    progress：0〜1。全体の点が下から順に現れる。color_of(v) で点の色を変えられる
    """
    x0, y0, x1, y1 = box
    n = vmax - vmin + 1
    colw = (x1 - x0) / n
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    mx = max(counts.values())
    d = r * 2 if r else min(colw - gap, (y1 - y0) / mx - gap)
    shown = int(round(len(values) * ease(progress)))
    order = sorted(values)
    # 各列で下から積み、全体として progress の割合だけ表示する（列ごとに同じ割合）
    for v, cnt in counts.items():
        if v < vmin or v > vmax:
            continue
        k_show = int(round(cnt * shown / max(len(order), 1)))
        cx = x0 + colw * (v - vmin + 0.5)
        col = color_of(v) if color_of else cv.th.accent
        for k in range(k_show):
            cy = y1 - (k + 0.5) * (d + gap)
            cv.d.ellipse((cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2), fill=mix(col, cv.th.bg, alpha))

    def X(v):
        return x0 + colw * (v - vmin + 0.5)

    return X, d
