"""1フレームを描く部品

DESIGN.md の方針に合わせ、動きは「出現（フェード）」と「棒の伸長」だけにする
半透明の重ね合わせは使わず、背景色との線形補間でフェードを表現する（高速で、文字の重なりも起きない）
"""
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

from .config import find_font


def ease(p):
    """0〜1 を ease-out（3次）で補間"""
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def ramp(t, start, dur=0.5):
    """時刻 t における、start から dur 秒かけた進行度（0〜1、ease-out）"""
    if t is None or start is None:
        return 0.0
    return ease((t - start) / dur) if dur > 0 else float(t >= start)


def mix(c1, c2, a):
    """c2 から c1 へ a の割合で近づけた色（a=1 で c1）"""
    return tuple(round(c2[i] + (c1[i] - c2[i]) * a) for i in range(3))


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@dataclass
class Theme:
    width: int = 1920
    height: int = 1080
    margin: int = 120
    bg: tuple = hexrgb("F6F5F2")
    text: tuple = hexrgb("1F2328")
    sub: tuple = hexrgb("5B6470")
    grid: tuple = hexrgb("D9DCE0")
    accent: tuple = hexrgb("2E6BD1")
    compare: tuple = hexrgb("8E98A3")
    muted: tuple = hexrgb("C9CED4")
    font_regular: str = "BIZUDPGothic-Regular.ttf"
    font_bold: str = "BIZUDPGothic-Bold.ttf"
    # 文字サイズは3段階（タイトル・主要数値・補足）＋字幕と注記
    size_title: int = 56
    size_number: int = 120
    size_body: int = 40
    size_note: int = 26
    size_caption: int = 40
    caption_top: int = 948
    caption_bottom: int = 1040
    _fonts: dict = field(default_factory=dict, repr=False)

    def font(self, size, bold=False):
        k = (size, bold)
        if k not in self._fonts:
            self._fonts[k] = ImageFont.truetype(str(find_font(self.font_bold if bold else self.font_regular)), size)
        return self._fonts[k]


class Canvas:
    def __init__(self, theme):
        self.th = theme
        self.img = Image.new("RGB", (theme.width, theme.height), theme.bg)
        self.d = ImageDraw.Draw(self.img)

    # 文字
    def text(self, xy, s, size=None, bold=False, color=None, alpha=1.0, anchor="la"):
        if alpha <= 0:
            return
        f = self.th.font(size or self.th.size_body, bold)
        self.d.text(xy, s, font=f, fill=mix(color or self.th.text, self.th.bg, alpha), anchor=anchor)

    def text_width(self, s, size=None, bold=False):
        return self.d.textlength(s, font=self.th.font(size or self.th.size_body, bold))

    def wrap(self, s, width, size=None, bold=False):
        """幅に収まるよう1文字単位で折り返す（句読点・閉じ括弧を行頭に置かない）"""
        lines, cur = [], ""
        for ch in s:
            if self.text_width(cur + ch, size, bold) > width and cur:
                if ch in "、。）」％%・ー":
                    ch, cur = cur[-1] + ch, cur[:-1]
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        if cur:
            lines.append(cur)
        return lines

    # 図形
    def rect(self, box, color, alpha=1.0, radius=0):
        if alpha <= 0 or box[2] <= box[0] or box[3] <= box[1]:
            return
        c = mix(color, self.th.bg, alpha)
        if radius:
            self.d.rounded_rectangle(box, radius=radius, fill=c)
        else:
            self.d.rectangle(box, fill=c)

    def line(self, xy, color=None, width=2, alpha=1.0):
        if alpha > 0:
            self.d.line(xy, fill=mix(color or self.th.grid, self.th.bg, alpha), width=width)

    # 画面の定型部分
    def title(self, s, alpha=1.0):
        self.text((self.th.margin, 92), s, self.th.size_title, bold=True, alpha=alpha)

    def note(self, s, alpha=1.0, y=890):
        """分母・定義・出典などの注記（字幕帯より上の固定位置）"""
        self.text((self.th.margin, y), s, self.th.size_note, color=self.th.sub, alpha=alpha)

    def caption(self, s):
        """字幕（画面下の帯。図表と重ならない位置に固定）"""
        if not s:
            return
        th = self.th
        lines = self.wrap(s, th.width - 2 * th.margin - 80, th.size_caption)
        if len(lines) > 2:
            raise ValueError(f"字幕が3行以上になります：{s}")
        self.rect((0, th.caption_top, th.width, th.caption_bottom + 10), hexrgb("FFFFFF"))
        self.line([(0, th.caption_top), (th.width, th.caption_top)], th.grid, 2)
        lh = th.size_caption + 10
        y0 = (th.caption_top + th.caption_bottom) // 2 - lh * len(lines) // 2 + 4
        for i, ln in enumerate(lines):
            self.text((th.width // 2, y0 + i * lh), ln, th.size_caption, anchor="ma")


def vbars(cv, box, labels, values, progress=1.0, color=None, highlight=None, vmax=None,
          fmt="{:,}", alpha=1.0, label_size=None, value_size=None, colors=None):
    """縦棒グラフ（軸は0から）。highlight の棒だけ強調色、他は muted"""
    th = cv.th
    x0, y0, x1, y1 = box
    vmax = vmax or max(values)
    n = len(values)
    gap = (x1 - x0) / n
    bw = gap * 0.62
    ls = label_size or th.size_note + 4
    vs = value_size or th.size_body
    base = y1 - ls - 24
    cv.line([(x0, base), (x1, base)], th.grid, 3, alpha)
    for i, (lab, v) in enumerate(zip(labels, values)):
        cx = x0 + gap * (i + 0.5)
        h = (base - y0 - vs - 20) * v / vmax * progress
        c = (colors[i] if colors else (color or th.accent) if highlight is None or i in highlight else th.muted)
        cv.rect((cx - bw / 2, base - h, cx + bw / 2, base), c, alpha)
        cv.text((cx, base + 14), lab, ls, color=th.sub, alpha=alpha, anchor="ma")
        if progress > 0.98:
            cv.text((cx, base - h - 12), fmt.format(v), vs, bold=True, alpha=alpha, anchor="md")


def hbars(cv, box, labels, values, progress=1.0, color=None, vmax=None, fmt="{}", alpha=1.0,
          label_w=420, size=None, colors=None, row_h=None):
    """横棒グラフ（軸は0から）。progress は棒ごとのリストでもよい"""
    th = cv.th
    x0, y0, x1, y1 = box
    vmax = vmax or max(values)
    n = len(values)
    rh = row_h or (y1 - y0) / n
    s = size or th.size_body
    bx0 = x0 + label_w
    bx1 = x1 - 220
    for i, (lab, v) in enumerate(zip(labels, values)):
        p = progress[i] if isinstance(progress, (list, tuple)) else progress
        a = alpha if not isinstance(progress, (list, tuple)) else alpha * min(1.0, p * 3)
        cy = y0 + rh * (i + 0.5)
        bh = min(rh * 0.56, 64)
        c = colors[i] if colors else (color or th.accent)
        cv.text((x0, cy), lab, s, alpha=a, anchor="lm")
        w = (bx1 - bx0) * v / vmax * p
        cv.rect((bx0, cy - bh / 2, bx0 + w, cy + bh / 2), c, a)
        if p > 0.98:
            cv.text((bx0 + w + 18, cy), fmt.format(v), s, bold=True, alpha=a, anchor="lm")
    cv.line([(bx0, y0), (bx0, y0 + rh * n)], th.text, 2, alpha)


def waffle(cv, box, n_on, total=100, cols=10, progress=1.0, on=None, off=None, alpha=1.0):
    """total マスのうち n_on マスを強調する割合図（progress に応じて強調マスが順に色付く）"""
    th = cv.th
    x0, y0, x1, y1 = box
    rows = (total + cols - 1) // cols
    cell = min((x1 - x0) / cols, (y1 - y0) / rows)
    pad = cell * 0.14
    lit = int(round(n_on * progress))
    for k in range(total):
        r, c = divmod(k, cols)
        bx = x0 + c * cell
        by = y0 + r * cell
        col = (on or th.accent) if k < lit else (off or th.muted)
        cv.rect((bx + pad, by + pad, bx + cell - pad, by + cell - pad), col, alpha, radius=int(cell * 0.12))


def gantt(cv, box, rows, start, end, progress=1.0, label_w=360, size=None, tick_every=2, markers=()):
    """年表（横棒の期間図）。rows は (ラベル, 開始年, 終了年, 色) のリスト（年は小数可）

    progress は行ごとのリストでもよい。markers は (年, ラベル) を軸の下に示す
    """
    th = cv.th
    x0, y0, x1, y1 = box
    s = size or th.size_note + 6
    ax0, ax1 = x0 + label_w, x1
    span = end - start

    def X(y):
        return ax0 + (ax1 - ax0) * (y - start) / span

    rh = (y1 - y0 - 70) / max(len(rows), 1)
    base = y0 + rh * len(rows) + 10
    cv.line([(ax0, base), (ax1, base)], th.grid, 2)
    for yr in range(int(start), int(end) + 1):
        if (yr - int(start)) % tick_every == 0:
            cv.line([(X(yr), base), (X(yr), base + 10)], th.grid, 2)
            cv.text((X(yr), base + 16), str(yr), th.size_note - 4, color=th.sub, anchor="ma")
    for i, (lab, a, b, col) in enumerate(rows):
        p = progress[i] if isinstance(progress, (list, tuple)) else progress
        if p <= 0:
            continue
        al = min(1.0, p * 2)
        cy = y0 + rh * (i + 0.5)
        cv.text((x0, cy), lab, s, alpha=al, anchor="lm")
        bh = min(rh * 0.5, 40)
        cv.rect((X(a), cy - bh / 2, X(a) + (X(b) - X(a)) * p, cy + bh / 2), col, al)
    # 近い位置のラベルは段をずらして重ならないようにする
    prev_x, level = None, 0
    for yr, lab, p in markers:
        x = X(yr)
        w = cv.text_width(lab, th.size_note, True)
        level = level + 1 if prev_x is not None and x - prev_x < w + 20 and level == 0 else 0
        prev_x = x
        if p <= 0:
            continue
        cv.line([(x, y0), (x, base)], th.text, 2, p)
        cv.text((min(x, ax1 - w / 2), base + 48 + level * 40), lab, th.size_note, bold=True, alpha=p, anchor="ma")


def arrow(cv, xy0, xy1, color=None, alpha=1.0, width=4, head=16):
    """右向きの矢印（水平）"""
    th = cv.th
    (a, y), (b, _) = xy0, xy1
    cv.line([(a, y), (b - head, y)], color or th.sub, width, alpha)
    if alpha > 0:
        cv.d.polygon([(b, y), (b - head, y - head * 0.6), (b - head, y + head * 0.6)],
                     fill=mix(color or th.sub, th.bg, alpha))


def flow(cv, box, items, alphas, size=None, head_size=None):
    """横に並ぶ箱と矢印の流れ図。items は (見出し, 本文) のリスト。本文は箱の幅で折り返す"""
    th = cv.th
    x0, y0, x1, y1 = box
    n = len(items)
    gap = 70
    w = (x1 - x0 - gap * (n - 1)) / n
    s = size or th.size_note + 4
    hs = head_size or th.size_note + 2
    for i, ((head, body), a) in enumerate(zip(items, alphas)):
        if a <= 0:
            continue
        bx = x0 + i * (w + gap)
        cv.rect((bx, y0, bx + w, y1), (255, 255, 255), a, radius=10)
        cv.text((bx + 24, y0 + 20), head, hs, bold=True, color=th.accent, alpha=a)
        lines = cv.wrap(body, w - 48, s)
        if len(lines) * (s + 12) > y1 - y0 - 80:
            raise ValueError(f"流れ図の本文が箱に収まりません：{body}")
        for k, ln in enumerate(lines):
            cv.text((bx + 24, y0 + 30 + hs + 18 + k * (s + 12)), ln, s, alpha=a)
        if i:
            arrow(cv, (bx - gap + 12, (y0 + y1) / 2), (bx - 12, (y0 + y1) / 2), alpha=a)


def table(cv, box, header, rows, col_w, alphas=None, size=None, row_h=None, head_fill=None):
    """表。col_w は列幅のリスト。セルは列幅で折り返す。alphas は行ごとの不透明度"""
    th = cv.th
    x0, y0, x1, y1 = box
    s = size or th.size_note + 2
    lh = s + 10
    xs = [x0]
    for w in col_w:
        xs.append(xs[-1] + w)
    y = y0
    hh = lh + 24
    cv.rect((x0, y, xs[-1], y + hh), head_fill or th.muted)
    for j, h in enumerate(header):
        cv.text((xs[j] + 16, y + 12), h, s, bold=True)
    y += hh
    for i, row in enumerate(rows):
        a = alphas[i] if alphas else 1.0
        cells = [cv.wrap(c, col_w[j] - 32, s, bold=(j == 0)) for j, c in enumerate(row)]
        h = row_h or (max(len(c) for c in cells) * lh + 24)
        if a > 0:
            for j, c in enumerate(cells):
                for k, ln in enumerate(c):
                    cv.text((xs[j] + 16, y + 12 + k * lh), ln, s, bold=(j == 0), alpha=a)
        cv.line([(x0, y + h), (xs[-1], y + h)], th.grid, 2)
        y += h
    if y > y1:
        raise ValueError("表が枠に収まりません")
